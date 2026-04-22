"""
Download official datasets and build stratified ground truth files.

Produces data/ground_truth/{task}.jsonl with 500 examples per task,
stratified so difficulty is evenly spread across bins.

Each row:
  {"sample_id": "maths_0001", "task": "maths",
   "prompt": "...", "reference": {...}, "source": "gsm8k", "difficulty_bin": 2}

Usage:
    python tools/build_ground_truth.py
    python tools/build_ground_truth.py --tasks maths code_generation
    python tools/build_ground_truth.py --target 500 --seed 42
"""

from __future__ import annotations

import sys
from pathlib import Path

# Must happen before any other imports — strip the project root from sys.path
# so the local pandas/ directory doesn't shadow the real pandas package.
_ROOT = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if Path(p).resolve() != _ROOT]

import argparse
import json
import random
from collections import defaultdict
from typing import Any

ROOT    = _ROOT
GT_DIR  = ROOT / "data" / "ground_truth"

# ── helpers ──────────────────────────────────────────────────────────────────

def load_hf(path: str, name: str | None = None, split: str = "test",
            fallback_split: str = "train") -> list[dict]:
    from datasets import load_dataset
    try:
        ds = load_dataset(path, name, split=split, trust_remote_code=True)
        return [dict(r) for r in ds]
    except Exception:
        try:
            ds = load_dataset(path, name, split=fallback_split, trust_remote_code=True)
            return [dict(r) for r in ds]
        except Exception as e:
            print(f"  WARN: could not load {path} ({name}): {e}")
            return []


def stratified_sample(rows: list[dict], key: str, n: int, rng: random.Random) -> list[dict]:
    """
    Sample n rows with equal representation across values of `key`.
    Falls back to random sample if buckets are uneven.
    """
    buckets: dict[Any, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[r.get(key, "unknown")].append(r)

    if not buckets:
        return rng.sample(rows, min(n, len(rows)))

    per_bucket = max(1, n // len(buckets))
    sampled: list[dict] = []
    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)
        sampled.extend(bucket_rows[:per_bucket])

    # top up or trim to exactly n
    rng.shuffle(sampled)
    if len(sampled) < n:
        remaining = [r for r in rows if r not in sampled]
        rng.shuffle(remaining)
        sampled.extend(remaining[:n - len(sampled)])
    return sampled[:n]


def save_gt(task: str, rows: list[dict]) -> None:
    GT_DIR.mkdir(parents=True, exist_ok=True)
    out = GT_DIR / f"{task}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  Saved {len(rows)} rows -> {out}")


def difficulty_bin(value: float, n_bins: int = 5) -> int:
    """Assign to bin 0-4 given a numeric difficulty value (percentile-relative)."""
    return min(n_bins - 1, max(0, int(value)))


# ── task builders ─────────────────────────────────────────────────────────────

def build_classification(target: int, rng: random.Random) -> list[dict]:
    print("  Loading SST-2 ...")
    sst2_rows = load_hf("nyu-mll/glue", "sst2", split="validation")
    label_map_sst = {0: "negative", 1: "positive"}

    print("  Loading AG News ...")
    ag_rows = load_hf("fancyzhx/ag_news", split="test")
    label_map_ag = {0: "world", 1: "sports", 2: "business", 3: "sci/tech"}

    print("  Loading TREC ...")
    trec_rows = load_hf("CogComp/trec", split="test", fallback_split="train")
    label_map_trec = {0: "description", 1: "entity", 2: "abbreviation",
                      3: "human", 4: "location", 5: "number"}

    pool: list[dict] = []

    # SST-2 — 250 samples, stratify by label
    sst_prep = [{"text": r["sentence"], "label": label_map_sst.get(r["label"], str(r["label"])),
                 "source": "sst2"} for r in sst2_rows if r.get("sentence")]
    sst_sampled = stratified_sample(sst_prep, "label", min(250, len(sst_prep)), rng)
    pool.extend(sst_sampled)

    # AG News — 150 samples, stratify by label
    ag_prep = [{"text": (r.get("text") or r.get("description") or "")[:300],
                "label": label_map_ag.get(r["label"], str(r["label"])),
                "source": "ag_news"} for r in ag_rows if r.get("text") or r.get("description")]
    ag_sampled = stratified_sample(ag_prep, "label", min(150, len(ag_prep)), rng)
    pool.extend(ag_sampled)

    # TREC — 100 samples, stratify by label
    trec_prep = []
    for r in trec_rows:
        label_field = r.get("coarse_label") if r.get("coarse_label") is not None else r.get("label-coarse")
        text = r.get("text") or r.get("question-text") or ""
        if text and label_field is not None:
            trec_prep.append({"text": text,
                               "label": label_map_trec.get(int(label_field), str(label_field)),
                               "source": "trec"})
    trec_sampled = stratified_sample(trec_prep, "label", min(100, len(trec_prep)), rng)
    pool.extend(trec_sampled)

    rng.shuffle(pool)
    pool = pool[:target]

    rows = []
    for i, r in enumerate(pool):
        text = r["text"].strip()
        label = r["label"]
        rows.append({
            "sample_id": f"classification_{i:04d}",
            "task":      "classification",
            "source":    r["source"],
            "prompt":    f"Classify the sentiment or category of the following text.\n"
                         f"Respond with exactly one label.\n\nText: {text}",
            "reference": {"label": label},
        })
    return rows


