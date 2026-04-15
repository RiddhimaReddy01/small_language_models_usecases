#!/usr/bin/env python3
"""
Comprehensive Test: Adaptive Validation Across All Task Families & Models

Tests adaptive percentile-based validation on all combinations of:
- Tasks: 8 task families
- Models: 4 models (qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b, llama-3.3-70b)
Total: 32 combinations
"""

import json
import sys
from pathlib import Path
from typing import Any
from collections import defaultdict

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

    arr = np.array(raw_scores, dtype=float)
    lo = float(np.min(arr)) if arr.size else 0.0
    hi = float(np.max(arr)) if arr.size else 1.0
    if hi <= lo:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - lo) / (hi - lo)

    difficulty_scores = {ids[i]: float(norm[i]) for i in range(len(ids))}
    return samples, difficulty_scores


# Fixed baseline capability values (from COMMON_SAMPLES_REPORT and task estimates)
BASELINE_CAPABILITY_FIXED = {
    "maths": 0.726,
    "code_generation": 0.380,
    "classification": 0.90,
    "summarization": 0.95,
    "information_extraction": 0.92,
    "instruction_following": 0.90,
    "retrieval_grounded": 0.88,
    "text_generation": 0.93,
}


def test_combination(task: str, model: str) -> dict[str, Any]:
    """Test adaptive validation on task/model combination."""
    splits_root = ROOT / "model_runs" / "sddf_training_splits_slm_only"
    val_path = splits_root / task / model / "val.jsonl"

    if not val_path.exists():
        return {"error": f"Missing {val_path}"}

    try:
        samples, scores = _prepare_validation_data(val_path)
    except Exception as e:
        return {"error": str(e)}

    # Run NEW approach only (adaptive percentiles)
    try:
        result = run_validation(
            samples,
            scores,
            task=task,
            use_adaptive=True,
            cap_percentile=50,
            risk_percentile=75,
        )
    except Exception as e:
        return {"error": f"Validation failed: {str(e)}"}

    # Use fixed baseline capability (data doesn't have llm_correct field)
    baseline_cap = BASELINE_CAPABILITY_FIXED.get(task, 0.90)

    return {
        "task": task,
        "model": model,
        "n_samples": len(samples),
        "baseline_capability": baseline_cap,  # Use fixed value
        "baseline_capability_source": "common_samples_report" if task in ["maths", "code_generation"] else "task_estimate",
        "baseline_risk": result.get("baseline_risk"),
        "cap_target": result.get("cap_target"),
        "risk_target": result.get("risk_target"),
        "selected_tau": result.get("selected_tau_score"),
        "feasible_zone_size": result.get("feasible_tau_count"),
        "selected_capability": result.get("selected_capability"),
        "selected_risk": result.get("selected_risk"),
        "tau_source": result.get("tau_source"),
    }


