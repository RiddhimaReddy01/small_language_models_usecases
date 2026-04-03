#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "model_runs" / "benchmark_75"
MODEL_RUNS = LEGACY if LEGACY.exists() else ROOT / "model_runs"
GROUND_TRUTH_DIR = ROOT / "data" / "ground_truth"

CANONICAL_MODELS = [
    "llama_llama-3.3-70b-versatile",
    "qwen2.5_1.5b",
    "phi3_mini",
    "tinyllama_1.1b",
]

REFERENCE_BANK = {
    "classification": {
        "Classify sentiment: 'This movie was amazing!'": {"label": "positive"},
        "Classify sentiment: 'Terrible experience, never again'": {"label": "negative"},
        "Classify sentiment: 'It was okay, nothing special'": {"label": "neutral"},
        "Categorize text: Political or Sports?": {"choices": ["political", "sports"]},
        "Is this email spam or not spam?": {"choices": ["spam", "not spam"]},
    },
    "maths": {
        "Solve: 2x + 5 = 13": {"answer": 4.0},
        "Calculate: (12 + 8) * 3 - 5": {"answer": 55.0},
        "What is the square root of 144?": {"answer": 12.0},
        "Solve: 3x^2 + 2x - 1 = 0": {"answers_text": ["1/3", "-1"]},
        "Calculate: (5! + 3!) / 4": {"answer": 31.5},
    },
    "information_extraction": {
        "Extract person name: 'John Smith works at Microsoft'": {"contains": ["john smith"]},
        "Extract location: 'The meeting is in New York'": {"contains": ["new york"]},
        "Extract date: 'Event scheduled for March 15, 2025'": {"contains": ["march 15, 2025"]},
        "Extract organization: 'Alice is CEO of TechCorp'": {"contains": ["techcorp"]},
        "Extract all entities: 'Bob visited Paris in 2023'": {"contains": ["bob", "paris", "2023"]},
    },
    "instruction_following": {
        "Count to 5 starting from 1": {"sequence": ["1", "2", "3", "4", "5"]},
        "List 3 colors in alphabetical order": {"ordered_contains": ["blue", "green", "red"]},
        "Translate 'hello' to Spanish": {"contains": ["hola"]},
        "Write the alphabet backwards": {"contains": ["zyx"]},
        "List months of the year in order": {"ordered_contains": ["january", "february", "march", "april"]},
    },
    "retrieval_grounded": {
        "Based on context, answer: What year was X invented?": {"requires_context_ack": True},
        "Using the provided text, who is the main character?": {"requires_context_ack": True},
        "From the document, what is the capital of France?": {"contains": ["paris"]},
        "According to the passage, what happened first?": {"requires_context_ack": True},
        "From the context, what is the definition of X?": {"requires_context_ack": True},
    },
    "summarization": {
        "Summarize: The quick brown fox jumps over the lazy dog. The dog was sleeping peacefully.": {"contains": ["fox", "dog"]},
        "Summarize article about climate change in 2-3 sentences": {"contains": ["climate"]},
        "Summarize the key points of quantum mechanics": {"contains": ["quantum"]},
        "Give a brief summary of the Industrial Revolution": {"contains": ["industrial", "revolution"]},
        "Summarize COVID-19 pandemic timeline": {"contains": ["covid", "pandemic"]},
    },
    "code_generation": {
        "Write a function to reverse a string": {"kind": "reverse_string"},
        "Implement bubble sort algorithm": {"kind": "bubble_sort"},
        "Create a function to calculate factorial": {"kind": "factorial"},
        "Write code to parse JSON": {"kind": "parse_json"},
        "Implement binary search": {"kind": "binary_search"},
    },
    "text_generation": {
        "Explain quantum computing in simple terms": {"contains": ["quantum"]},
        "What are the benefits of renewable energy?": {"contains": ["renewable", "energy"]},
        "Describe the process of photosynthesis": {"contains": ["photosynthesis"]},
        "Write a short story about a robot": {"contains": ["robot"]},
        "Explain what machine learning is": {"contains": ["machine learning"]},
    },
}


def _strip_example(prompt: str) -> str:
    return re.sub(r"\s*\(Example \d+\)\s*$", "", (prompt or "").strip())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("sample_id", ""))
        if not sid:
            continue
        existing = by_sample.get(sid)
        if existing is None:
            by_sample[sid] = row
            continue
        ts_new = str(row.get("timestamp") or "")
        ts_old = str(existing.get("timestamp") or "")
        if ts_new >= ts_old:
            by_sample[sid] = row
    return list(by_sample.values())


def _pick_source_outputs(task_dir: Path) -> Path | None:
    for model_key in CANONICAL_MODELS:
        path = task_dir / model_key / "outputs.jsonl"
        if path.exists():
            return path
    return None


def main() -> int:
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    total_tasks = 0
    for task, prompt_bank in REFERENCE_BANK.items():
        task_dir = MODEL_RUNS / task
        if not task_dir.exists():
            continue
        src = _pick_source_outputs(task_dir)
        if src is None:
            continue
        rows = _dedupe_rows(_load_jsonl(src))
        missing: set[str] = set()
        out_rows: list[dict[str, Any]] = []
        for row in rows:
            sample_id = str(row.get("sample_id", ""))
            prompt = _strip_example(str(row.get("prompt", "")))
            reference = prompt_bank.get(prompt)
            if not sample_id:
                continue
            if not reference:
                missing.add(prompt)
                continue
            out_rows.append(
                {
                    "sample_id": sample_id,
                    "task": task,
                    "prompt": prompt,
                    "reference": reference,
                }
            )
        if missing:
            missing_preview = sorted(missing)[:5]
            raise RuntimeError(
                f"Unmapped prompts for task '{task}' ({len(missing)}). "
                f"First examples: {missing_preview}"
            )
        out_path = GROUND_TRUTH_DIR / f"{task}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for item in sorted(out_rows, key=lambda x: x["sample_id"]):
                handle.write(json.dumps(item) + "\n")
        print(f"Wrote {out_path} ({len(out_rows)} rows)")
        total_tasks += 1
    print(f"Ground truth bootstrap complete for {total_tasks} tasks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
