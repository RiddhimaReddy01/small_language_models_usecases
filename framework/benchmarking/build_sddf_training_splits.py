from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXCLUDED = {"benchmarking", "business_analytics", "difficulty_weights", "clean_deterministic_splits"}
SPLIT_FILES = ("outputs_train.jsonl", "outputs_val.jsonl", "outputs_test.jsonl", "outputs.jsonl")


def _normalize_sample_id(task: str, sample_id: str) -> str:
    sample_id = (sample_id or "").strip()
    if not sample_id:
        return ""
    i = len(sample_id) - 1
    while i >= 0 and sample_id[i].isdigit():
        i -= 1
    if i == len(sample_id) - 1:
        return f"{task}:{sample_id}"
    prefix = sample_id[: i + 1]
    digits = sample_id[i + 1 :]
    idx = int(digits) if digits else 0
    return f"{task}:{prefix}{idx}"


def _canonical_id(task: str, row: dict[str, Any]) -> str:
    sid = _normalize_sample_id(task, str(row.get("sample_id", "")))
    if sid:
        return sid
    qid = str(row.get("query_id", "")).strip()
    if qid:
        return f"{task}:{qid}"
    return ""


def _is_fail(row: dict[str, Any]) -> int:
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _read_rows(model_dir: Path, task: str) -> dict[str, dict[str, Any]]:
    # Priority order: train, val, test, then fallback outputs.
    by_id: dict[str, dict[str, Any]] = {}
    for filename in SPLIT_FILES:
        fp = model_dir / filename
        if not fp.exists():
            continue
        for line in fp.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                row = json.loads(s)
            except json.JSONDecodeError:
                continue
            cid = _canonical_id(task, row)
            if not cid:
                continue
            if cid not in by_id:
                row["_canonical_id"] = cid
                row["_fail"] = _is_fail(row)
                by_id[cid] = row
    return by_id


def _hash_bucket(seed: str, cid: str) -> float:
    dig = hashlib.sha256(f"{seed}:{cid}".encode("utf-8")).digest()
    val = int.from_bytes(dig[:8], byteorder="big", signed=False)
    return val / float(2**64)


def _initial_split(seed: str, ids: list[str], train_ratio: float, val_ratio: float) -> dict[str, str]:
    out: dict[str, str] = {}
    for cid in ids:
        b = _hash_bucket(seed, cid)
        if b < train_ratio:
            out[cid] = "train"
        elif b < train_ratio + val_ratio:
            out[cid] = "val"
        else:
            out[cid] = "test"
    return out


def _repair_train_collapse(
    assignment: dict[str, str],
    ids_sorted: list[str],
    model_rows: dict[str, dict[str, Any]],
) -> dict[str, str]:
    # Keep shared assignment across models by editing ids globally.
    # For each model, if train has only one class but global ids include both, move one missing-class id into train.
    for _ in range(3):
        changed = False
        for _, rows in model_rows.items():
            train_ids = [cid for cid in ids_sorted if assignment[cid] == "train"]
            train_labels = [rows[cid]["_fail"] for cid in train_ids]
            if not train_labels:
                continue
            unique_train = set(train_labels)
            all_labels = [rows[cid]["_fail"] for cid in ids_sorted]
            unique_all = set(all_labels)
            if len(unique_train) >= 2 or len(unique_all) < 2:
                continue
            missing = 1 if 1 not in unique_train else 0
            donor = None
            for cid in ids_sorted:
                if assignment[cid] != "train" and rows[cid]["_fail"] == missing:
                    donor = cid
                    break
            if donor is None:
                continue
            eject = None
            for cid in reversed(train_ids):
                if rows[cid]["_fail"] != missing:
                    eject = cid
                    break
            if eject is None:
                continue
            assignment[donor] = "train"
            assignment[eject] = "val"
            changed = True
        if not changed:
            break
    return assignment


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            clean = {k: v for k, v in row.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=True) + "\n")