def main() -> None:
    """Run comprehensive tests on all task/model combinations."""
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

    models = [
        "qwen2.5_0.5b",
        "qwen2.5_3b",
        "qwen2.5_7b",
        "llama-3.3-70b-versatile",
    ]

    print("\n" + "=" * 120)
    print("COMPREHENSIVE ADAPTIVE VALIDATION TEST: ALL TASK FAMILIES x ALL MODELS")
    print("=" * 120)
    print(f"\nTesting {len(tasks)} tasks × {len(models)} models = {len(tasks) * len(models)} combinations\n")

    all_results = []
    results_by_task = defaultdict(list)
    results_by_model = defaultdict(list)

    # Run all combinations
    total = len(tasks) * len(models)
    current = 0
    for task in tasks:
        for model in models:
            current += 1
            result = test_combination(task, model)

            if "error" not in result:
                all_results.append(result)
                results_by_task[task].append(result)
                results_by_model[model].append(result)
                status = "[OK]"
                zone_info = f"zone={result['feasible_zone_size']:2d}"
            else:
                status = "[ERR]"
                zone_info = result["error"][:40]

            print(f"[{current:2d}/{total}] {status} {task:25s} {model:25s} {zone_info}")

    # Summary by task
    print("\n" + "=" * 120)
    print("SUMMARY BY TASK")
    print("=" * 120)
    print()
    print(f"{'Task':<25} | {'Models':<6} | {'Base Cap':<9} | {'Avg Risk':<8} | {'Avg Zone':<8} | {'All Feasible?':<12}")
    print("-" * 100)

    for task in tasks:
        task_results = results_by_task[task]
        if not task_results:
            print(f"{task:<25} | {0:>5d}  | {'—':<9} | {'—':<8} | {'—':<8} | NO")
            continue

        avg_cap = np.mean([r.get("baseline_capability", 0) for r in task_results])
        avg_risk = np.mean([r.get("baseline_risk", 0) for r in task_results])
        avg_zone = np.mean([r.get("feasible_zone_size", 0) for r in task_results])
        all_feasible = all(r.get("feasible_zone_size", 0) > 0 for r in task_results)

        print(
            f"{task:<25} | {len(task_results):>5d}  | {avg_cap:>8.3f}  | {avg_risk:>7.4f}  | {avg_zone:>7.2f}  | {'YES' if all_feasible else 'NO':<12}"
        )

    # Summary by model
    print("\n" + "=" * 120)
    print("SUMMARY BY MODEL")
    print("=" * 120)
    print()
    print(f"{'Model':<27} | {'Tasks':<6} | {'Avg Cap':<8} | {'Avg Risk':<8} | {'Avg Zone':<8} | {'Feasible %':<10}")
    print("-" * 100)

    for model in models:
        model_results = results_by_model[model]
        if not model_results:
            print(f"{model:<27} | {0:>5d}  | {'—':<8} | {'—':<8} | {'—':<8} | {'—':<10}")
            continue

        avg_cap = np.mean([r.get("baseline_capability", 0) for r in model_results])
        avg_risk = np.mean([r.get("baseline_risk", 0) for r in model_results])
        avg_zone = np.mean([r.get("feasible_zone_size", 0) for r in model_results])
        feasible_pct = sum(1 for r in model_results if r.get("feasible_zone_size", 0) > 0) / len(model_results) * 100

        print(
            f"{model:<27} | {len(model_results):>5d}  | {avg_cap:>7.3f}  | {avg_risk:>7.4f}  | {avg_zone:>7.2f}  | {feasible_pct:>8.1f}%"
        )

    # Overall statistics
    print("\n" + "=" * 120)
    print("OVERALL STATISTICS")
    print("=" * 120)
    print()

    if all_results:
        total_feasible = sum(1 for r in all_results if r.get("feasible_zone_size", 0) > 0)
        total_strict = sum(1 for r in all_results if r.get("tau_source") == "strict_feasible_adaptive")
        total_fallback = sum(1 for r in all_results if r.get("tau_source") == "fallback_min_violation_adaptive")

        avg_cap = np.mean([r.get("baseline_capability", 0) for r in all_results])
        avg_risk = np.mean([r.get("baseline_risk", 0) for r in all_results])
        avg_zone = np.mean([r.get("feasible_zone_size", 0) for r in all_results])

        print(f"Total combinations tested:     {len(all_results)}/{total}")
        print(f"Feasible (zone > 0):           {total_feasible}/{len(all_results)} ({total_feasible/len(all_results)*100:.1f}%)")
        print(f"Strict feasible selection:     {total_strict}/{len(all_results)} ({total_strict/len(all_results)*100:.1f}%)")
        print(f"Fallback selection:            {total_fallback}/{len(all_results)} ({total_fallback/len(all_results)*100:.1f}%)")
        print()
        print(f"Average baseline capability:   {avg_cap:.3f}")
        print(f"Average baseline risk:         {avg_risk:.4f}")
        print(f"Average zone size:             {avg_zone:.2f}")
        print()

        # Model comparison
        print("Model Capability Ranking (avg baseline cap):")
        model_caps = [(model, np.mean([r.get("baseline_capability", 0) for r in results_by_model[model]]))
                      for model in models if model in results_by_model and results_by_model[model]]
        for rank, (model, cap) in enumerate(sorted(model_caps, key=lambda x: x[1], reverse=True), 1):
            print(f"  {rank}. {model:<27s} {cap:.3f}")

        print()
        print("Task Difficulty Ranking (avg baseline cap, lower = harder):")
        task_caps = [(task, np.mean([r.get("baseline_capability", 0) for r in results_by_task[task]]))
                     for task in tasks if task in results_by_task and results_by_task[task]]
        for rank, (task, cap) in enumerate(sorted(task_caps, key=lambda x: x[1]), 1):
            print(f"  {rank}. {task:<25s} {cap:.3f}")

    # Write detailed results to JSON
    output_file = ROOT / "adaptive_validation_comprehensive_results.json"
    with open(output_file, "w") as f:
        json.dump({"results": all_results, "metadata": {
            "total_combinations": len(all_results),
            "tasks": tasks,
            "models": models,
            "test_date": "2026-04-15",
            "validation_mode": "adaptive_percentile_p50_q75"
        }}, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")

    print("\n" + "=" * 120)


if __name__ == "__main__":
    main()
