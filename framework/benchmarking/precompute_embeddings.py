from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return out


def _split_context_query(prompt: str, task: str) -> tuple[str, str]:
    def _fallback_segments(text: str) -> tuple[str, str]:
        sentences: list[str] = []
        cur: list[str] = []
        for ch in text:
            cur.append(ch)
            if ch in ".!?":
                s = "".join(cur).strip()
                if s:
                    sentences.append(s)
                cur = []
        tail = "".join(cur).strip()
        if tail:
            sentences.append(tail)
        if len(sentences) >= 2:
            return " ".join(sentences[:-1]).strip(), sentences[-1].strip()
        toks = text.split()
        if len(toks) >= 8:
            split_at = max(1, int(len(toks) * 0.7))
            return " ".join(toks[:split_at]).strip(), " ".join(toks[split_at:]).strip()
        return text.strip(), text.strip()

    lower = prompt.lower()
    markers = ["question:", "query:", "instruction:", "task:"]
    if task == "summarization":
        markers = ["summary:", "summarize", "write a summary"]
    idx = -1
    for marker in markers:
        j = lower.find(marker)
        if j != -1 and (idx == -1 or j < idx):
            idx = j
    if idx == -1:
        return _fallback_segments(prompt)
    context = prompt[:idx].strip()
    query = prompt[idx:].strip()
    if not context or not query:
        return _fallback_segments(prompt)
    return context, query


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main() -> int:
    parser = argparse.ArgumentParser(description="Precompute sentence-transformer embeddings and query-context cosine features.")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--model-path", default="model_runs/local_models/all-MiniLM-L6-v2")
    parser.add_argument("--output-root", default="model_runs/sddf_training_splits_slm_only/embedding_cache_v2")
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(str(Path(args.model_path).resolve()))
    exclude_model_substrings = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]

    report: dict[str, Any] = {"processed": 0, "files": []}
    for task_dir in sorted([p for p in splits_root.iterdir() if p.is_dir() and (p / "split_query_ids.json").exists()]):
        task = task_dir.name
        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            if any(substr and substr in model_dir.name for substr in exclude_model_substrings):
                continue
            model_name = model_dir.name
            for split in ("train", "val", "test"):
                in_path = model_dir / f"{split}.jsonl"
                rows = _read_jsonl(in_path)
                if not rows:
                    continue
                contexts: list[str] = []
                queries: list[str] = []
                keys: list[tuple[str, str]] = []
                for row in rows:
                    prompt = str(row.get("prompt", ""))
                    context, query = _split_context_query(prompt=prompt, task=task)
                    qid = str(row.get("query_id", ""))
                    sid = str(row.get("sample_id", ""))
                    keys.append((qid, sid))
                    contexts.append(context if context else prompt)
                    queries.append(query)

                ctx_emb = model.encode(contexts, convert_to_numpy=True, show_progress_bar=False)
                qry_emb = model.encode(queries, convert_to_numpy=True, show_progress_bar=False)

                out_rows = []
                for i in range(len(rows)):
                    out_rows.append(
                        {
                            "query_id": keys[i][0],
                            "sample_id": keys[i][1],
                            "embedding_query_context_cosine": _cos(qry_emb[i], ctx_emb[i]),
                        }
                    )

                out_dir = output_root / task / model_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{split}_embedding_features.jsonl"
                with out_path.open("w", encoding="utf-8", newline="\n") as f:
                    for row in out_rows:
                        f.write(json.dumps(row, ensure_ascii=True) + "\n")

                report["processed"] += len(out_rows)
                report["files"].append(str(out_path))

    report_path = output_root / "embedding_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote: {report_path}")
    print(f"Rows processed: {report['processed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