def build_maths(target: int, rng: random.Random) -> list[dict]:
    import re

    print("  Loading GSM8K ...")
    gsm_rows = load_hf("openai/gsm8k", "main", split="test")

    print("  Loading SVAMP ...")
    svamp_rows = load_hf("ChilleD/SVAMP", split="test", fallback_split="train")

    def extract_answer(ans_str: str) -> float | None:
        # GSM8K answers end with "#### <number>"
        m = re.search(r"####\s*([\d,\.\-]+)", str(ans_str))
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                return None
        try:
            return float(str(ans_str).replace(",", "").strip())
        except ValueError:
            return None

    def n_steps(solution: str) -> int:
        # proxy: number of sentences / lines in the solution
        lines = [l.strip() for l in str(solution).split("\n") if l.strip()]
        return len(lines)

    pool: list[dict] = []

    # GSM8K — up to 400 samples, stratify by difficulty (n_steps)
    gsm_prep = []
    for r in gsm_rows:
        q   = r.get("question", "")
        ans = r.get("answer", "")
        val = extract_answer(ans)
        if q and val is not None:
            steps = n_steps(ans)
            bin_  = min(4, (steps - 1) // 2)   # 1-2 steps=0, 3-4=1, 5-6=2, 7-8=3, 9+=4
            gsm_prep.append({"question": q, "answer": val, "source": "gsm8k",
                              "diff_bin": str(bin_)})
    gsm_sampled = stratified_sample(gsm_prep, "diff_bin", min(400, len(gsm_prep)), rng)
    pool.extend(gsm_sampled)

    # SVAMP — up to 100 samples
    svamp_prep = []
    for r in svamp_rows:
        q   = r.get("Question") or r.get("question") or r.get("Body", "") + " " + r.get("Question", "")
        ans = r.get("Answer") or r.get("answer")
        if q and ans is not None:
            try:
                val = float(str(ans).replace(",", "").strip())
                svamp_prep.append({"question": str(q).strip(), "answer": val,
                                   "source": "svamp", "diff_bin": "2"})
            except ValueError:
                pass
    svamp_sampled = stratified_sample(svamp_prep, "diff_bin", min(100, len(svamp_prep)), rng)
    pool.extend(svamp_sampled)

    rng.shuffle(pool)
    pool = pool[:target]

    rows = []
    for i, r in enumerate(pool):
        rows.append({
            "sample_id": f"maths_{i:04d}",
            "task":      "maths",
            "source":    r["source"],
            "prompt":    f"Solve the following math problem. Show your reasoning step by step, "
                         f"then provide the final numerical answer on the last line.\n\n"
                         f"Problem: {r['question']}",
            "reference": {"answer": r["answer"]},
        })
    return rows


def build_code_generation(target: int, rng: random.Random) -> list[dict]:
    print("  Loading HumanEval ...")
    he_rows = load_hf("openai/openai_humaneval", split="test")

    print("  Loading MBPP ...")
    mbpp_rows = load_hf("google-research-datasets/mbpp", "sanitized", split="test",
                        fallback_split="train")
    if not mbpp_rows:
        mbpp_rows = load_hf("google-research-datasets/mbpp", split="test",
                            fallback_split="train")

    pool: list[dict] = []

    # HumanEval — all 164
    for r in he_rows:
        prompt_text = r.get("prompt", "")
        canonical   = r.get("canonical_solution", "")
        task_id     = r.get("task_id", "")
        if prompt_text:
            pool.append({
                "source":    "humaneval",
                "prompt_raw": prompt_text,
                "canonical": canonical,
                "task_id":   task_id,
                "tests":     r.get("test", ""),
                "diff_bin":  "1",
            })

    # MBPP — up to 336
    for r in mbpp_rows:
        text = r.get("text") or r.get("prompt") or ""
        code = r.get("code") or r.get("canonical_solution") or ""
        tests = r.get("test_list") or r.get("tests") or []
        tid   = r.get("task_id") or r.get("id") or ""
        if text:
            pool.append({
                "source":    "mbpp",
                "prompt_raw": str(text).strip(),
                "canonical": str(code),
                "task_id":   str(tid),
                "tests":     tests,
                "diff_bin":  "2",
            })

    rng.shuffle(pool)
    pool = pool[:target]

    rows = []
    for i, r in enumerate(pool):
        if r["source"] == "humaneval":
            prompt = (f"Complete the following Python function. "
                      f"Return only the function implementation.\n\n{r['prompt_raw']}")
        else:
            prompt = (f"Write a Python function to {r['prompt_raw']}. "
                      f"Return only the function implementation.")
        rows.append({
            "sample_id": f"code_generation_{i:04d}",
            "task":      "code_generation",
            "source":    r["source"],
            "prompt":    prompt,
            "reference": {
                "task_id":   r["task_id"],
                "canonical": r["canonical"],
                "tests":     r["tests"],
            },
        })
    return rows


def build_instruction_following(target: int, rng: random.Random) -> list[dict]:
    print("  Loading IFEval ...")
    ifeval_rows = load_hf("google/IFEval", split="train")

    pool: list[dict] = []
    for r in ifeval_rows:
        prompt   = r.get("prompt", "")
        inst_ids = r.get("instruction_id_list") or []
        kwargs   = r.get("kwargs") or []
        if prompt and inst_ids:
            n_constraints = len(inst_ids)
            diff_bin = min(4, n_constraints - 1)
            pool.append({
                "prompt":      prompt,
                "inst_ids":    inst_ids,
                "kwargs":      kwargs,
                "diff_bin":    str(diff_bin),
                "source":      "ifeval",
            })

    sampled = stratified_sample(pool, "diff_bin", min(target, len(pool)), rng)

    rows = []
    for i, r in enumerate(sampled):
        rows.append({
            "sample_id": f"instruction_following_{i:04d}",
            "task":      "instruction_following",
            "source":    r["source"],
            "prompt":    r["prompt"],
            "reference": {
                "instruction_ids": r["inst_ids"],
                "kwargs":          r["kwargs"],
            },
        })
    return rows


def build_information_extraction(target: int, rng: random.Random) -> list[dict]:
    print("  Loading CoNLL-2003 ...")
    conll_rows = load_hf("eriktks/conll2003", split="test", fallback_split="validation")
    if not conll_rows:
        conll_rows = load_hf("conll2003", split="test", fallback_split="validation")

    print("  Loading SQuAD for extraction ...")
    squad_rows = load_hf("rajpurkar/squad", split="validation")

    NER_MAP = {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG", 4: "I-ORG",
               5: "B-LOC", 6: "I-LOC", 7: "B-MISC", 8: "I-MISC"}

    pool: list[dict] = []

    # CoNLL — 250 samples, stratify by number of entities
    for r in conll_rows:
        tokens = r.get("tokens", [])
        labels = r.get("ner_tags", [])
        if not tokens or not labels:
            continue
        sentence = " ".join(tokens)
        # Extract entity spans
        entities: list[dict] = []
        curr_ent: list[str] = []
        curr_type = ""
        for tok, lbl in zip(tokens, labels):
            tag = NER_MAP.get(lbl, "O")
            if tag.startswith("B-"):
                if curr_ent:
                    entities.append({"text": " ".join(curr_ent), "type": curr_type})
                curr_ent  = [tok]
                curr_type = tag[2:]
            elif tag.startswith("I-") and curr_ent:
                curr_ent.append(tok)
            else:
                if curr_ent:
                    entities.append({"text": " ".join(curr_ent), "type": curr_type})
                curr_ent  = []
                curr_type = ""
        if curr_ent:
            entities.append({"text": " ".join(curr_ent), "type": curr_type})

        if sentence.strip():
            n_ents  = len(entities)
            diff_bin = min(4, n_ents)
            pool.append({
                "type":     "ner",
                "text":     sentence,
                "entities": entities,
                "diff_bin": str(diff_bin),
                "source":   "conll2003",
            })

    conll_sampled = stratified_sample(pool, "diff_bin", min(250, len(pool)), rng)

    # SQuAD extractive — 250 samples
    squad_pool: list[dict] = []
    for r in squad_rows:
        ctx    = r.get("context", "")[:600]
        q      = r.get("question", "")
        ans    = (r.get("answers") or {}).get("text", [])
        ans_str = ans[0] if ans else ""
        if ctx and q and ans_str:
            squad_pool.append({
                "type":    "extractive_qa",
                "context": ctx,
                "question": q,
                "answer":  ans_str,
                "diff_bin": str(min(4, len(q.split()) // 5)),
                "source":  "squad",
            })

    squad_sampled = stratified_sample(squad_pool, "diff_bin", min(250, len(squad_pool)), rng)

    combined = conll_sampled + squad_sampled
    rng.shuffle(combined)
    combined = combined[:target]

    rows = []
    for i, r in enumerate(combined):
        if r["type"] == "ner":
            prompt = (f"Extract all named entities from the following text. "
                      f"List each entity and its type (PER=person, ORG=organization, "
                      f"LOC=location, MISC=miscellaneous).\n\nText: {r['text']}")
            reference = {"entities": r["entities"]}
        else:
            prompt = (f"Extract the answer to the question from the context below. "
                      f"Copy the answer exactly as it appears in the text.\n\n"
                      f"Context: {r['context']}\n\nQuestion: {r['question']}")
            reference = {"contains": [r["answer"].lower()]}

        rows.append({
            "sample_id": f"information_extraction_{i:04d}",
            "task":      "information_extraction",
            "source":    r["source"],
            "prompt":    prompt,
            "reference": reference,
        })
    return rows


def build_retrieval_grounded(target: int, rng: random.Random) -> list[dict]:
    print("  Loading SQuAD v1.1 ...")
    squad_rows = load_hf("rajpurkar/squad", split="validation")

    print("  Loading TriviaQA ...")
    trivia_rows = load_hf("mandarjoshi/trivia_qa", "rc", split="validation",
                          fallback_split="train")

    pool: list[dict] = []

    # SQuAD — 250 samples
    for r in squad_rows:
        ctx  = r.get("context", "")[:800]
        q    = r.get("question", "")
        ans  = (r.get("answers") or {}).get("text", [])
        if ctx and q and ans:
            pool.append({
                "context":  ctx,
                "question": q,
                "answers":  ans,
                "source":   "squad",
                "diff_bin": str(min(4, len(ctx.split()) // 60)),
            })

    squad_sampled = stratified_sample(pool, "diff_bin", min(250, len(pool)), rng)

    # TriviaQA — 250 samples
    trivia_pool: list[dict] = []
    for r in trivia_rows:
        q      = r.get("question", "")
        ans    = r.get("answer", {})
        val    = ans.get("value", "") if isinstance(ans, dict) else str(ans)
        aliases = (ans.get("aliases", []) if isinstance(ans, dict) else []) or []

        # Get first evidence passage
        evidence = r.get("search_results") or r.get("entity_pages") or {}
        passages = []
        if isinstance(evidence, dict):
            passages = evidence.get("search_context", []) or evidence.get("wiki_context", []) or []
        ctx = str(passages[0])[:800] if passages else ""

        if q and val and ctx:
            trivia_pool.append({
                "context":  ctx,
                "question": q,
                "answers":  [val] + aliases[:2],
                "source":   "trivia_qa",
                "diff_bin": "2",
            })

    trivia_sampled = stratified_sample(trivia_pool, "diff_bin", min(250, len(trivia_pool)), rng)

    combined = squad_sampled + trivia_sampled
    rng.shuffle(combined)
    combined = combined[:target]

    rows = []
    for i, r in enumerate(combined):
        rows.append({
            "sample_id": f"retrieval_grounded_{i:04d}",
            "task":      "retrieval_grounded",
            "source":    r["source"],
            "prompt":    f"Use only the provided context to answer the question. "
                         f"If the answer is not in the context, say 'not found'.\n\n"
                         f"Context: {r['context']}\n\nQuestion: {r['question']}",
            "reference": {"contains": [a.lower() for a in r["answers"][:3]]},
        })
    return rows


def build_summarization(target: int, rng: random.Random) -> list[dict]:
    print("  Loading CNN/DailyMail ...")
    cnn_rows = load_hf("abisee/cnn_dailymail", "3.0.0", split="test")

    print("  Loading XSum ...")
    xsum_rows = load_hf("EdinburghNLP/xsum", split="test")

    print("  Loading SAMSum ...")
    sam_rows = load_hf("Samsung/samsum", split="test", fallback_split="validation")

    pool: list[dict] = []

    def word_count(text: str) -> int:
        return len(str(text).split())

    # CNN/DM — 200
    cnn_prep = []
    for r in cnn_rows:
        article = r.get("article", "")
        hl      = r.get("highlights", "")
        if article and hl:
            wc = word_count(article)
            cnn_prep.append({
                "text":      article[:1200],
                "reference": hl,
                "source":    "cnn_dailymail",
                "max_words": 60,
                "diff_bin":  str(min(4, wc // 150)),
            })
    cnn_sampled = stratified_sample(cnn_prep, "diff_bin", min(200, len(cnn_prep)), rng)
    pool.extend(cnn_sampled)

    # XSum — 200
    xsum_prep = []
    for r in xsum_rows:
        doc = r.get("document", "")
        summ = r.get("summary", "")
        if doc and summ:
            wc = word_count(doc)
            xsum_prep.append({
                "text":      doc[:1200],
                "reference": summ,
                "source":    "xsum",
                "max_words": 30,
                "diff_bin":  str(min(4, wc // 100)),
            })
    xsum_sampled = stratified_sample(xsum_prep, "diff_bin", min(200, len(xsum_prep)), rng)
    pool.extend(xsum_sampled)

    # SAMSum — 100
    sam_prep = []
    for r in sam_rows:
        dialogue = r.get("dialogue", "")
        summ     = r.get("summary", "")
        if dialogue and summ:
            sam_prep.append({
                "text":      dialogue,
                "reference": summ,
                "source":    "samsum",
                "max_words": 40,
                "diff_bin":  str(min(4, word_count(dialogue) // 50)),
            })
    sam_sampled = stratified_sample(sam_prep, "diff_bin", min(100, len(sam_prep)), rng)
    pool.extend(sam_sampled)

    rng.shuffle(pool)
    pool = pool[:target]

    rows = []
    for i, r in enumerate(pool):
        max_w = r["max_words"]
        src   = r["source"]
        if src == "xsum":
            instruction = f"Summarize the following article in one sentence (maximum {max_w} words)."
        elif src == "samsum":
            instruction = f"Summarize the following conversation in 1-2 sentences (maximum {max_w} words)."
        else:
            instruction = f"Summarize the following article in 3-4 sentences (maximum {max_w} words)."

        rows.append({
            "sample_id": f"summarization_{i:04d}",
            "task":      "summarization",
            "source":    src,
            "prompt":    f"{instruction}\n\n{r['text']}",
            "reference": {
                "summary":   r["reference"],
                "max_words": max_w,
            },
        })
    return rows


def build_text_generation(target: int, rng: random.Random) -> list[dict]:
    print("  Loading CommonGen ...")
    cg_rows = load_hf("allenai/common_gen", split="test", fallback_split="validation")
    if not cg_rows:
        cg_rows = load_hf("common_gen", split="test", fallback_split="validation")

    print("  Loading ROCStories ...")
    roc_rows = load_hf("Ximing/ROCStories", split="test", fallback_split="validation")
    if not roc_rows:
        roc_rows = load_hf("story_cloze", "2016", split="test", fallback_split="validation")

    pool: list[dict] = []

    # CommonGen — 300
    cg_prep = []
    seen_concepts: set[str] = set()
    for r in cg_rows:
        concepts = r.get("concepts") or r.get("concept_set") or []
        if isinstance(concepts, str):
            concepts = concepts.split("#")
        concepts = [c.strip() for c in concepts if c.strip()]
        target_text = r.get("target") or ""
        key = " ".join(sorted(concepts))
        if concepts and key not in seen_concepts:
            seen_concepts.add(key)
            n_con = len(concepts)
            cg_prep.append({
                "concepts":    concepts,
                "target":      target_text,
                "source":      "commongen",
                "diff_bin":    str(min(4, n_con - 2)),
            })
    cg_sampled = stratified_sample(cg_prep, "diff_bin", min(300, len(cg_prep)), rng)
    pool.extend(cg_sampled)

    # ROCStories — 200: complete the story given first 4 sentences
    roc_prep = []
    for r in roc_rows:
        sentences = []
        for k in ["sentence1", "sentence2", "sentence3", "sentence4"]:
            s = r.get(k, "")
            if s:
                sentences.append(s)
        ending = r.get("sentence5") or r.get("correct_ending") or r.get("RandomFifthSentenceQuiz1") or ""
        if len(sentences) >= 3 and ending:
            roc_prep.append({
                "sentences": sentences,
                "ending":    ending,
                "source":    "rocstories",
                "diff_bin":  "2",
            })
    roc_sampled = stratified_sample(roc_prep, "diff_bin", min(200, len(roc_prep)), rng)
    pool.extend(roc_sampled)

    rng.shuffle(pool)
    pool = pool[:target]

    rows = []
    for i, r in enumerate(pool):
        if r["source"] == "commongen":
            concepts = r["concepts"]
            prompt = (f"Write 2-3 sentences that naturally use ALL of the following words: "
                      f"{', '.join(concepts)}.\n"
                      f"Every word in the list must appear in your response.")
            reference = {
                "required_concepts": concepts,
                "example":           r.get("target", ""),
            }
        else:
            story_so_far = " ".join(r["sentences"])
            prompt = (f"Continue the following story with one final sentence that "
                      f"provides a logical and coherent conclusion.\n\n"
                      f"Story so far: {story_so_far}")
            reference = {
                "example_ending": r["ending"],
                "requires_coherence": True,
            }

        rows.append({
            "sample_id": f"text_generation_{i:04d}",
            "task":      "text_generation",
            "source":    r["source"],
            "prompt":    prompt,
            "reference": reference,
        })
    return rows


# ── orchestrator ──────────────────────────────────────────────────────────────

BUILDERS = {
    "classification":       build_classification,
    "maths":                build_maths,
    "code_generation":      build_code_generation,
    "instruction_following": build_instruction_following,
    "information_extraction": build_information_extraction,
    "retrieval_grounded":   build_retrieval_grounded,
    "summarization":        build_summarization,
    "text_generation":      build_text_generation,
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tasks",  nargs="+", default=list(BUILDERS.keys()),
                   help="Which tasks to build (default: all)")
    p.add_argument("--target", type=int, default=500,
                   help="Target samples per task (default: 500)")
    p.add_argument("--seed",   type=int, default=42,
                   help="Random seed for reproducibility (default: 42)")
    p.add_argument("--overwrite", action="store_true",
                   help="Overwrite existing ground truth files")
    args = p.parse_args()

    rng = random.Random(args.seed)

    invalid = [t for t in args.tasks if t not in BUILDERS]
    if invalid:
        print(f"Unknown tasks: {invalid}")
        sys.exit(1)

    GT_DIR.mkdir(parents=True, exist_ok=True)

    for task in args.tasks:
        out = GT_DIR / f"{task}.jsonl"
        if out.exists() and not args.overwrite:
            existing = sum(1 for _ in out.open(encoding="utf-8"))
            print(f"\n[{task}] Already exists ({existing} rows) — skipping. "
                  f"Use --overwrite to replace.")
            continue

        print(f"\n[{task}] Building ground truth ...")
        try:
            rows = BUILDERS[task](args.target, rng)
            save_gt(task, rows)
            print(f"[{task}] Done: {len(rows)} rows from "
                  f"{set(r['source'] for r in rows)}")
        except Exception as e:
            print(f"[{task}] ERROR: {e}")
            import traceback; traceback.print_exc()

    print("\nAll tasks complete.")
    print(f"Ground truth saved to: {GT_DIR}")


if __name__ == "__main__":
    main()
