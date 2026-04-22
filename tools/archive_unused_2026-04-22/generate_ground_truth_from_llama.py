#!/usr/bin/env python3
"""Auto-generate minimal ground truth using Llama 70B outputs as reference."""

import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "model_runs"
GT_DIR = ROOT / "data" / "ground_truth"

GT_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    "classification", "maths", "code_generation", "instruction_following",
    "information_extraction", "retrieval_grounded", "summarization", "text_generation",
]


def extract_number(text: str) -> str | None:
    """Extract the last number from text (for maths ground truth)."""
    nums = re.findall(r"[+-]?\d+(?:\.\d+)?", text.replace(",", ""))
    return nums[-1] if nums else None


def extract_concepts(text: str) -> list[str]:
    """Extract likely concept words from generated text (for text_generation)."""
    # Simple heuristic: extract nouns/verbs (words not in stop list)
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "in", "of", "to", "and", "or", "but"}
    words = re.findall(r"\b[a-z]+\b", text.lower())
    return [w for w in set(words) if w not in stop and len(w) > 2][:4]


def extract_constraints_from_prompt(task: str, prompt: str) -> dict:
    """Infer constraints from prompt text (for instruction_following)."""
    # Minimal extraction: identify constraint keywords from prompt
    kwargs = {}

    if "word" in prompt.lower():
        m = re.search(r"(\d+)\s+word", prompt)
        if m:
            kwargs["num_words"] = int(m.group(1))

    if "sentence" in prompt.lower():
        m = re.search(r"(\d+)\s+sentence", prompt)
        if m:
            kwargs["num_sentences"] = int(m.group(1))

    if "paragraph" in prompt.lower():
        m = re.search(r"(\d+)\s+paragraph", prompt)
        if m:
            kwargs["num_paragraphs"] = int(m.group(1))

    if "quote" in prompt.lower() or "quotation" in prompt.lower():
        return {"instruction_ids": ["quotation:start_end"], "kwargs": [{}]}

    if kwargs:
        # Guess instruction ID based on kwargs
        if "num_words" in kwargs:
            return {"instruction_ids": ["length_constraints:number_words"], "kwargs": [kwargs]}
        if "num_sentences" in kwargs:
            return {"instruction_ids": ["length_constraints:number_sentences"], "kwargs": [kwargs]}
        if "num_paragraphs" in kwargs:
            return {"instruction_ids": ["length_constraints:number_paragraphs"], "kwargs": [kwargs]}

    # Fallback: no specific constraint detected
    return {"instruction_ids": [], "kwargs": [{}]}


def load_outputs(task: str, model: str, split: str) -> list[dict]:
    """Load model outputs for a task."""
    path = RUNS_DIR / task / model / f"outputs_{split}.jsonl"
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_all_outputs(task: str, model: str) -> list[dict]:
    """Load model outputs for a task across all splits."""
    rows = []
    for split in ["train", "val", "test"]:
        rows.extend(load_outputs(task, model, split))
    return rows


def main():
    # Collect unique prompts (keyed by sample_id) across all outputs
    samples: dict[str, dict] = defaultdict(lambda: {
        "task": None, "prompt": None, "llama_output": None, "split": None
    })

    print("Collecting samples from model outputs...")
    for task in TASKS:
        print(f"  {task}...", end=" ", flush=True)

        # Get Llama outputs across all splits
        llama_rows = load_all_outputs(task, "llama_llama-3.3-70b-versatile")
        for row in llama_rows:
            sid = row["sample_id"]
            if sid not in samples:
                samples[sid]["task"] = task
                samples[sid]["prompt"] = row.get("prompt", "")
                samples[sid]["llama_output"] = row.get("raw_output", "")
                samples[sid]["split"] = row.get("split", "test")  # default to test if missing

        print(f"found {sum(1 for s in samples.values() if s['task'] == task)} samples")

    # Generate ground truth for each task
    for task in TASKS:
        task_samples = [s for s in samples.values() if s["task"] == task]
        if not task_samples:
            print(f"  SKIP {task} (no samples)")
            continue

        gt_rows = []
        for sample in task_samples:
            sample_id = [k for k, v in samples.items() if v == sample][0]
            prompt = sample["prompt"]
            llama_output = sample["llama_output"]

            # Task-specific reference generation
            if task == "maths":
                answer = extract_number(llama_output)
                reference = {"answer": answer if answer else "0"}

            elif task == "code_generation":
                # Use Llama's code as reference (simplified)
                reference = {"tests": "# Reference from Llama output"}

            elif task == "text_generation":
                concepts = extract_concepts(llama_output)
                reference = {"required_concepts": concepts if concepts else ["word"]}

            elif task == "instruction_following":
                reference = extract_constraints_from_prompt(task, prompt)

            elif task == "classification":
                # Extract label from Llama output (first capitalized word)
                m = re.search(r"\b([A-Z][a-z]+)\b", llama_output)
                label = m.group(1).lower() if m else "unknown"
                reference = {"label": label}

            elif task == "information_extraction":
                reference = {"reference": llama_output[:200]}  # First 200 chars

            elif task == "retrieval_grounded":
                reference = {"reference": llama_output[:100]}  # Entity or short answer

            elif task == "summarization":
                reference = {"reference": llama_output[:300]}  # First 300 chars as reference summary

            else:
                reference = {"reference": llama_output}

            gt_rows.append({
                "sample_id": sample_id,
                "task": task,
                "source": "auto-generated",
                "split": sample.get("split", "test"),  # preserve split from outputs
                "prompt": prompt,
                "reference": reference,
            })

        # Write ground truth file
        gt_file = GT_DIR / f"{task}.jsonl"
        with open(gt_file, "w", encoding="utf-8") as f:
            for row in gt_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"  WROTE {task}.jsonl ({len(gt_rows)} samples)")


if __name__ == "__main__":
    main()
    print("\nGround truth auto-generated from Llama 70B outputs.")
    print(f"Location: {GT_DIR}")
