#!/usr/bin/env python3
"""
Test: Adaptive Percentile-Based Validation Against Real Data

Compares old (fixed targets) vs new (adaptive percentiles) validation approaches
on actual SDDF validation splits for multiple tasks.
"""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.validation_dynamic import run_validation


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL file."""
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _label_fail(row: dict[str, Any]) -> int:
    """Determine if sample failed."""
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _prepare_validation_data(val_path: Path) -> tuple[list[dict], dict[str, float]]:
    """Prepare validation data from val.jsonl file."""
    rows = _read_jsonl(val_path)
    if not rows:
        raise ValueError(f"Missing val split rows at {val_path}")

    ids: list[str] = []
    samples: list[dict[str, Any]] = []
    raw_scores: list[float] = []

    for i, row in enumerate(rows):
        sid = str(row.get("sample_id") or row.get("query_id") or f"sample_{i}")
        ids.append(sid)

        # Use "bin" field if available, else "score"
        if "bin" in row:
            bval = float(row.get("bin", 5.0))
            sval = bval / 9.0
        else:
            sval = float(row.get("score", 0.5))

        raw_scores.append(sval)
        samples.append({
            "sample_id": sid,
            "slm_correct": bool(1 - _label_fail(row)),
            "llm_correct": bool(row.get("llm_correct", True)),
            "failure_category": row.get("failure_category"),
            "failure_type": row.get("failure_type"),
            "severity_score": row.get("severity_score"),
            "risk_weight": row.get("risk_weight"),
        })

    # Normalize scores to [0, 1]
    arr = np.array(raw_scores, dtype=float)
    lo = float(np.min(arr)) if arr.size else 0.0
    hi = float(np.max(arr)) if arr.size else 1.0
    if hi <= lo:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - lo) / (hi - lo)

    difficulty_scores = {ids[i]: float(norm[i]) for i in range(len(ids))}
    return samples, difficulty_scores


def test_task(task: str, model: str = "qwen2.5_3b") -> dict[str, Any]:
    """Test adaptive validation on a task."""
    splits_root = ROOT / "model_runs" / "sddf_training_splits_slm_only"
    val_path = splits_root / task / model / "val.jsonl"

    if not val_path.exists():
        return {"error": f"Missing {val_path}"}

    samples, scores = _prepare_validation_data(val_path)

    # Run OLD approach (fixed targets)
    result_old = run_validation(
        samples,
        scores,
        task=task,
        use_adaptive=False,
        cap_static=0.65,
        risk_static=0.30,
    )

    # Run NEW approach (adaptive percentiles)
    result_new = run_validation(
        samples,
        scores,
        task=task,
        use_adaptive=True,
        cap_percentile=50,
        risk_percentile=75,
    )

    return {
        "task": task,
        "model": model,
        "n_samples": len(samples),
        "baseline_capability": result_new["baseline_capability"],
        "baseline_risk": result_new["baseline_risk"],
        "old": {
            "mode": "fixed_targets",
            "cap_static": 0.65,
            "risk_static": 0.30,
            "cap_dynamic": result_old.get("cap_dynamic"),
            "risk_dynamic": result_old.get("risk_dynamic"),
            "selected_tau": result_old.get("selected_tau_score"),
            "feasible_zone_size": result_old.get("feasible_tau_count"),
            "selected_capability": result_old.get("selected_capability"),
            "selected_risk": result_old.get("selected_risk"),
            "tau_source": result_old.get("tau_source"),
        },
        "new": {
            "mode": "adaptive_percentiles",
            "cap_percentile": 50,
            "risk_percentile": 75,
            "cap_target": result_new.get("cap_target"),
            "risk_target": result_new.get("risk_target"),
            "selected_tau": result_new.get("selected_tau_score"),
            "feasible_zone_size": result_new.get("feasible_tau_count"),
            "selected_capability": result_new.get("selected_capability"),
            "selected_risk": result_new.get("selected_risk"),
            "tau_source": result_new.get("tau_source"),
        },
    }


def main() -> None:
    """Run comprehensive tests."""
    tasks = [
        "maths",
        "code_generation",
        "classification",
        "summarization",
        "information_extraction",
        "instruction_following",
        "retrieval_grounded",
        "text_generation",
    ]

    print("\n" + "=" * 100)
    print("ADAPTIVE VALIDATION: REAL DATA TEST")
    print("=" * 100)
    print("\nModel: qwen2.5_3b (seed 42)")
    print("Comparing: Fixed Targets (OLD) vs Adaptive Percentiles (NEW)\n")

    results = []
    for task in tasks:
        result = test_task(task)
        results.append(result)

        if "error" in result:
            print(f"[ERROR] {task:25s}: {result['error']}")
            continue

        print(f"[OK]    {task:25s}")
        print(f"    Baseline:     cap={result['baseline_capability']:.3f}, risk={result['baseline_risk']:.4f}")
        print(f"    OLD (fixed):  tau={result['old']['selected_tau']:6.3f} | cap={result['old']['selected_capability']:.3f} | risk={result['old']['selected_risk']:.4f} | zone={result['old']['feasible_zone_size']:2d} | {result['old']['tau_source']}")
        print(f"    NEW (adapt):  tau={result['new']['selected_tau']:6.3f} | cap={result['new']['selected_capability']:.3f} | risk={result['new']['selected_risk']:.4f} | zone={result['new']['feasible_zone_size']:2d} | {result['new']['tau_source']}")
        print(f"    Targets:      OLD: cap_dyn={result['old']['cap_dynamic']:.3f}, risk_dyn={result['old']['risk_dynamic']:.4f}")
        print(f"                  NEW: cap_target={result['new']['cap_target']:.3f}, risk_target={result['new']['risk_target']:.4f}")
        print()

    # Summary table
    print("\n" + "=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print()
    print(f"{'Task':<25} | {'Baseline Cap':<12} | {'OLD TAU':<10} | {'NEW TAU':<10} | {'OLD Zone':<10} | {'NEW Zone':<10}")
    print("-" * 95)
    for result in results:
        if "error" in result:
            continue
        print(
            f"{result['task']:<25} | "
            f"{result['baseline_capability']:>10.3f}  | "
            f"{result['old']['selected_tau']:>8.3f}  | "
            f"{result['new']['selected_tau']:>8.3f}  | "
            f"{result['old']['feasible_zone_size']:>8d}  | "
            f"{result['new']['feasible_zone_size']:>8d}"
        )

    # Key insights
    print("\n" + "=" * 100)
    print("KEY OBSERVATIONS")
    print("=" * 100)

    adaptations = 0
    for result in results:
        if "error" in result:
            continue
        old_tau = result['old']['selected_tau']
        new_tau = result['new']['selected_tau']
        if old_tau != new_tau:
            adaptations += 1
            print(f"[CHANGED] {result['task']:25s}: {old_tau:.3f} -> {new_tau:.3f}")

    print(f"\nTotal tasks with adaptive changes: {adaptations}/{len([r for r in results if 'error' not in r])}")

    # Detailed comparison
    print("\n" + "=" * 100)
    print("DETAILED COMPARISON: Why Targets Changed")
    print("=" * 100)

    for result in results:
        if "error" in result:
            continue

        old_cap_target = result['old']['cap_dynamic']
        old_risk_target = result['old']['risk_dynamic']
        new_cap_target = result['new']['cap_target']
        new_risk_target = result['new']['risk_target']

        if old_cap_target != new_cap_target or old_risk_target != new_risk_target:
            print(f"\n{result['task'].upper()}")
            print(f"  OLD approach (fixed 0.65/0.30, adjusted by baseline):")
            print(f"    cap_target: min(0.65, {result['baseline_capability']:.3f}-0.05) = {old_cap_target:.3f}")
            print(f"    risk_target: max(0.30, {result['baseline_risk']:.4f}+0.05) = {old_risk_target:.4f}")
            print(f"  NEW approach (percentile of curves):")
            print(f"    cap_target: 50th percentile = {new_cap_target:.3f}")
            print(f"    risk_target: 75th percentile = {new_risk_target:.4f}")
            print(f"  Result:")
            print(f"    OLD: zone size = {result['old']['feasible_zone_size']}")
            print(f"    NEW: zone size = {result['new']['feasible_zone_size']}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
