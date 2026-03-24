import json
from pathlib import Path
import random
from typing import Dict, List, Tuple


def read_jsonl(path: str) -> List[Dict]:
    items = []
    resolved_path = Path(path)
    if not resolved_path.exists() and "processed" in resolved_path.parts:
        fallback = resolved_path.parent.parent / resolved_path.name
        if fallback.exists():
            resolved_path = fallback
    if not resolved_path.exists():
        return items
    with resolved_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items


def compute_stratified_targets(sample_size: int) -> Tuple[int, int, int]:
    base = sample_size // 3
    remainder = sample_size % 3
    targets = [base, base, base]
    for idx in range(remainder):
        targets[idx] += 1
    return tuple(targets)


def stratified_sample(items: List[Dict], sample_size: int, rng: random.Random) -> List[Dict]:
    by_diff = {"easy": [], "medium": [], "hard": []}
    for item in items:
        difficulty = item.get("difficulty")
        if difficulty not in by_diff:
            raise ValueError(f"Unsupported difficulty '{difficulty}'. Expected one of: easy, medium, hard.")
        by_diff[difficulty].append(item)

    target_easy, target_medium, target_hard = compute_stratified_targets(sample_size)
    targets = {"easy": target_easy, "medium": target_medium, "hard": target_hard}
    sampled = []
    for difficulty in ["easy", "medium", "hard"]:
        pool = by_diff[difficulty]
        need = targets[difficulty]
        if len(pool) < need:
            raise ValueError(
                f"Dataset does not contain enough '{difficulty}' examples for sample_size={sample_size}. Need {need}, found {len(pool)}."
            )
        sampled.extend(rng.sample(pool, need))
    rng.shuffle(sampled)
    return sampled


def load_dataset_config(path: str, sample_size: int, seed: int) -> List[Dict]:
    rng = random.Random(seed)
    items = read_jsonl(path)
    if not items:
        raise FileNotFoundError(f"Dataset not found or empty: {path}")

    normalized = []
    for idx, item in enumerate(items):
        if "question" not in item or "answer" not in item or "difficulty" not in item:
            raise ValueError(
                f"Dataset item #{idx} in {path} must include 'question', 'answer', and 'difficulty'."
            )
        record = dict(item)
        record.setdefault("source", "dataset")
        normalized.append(record)

    return stratified_sample(normalized, sample_size, rng)