def build(
    model_runs_dir: Path,
    output_dir: Path,
    seed: str,
    train_ratio: float,
    val_ratio: float,
    max_common_per_task: int | None,
    exclude_model_substrings: list[str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "seed": seed,
        "train_ratio": train_ratio,
        "val_ratio": val_ratio,
        "test_ratio": 1.0 - train_ratio - val_ratio,
        "tasks": {},
    }

    task_dirs = sorted([p for p in model_runs_dir.iterdir() if p.is_dir() and p.name not in EXCLUDED])
    for task_dir in task_dirs:
        task = task_dir.name
        model_rows: dict[str, dict[str, dict[str, Any]]] = {}
        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            if any(substr and substr in model_dir.name for substr in exclude_model_substrings):
                continue
            rows = _read_rows(model_dir, task)
            if rows:
                model_rows[model_dir.name] = rows

        if len(model_rows) < 2:
            continue

        common_ids = set.intersection(*[set(rows.keys()) for rows in model_rows.values()])
        ids_sorted = sorted(common_ids)
        if max_common_per_task is not None:
            ids_sorted = ids_sorted[:max_common_per_task]
        ids_set = set(ids_sorted)
        if not ids_sorted:
            continue

        assignment = _initial_split(seed=seed, ids=ids_sorted, train_ratio=train_ratio, val_ratio=val_ratio)
        assignment = _repair_train_collapse(assignment=assignment, ids_sorted=ids_sorted, model_rows=model_rows)

        split_ids = {"train": [], "val": [], "test": []}
        for cid in ids_sorted:
            split_ids[assignment[cid]].append(cid)

        task_out = output_dir / task
        task_out.mkdir(parents=True, exist_ok=True)
        (task_out / "split_query_ids.json").write_text(json.dumps(split_ids, indent=2), encoding="utf-8")

        task_meta: dict[str, Any] = {
            "common_query_count": len(ids_sorted),
            "split_sizes": {k: len(v) for k, v in split_ids.items()},
            "models": {},
        }

        for model_name, rows in sorted(model_rows.items()):
            out_model = task_out / model_name
            per_split = {"train": [], "val": [], "test": []}
            for cid, row in rows.items():
                if cid not in ids_set:
                    continue
                per_split[assignment[cid]].append(row)
            for split in ("train", "val", "test"):
                rows_sorted = sorted(per_split[split], key=lambda r: r["_canonical_id"])
                _write_jsonl(out_model / f"{split}.jsonl", rows_sorted)
            train_labels = [int(r["_fail"]) for r in per_split["train"]]
            task_meta["models"][model_name] = {
                "rows_after_intersection": sum(len(per_split[s]) for s in ("train", "val", "test")),
                "split_sizes": {s: len(per_split[s]) for s in ("train", "val", "test")},
                "train_label_counts": {
                    "fail_0": int(sum(1 for v in train_labels if v == 0)),
                    "fail_1": int(sum(1 for v in train_labels if v == 1)),
                },
            }

        summary["tasks"][task] = task_meta

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic SDDF training splits with shared query IDs from raw model run files.")
    parser.add_argument("--model-runs-dir", default="model_runs")
    parser.add_argument("--output-dir", default="model_runs/sddf_training_splits")
    parser.add_argument("--seed", default="sddf-train-v1")
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--max-common-per-task", type=int, default=250)
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    args = parser.parse_args()

    if args.train_ratio <= 0 or args.val_ratio <= 0 or (args.train_ratio + args.val_ratio) >= 1:
        raise ValueError("Ratios must satisfy: train_ratio > 0, val_ratio > 0, and train_ratio + val_ratio < 1")

    model_runs_dir = Path(args.model_runs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build(
        model_runs_dir=model_runs_dir,
        output_dir=output_dir,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        max_common_per_task=args.max_common_per_task,
        exclude_model_substrings=[s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()],
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote: {output_dir}")
    print(f"Tasks processed: {len(summary['tasks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
