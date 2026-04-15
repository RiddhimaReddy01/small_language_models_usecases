from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXCLUDED_TASK_DIRS = {"benchmarking", "business_analytics", "difficulty_weights"}
TRAILING_INT_RE = re.compile(r"^(.*?)(\d+)$")


def _stable_bucket(canonical_id: str, seed: str) -> float:
    raw = f"{seed}:{canonical_id}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value / float(2**64)


def _assign_split(canonical_id: str, seed: str, train_ratio: float, val_ratio: float) -> str:
    bucket = _stable_bucket(canonical_id, seed)
    if bucket < train_ratio:
        return "train"
    if bucket < (train_ratio + val_ratio):
        return "val"
    return "test"


def _iter_clean_records(outputs_path: Path) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for idx, line in enumerate(outputs_path.read_text(encoding="utf-8").splitlines()):
        row = line.strip()
        if not row:
            continue
        try:
            parsed = json.loads(row)
        except json.JSONDecodeError:
            continue

        canonical_id = _canonical_id(parsed)
        if not canonical_id:
            continue
        if parsed.get("status") != "success":
            continue
        if not bool(parsed.get("valid")):
            continue

        # Keep first clean row per canonical_id for deterministic behavior.
        if canonical_id not in records:
            parsed["_line_index"] = idx
            parsed["_canonical_id"] = canonical_id
            records[canonical_id] = parsed

    return list(records.values())


def _canonical_id(row: dict[str, Any]) -> str:
    task = str(row.get("task", "")).strip()
    sample_id = str(row.get("sample_id", "")).strip()
    query_id = str(row.get("query_id", "")).strip()

    if sample_id:
        match = TRAILING_INT_RE.match(sample_id)
        if match:
            idx = int(match.group(2))
            if task:
                return f"{task}:{idx}"
            return str(idx)
        if task:
            return f"{task}:{sample_id}"
        return sample_id

    if task and query_id:
        return f"{task}:{query_id}"
    return query_id


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            row = {k: v for k, v in row.items() if k not in {"_line_index", "_canonical_id"}}
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def build_splits(
    model_runs_dir: Path,
    output_dir: Path,
    seed: str,
    train_ratio: float,
    val_ratio: float,
    max_common_per_task: int | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "seed": seed,
        "train_ratio": train_ratio,
        "val_ratio": val_ratio,
        "test_ratio": 1.0 - train_ratio - val_ratio,
        "tasks": {},
    }

    for task_dir in sorted([p for p in model_runs_dir.iterdir() if p.is_dir() and p.name not in EXCLUDED_TASK_DIRS]):
        model_to_rows: dict[str, list[dict[str, Any]]] = {}
        model_to_ids: dict[str, set[str]] = {}

        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            outputs_path = model_dir / "outputs.jsonl"
            if not outputs_path.exists():
                continue
            clean_rows = _iter_clean_records(outputs_path)
            if not clean_rows:
                continue
            model_to_rows[model_dir.name] = clean_rows
            model_to_ids[model_dir.name] = {str(r["_canonical_id"]) for r in clean_rows}

        if len(model_to_rows) < 2:
            continue

        common_ids = set.intersection(*model_to_ids.values())
        ordered_common_ids = sorted(common_ids)
        if max_common_per_task is not None:
            ordered_common_ids = ordered_common_ids[:max_common_per_task]
        common_id_set = set(ordered_common_ids)

        split_ids: dict[str, list[str]] = {"train": [], "val": [], "test": []}
        for canonical_id in ordered_common_ids:
            split = _assign_split(canonical_id, seed=seed, train_ratio=train_ratio, val_ratio=val_ratio)
            split_ids[split].append(canonical_id)

        task_output_dir = output_dir / task_dir.name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        (task_output_dir / "split_query_ids.json").write_text(
            json.dumps(split_ids, indent=2),
            encoding="utf-8",
        )

        task_meta: dict[str, Any] = {
            "models": {},
            "common_query_count": len(ordered_common_ids),
            "split_sizes": {k: len(v) for k, v in split_ids.items()},
        }

        for model_name, rows in sorted(model_to_rows.items()):
            model_dir = task_output_dir / model_name
            by_split: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
            for row in rows:
                canonical_id = str(row["_canonical_id"])
                if canonical_id not in common_id_set:
                    continue
                split = _assign_split(canonical_id, seed=seed, train_ratio=train_ratio, val_ratio=val_ratio)
                by_split[split].append(row)

            for split_name in ("train", "val", "test"):
                split_rows = sorted(by_split[split_name], key=lambda r: str(r["_canonical_id"]))
                _write_jsonl(model_dir / f"{split_name}.jsonl", split_rows)

            task_meta["models"][model_name] = {
                "clean_rows_before_intersection": len(rows),
                "rows_after_intersection": sum(len(v) for v in by_split.values()),
                "split_sizes": {k: len(v) for k, v in by_split.items()},
            }

        summary["tasks"][task_dir.name] = task_meta

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build clean deterministic train/val/test splits with shared query IDs across models.")
    parser.add_argument("--model-runs-dir", default="model_runs")
    parser.add_argument("--output-dir", default="model_runs/clean_deterministic_splits")
    parser.add_argument("--seed", default="slm-clean-v1")
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--max-common-per-task", type=int, default=None)
    args = parser.parse_args()

    if args.train_ratio <= 0 or args.val_ratio <= 0 or (args.train_ratio + args.val_ratio) >= 1:
        raise ValueError("Ratios must satisfy: train_ratio > 0, val_ratio > 0, train_ratio + val_ratio < 1")

    model_runs_dir = Path(args.model_runs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_splits(
        model_runs_dir=model_runs_dir,
        output_dir=output_dir,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        max_common_per_task=args.max_common_per_task,
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote deterministic clean splits to: {output_dir}")
    print(f"Tasks processed: {len(summary['tasks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
