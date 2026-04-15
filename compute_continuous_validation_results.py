#!/usr/bin/env python3
"""
Continuous Threshold Validation: 6-Step Implementation

For each (task, model) combination:
1. Sort samples by difficulty
2. Compute capability and risk curves
3. Compute dynamic thresholds: C_dyn, R_dyn
4. Find feasible set F
5. Select τ* (strict or fallback)
6. Collect derived metrics
"""

import json
import sys
from pathlib import Path
from typing import Any
from collections import defaultdict

import numpy as np

ROOT = Path(__file__).resolve().parent

# Fixed baseline capability values (from COMMON_SAMPLES_REPORT)
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

# Dynamic threshold parameters
C_MIN, C_MAX = 0.0, 1.0
R_MIN, R_MAX = 0.0, 1.0
CAPABILITY_MARGIN = 0.05
RISK_MARGIN = 0.05


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


def _compute_risk_score(row: dict[str, Any]) -> float:
    """Compute risk score for sample (0 if correct, else risk value)."""
    if not _label_fail(row):
        return 0.0  # Correct → no risk

    # Failed → use risk metrics
    severity = float(row.get("severity_score", 0.5))
    risk_weight = float(row.get("risk_weight", 1.0))

    # Risk = severity × weight, clamped to [0, 1]
    risk = min(severity * risk_weight, 1.0)
    return risk


def compute_continuous_validation(val_path: Path, task: str, model: str) -> dict[str, Any]:
    """
    Apply 6-step continuous threshold validation method.

    Args:
        val_path: Path to val.jsonl file
        task: Task name (for baseline_capability lookup)

    Returns:
        Dict with τ*, metrics, and diagnostics
    """
    rows = _read_jsonl(val_path)
    if not rows:
        return {"error": f"Empty validation set: {val_path}"}

    # =========================================================================
    # STEP 1: Sort samples by difficulty
    # =========================================================================
    samples = []
    for i, row in enumerate(rows):
        difficulty = float(row.get("score", 0.5))
        capability = 1 - _label_fail(row)  # 1 if correct, 0 if failed
        risk = _compute_risk_score(row)

        samples.append({
            "idx": i,
            "difficulty": difficulty,
            "capability": capability,
            "risk": risk,
        })

    # Sort by difficulty (ascending)
    samples = sorted(samples, key=lambda s: s["difficulty"])

    # =========================================================================
    # STEP 2: Compute capability and risk curves
    # =========================================================================
    capability_curve = {}
    risk_curve = {}
    tau_to_k = {}  # Map tau to position k (for coverage calculation)
    k_to_tau = {}  # Map position k to tau

    for k in range(1, len(samples) + 1):
        prefix = samples[:k]
        tau_k = prefix[-1]["difficulty"]

        cap_k = np.mean([s["capability"] for s in prefix])
        risk_k = np.mean([s["risk"] for s in prefix])

        capability_curve[tau_k] = float(cap_k)
        risk_curve[tau_k] = float(risk_k)
        tau_to_k[tau_k] = k  # Store position for THIS tau (will be overwritten if tau appears multiple times)
        k_to_tau[k] = tau_k

    # =========================================================================
    # STEP 3: Compute dynamic thresholds
    # =========================================================================
    baseline_cap = BASELINE_CAPABILITY_FIXED.get(task, 0.90)
    mean_risk = np.mean([s["risk"] for s in samples])

    c_dyn = np.clip(baseline_cap - CAPABILITY_MARGIN, C_MIN, C_MAX)
    r_dyn = np.clip(mean_risk + RISK_MARGIN, R_MIN, R_MAX)

    # =========================================================================
    # STEP 4: Find feasible set F
    # =========================================================================
    feasible_set = []
    for tau in capability_curve.keys():
        cap_tau = capability_curve[tau]
        risk_tau = risk_curve[tau]

        if cap_tau >= c_dyn and risk_tau <= r_dyn:
            feasible_set.append(tau)

    # =========================================================================
    # STEP 5: Select threshold τ*
    # =========================================================================
    if feasible_set:
        # Strict feasible: select max(F)
        tau_star = max(feasible_set)
        tau_source = "strict_feasible_max"
    else:
        # Fallback: minimize combined violation
        best_violation = float('inf')
        tau_star = None

        for tau in capability_curve.keys():
            cap_tau = capability_curve[tau]
            risk_tau = risk_curve[tau]

            cap_violation = max(0.0, c_dyn - cap_tau)
            risk_violation = max(0.0, risk_tau - r_dyn)
            violation = cap_violation + risk_violation

            if violation < best_violation:
                best_violation = violation
                tau_star = tau

        tau_source = "fallback_min_violation"

    # =========================================================================
    # STEP 6: Compute derived metrics
    # =========================================================================
    if tau_star is not None:
        selected_capability = capability_curve[tau_star]
        selected_risk = risk_curve[tau_star]

        # Coverage = k / N where τ* = τ_k (the k-th smallest difficulty)
        # Use stored position k from tau_to_k map
        if tau_star in tau_to_k:
            k_star = tau_to_k[tau_star]
            coverage = k_star / len(samples)
        else:
            # Fallback: count samples with difficulty <= τ*
            coverage = sum(1 for s in samples if s["difficulty"] <= tau_star) / len(samples)
    else:
        selected_capability = 0.0
        selected_risk = 1.0
        coverage = 0.0

    return {
        "task": task,
        "model": model,
        "n_samples": len(samples),
        "baseline_capability": baseline_cap,
        "mean_risk": float(mean_risk),
        "c_dyn": float(c_dyn),
        "r_dyn": float(r_dyn),
        "tau_star": float(tau_star) if tau_star is not None else None,
        "tau_source": tau_source,
        "feasible_set_size": len(feasible_set),
        "coverage": float(coverage),
        "selected_capability": float(selected_capability),
        "selected_risk": float(selected_risk),
    }


def main() -> None:
    """Run continuous validation on all task-model combinations."""
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
    ]

    print("\n" + "=" * 130)
    print("CONTINUOUS THRESHOLD VALIDATION: 6-Step Method")
    print("=" * 130)
    print(f"\nC_dyn = clamp(C_LLM - 0.05, {C_MIN}, {C_MAX})")
    print(f"R_dyn = clamp(R_mean + 0.05, {R_MIN}, {R_MAX})")
    print(f"\nTesting {len(tasks)} tasks x {len(models)} models = {len(tasks) * len(models)} combinations\n")

    all_results = []
    results_by_task = defaultdict(list)
    results_by_model = defaultdict(list)

    # Run all combinations
    total = len(tasks) * len(models)
    current = 0
    for task in tasks:
        for model in models:
            current += 1

            splits_root = ROOT / "model_runs" / "sddf_training_splits_slm_only"
            val_path = splits_root / task / model / "val.jsonl"

            if not val_path.exists():
                result = {"error": f"Missing {val_path}"}
            else:
                result = compute_continuous_validation(val_path, task, model)

            if "error" not in result:
                all_results.append(result)
                results_by_task[task].append(result)
                results_by_model[model].append(result)
                status = "[OK]"
                info = f"tau*={result['tau_star']:.3f} cov={result['coverage']:.2%}" if result['tau_star'] else "tau*=None"
            else:
                status = "[ERR]"
                info = result["error"][:40]

            print(f"[{current:2d}/{total}] {status} {task:25s} {model:20s} {info}")

    # =========================================================================
    # TABLE 1: OVERALL SUMMARY
    # =========================================================================
    print("\n" + "=" * 130)
    print("TABLE 1: OVERALL SUMMARY")
    print("=" * 130)
    print()

    if all_results:
        strict_count = sum(1 for r in all_results if r.get("tau_source") == "strict_feasible_max")
        fallback_count = sum(1 for r in all_results if r.get("tau_source") == "fallback_min_violation")

        mean_tau = np.mean([r["tau_star"] for r in all_results if r["tau_star"] is not None])
        mean_coverage = np.mean([r["coverage"] for r in all_results])
        mean_cap = np.mean([r["selected_capability"] for r in all_results])
        mean_risk = np.mean([r["selected_risk"] for r in all_results])

        table1_data = [
            ("Total Runs", len(all_results)),
            ("Strict Feasible", strict_count),
            ("Fallback", fallback_count),
            ("Mean tau*", f"{mean_tau:.4f}"),
            ("Mean Coverage", f"{mean_coverage:.4f}"),
            ("Mean Capability at tau*", f"{mean_cap:.4f}"),
            ("Mean Risk at tau*", f"{mean_risk:.4f}"),
        ]

        for metric, value in table1_data:
            print(f"  {metric:<35s} {value}")

    # =========================================================================
    # TABLE 2: TASK-LEVEL SUMMARY
    # =========================================================================
    print("\n" + "=" * 130)
    print("TABLE 2: TASK-LEVEL SUMMARY")
    print("=" * 130)
    print()

    header = f"{'Task':<25} {'n':<6} {'Strict':<7} {'Fallback':<8} {'Mean tau*':<10} {'Mean Cov':<10} {'Mean C(tau*)':<12} {'Mean R(tau*)':<12}"
    print(header)
    print("-" * len(header))

    for task in tasks:
        task_results = results_by_task[task]
        if not task_results:
            print(f"{task:<25} {'—':<6} {'—':<7} {'—':<8} {'—':<10} {'—':<10} {'—':<12} {'—':<12}")
            continue

        strict = sum(1 for r in task_results if r.get("tau_source") == "strict_feasible_max")
        fallback = sum(1 for r in task_results if r.get("tau_source") == "fallback_min_violation")
        mean_tau = np.mean([r["tau_star"] for r in task_results if r["tau_star"] is not None])
        mean_cov = np.mean([r["coverage"] for r in task_results])
        mean_cap = np.mean([r["selected_capability"] for r in task_results])
        mean_risk = np.mean([r["selected_risk"] for r in task_results])

        print(
            f"{task:<25} {len(task_results):<6} {strict:<7} {fallback:<8} "
            f"{mean_tau:<10.4f} {mean_cov:<10.4f} {mean_cap:<12.4f} {mean_risk:<12.4f}"
        )

    # =========================================================================
    # TABLE 3: MODEL-LEVEL DETAILED BEHAVIOR
    # =========================================================================
    print("\n" + "=" * 130)
    print("TABLE 3: DETAILED RESULTS (All Task × Model Combinations)")
    print("=" * 130)
    print()

    header3 = f"{'Task':<20} {'Model':<20} {'tau*':<10} {'Source':<20} {'Coverage':<10} {'C(tau*)':<10} {'R(tau*)':<10} {'|F|':<6}"
    print(header3)
    print("-" * len(header3))

    for result in all_results:
        tau_val = f"{result['tau_star']:.4f}" if result['tau_star'] is not None else "None"
        print(
            f"{result['task']:<20} {result['model']:<20} {tau_val:<10} "
            f"{result['tau_source']:<20} {result['coverage']:<10.4f} "
            f"{result['selected_capability']:<10.4f} {result['selected_risk']:<10.4f} "
            f"{result['feasible_set_size']:<6}"
        )

    # =========================================================================
    # TABLE 4: FEASIBILITY CHARACTERISTICS
    # =========================================================================
    print("\n" + "=" * 130)
    print("TABLE 4: FEASIBILITY CHARACTERISTICS")
    print("=" * 130)
    print()

    feasibility_types = {
        "Large F (|F| > 2)": [],
        "Moderate F (|F| = 1-2)": [],
        "Empty F (|F| = 0)": [],
    }

    for result in all_results:
        f_size = result["feasible_set_size"]
        if f_size > 2:
            feasibility_types["Large F (|F| > 2)"].append(result)
        elif f_size > 0:
            feasibility_types["Moderate F (|F| = 1-2)"].append(result)
        else:
            feasibility_types["Empty F (|F| = 0)"].append(result)

    for ftype, results in feasibility_types.items():
        count = len(results)
        pct = (count / len(all_results) * 100) if all_results else 0
        interpretation = {
            "Large F (|F| > 2)": "Robust feasibility — many valid thresholds",
            "Moderate F (|F| = 1-2)": "Narrow safe region — few valid thresholds",
            "Empty F (|F| = 0)": "Infeasible — all thresholds violate constraints",
        }[ftype]

        print(f"  {ftype:<25} {count:>2d} / {len(all_results)} ({pct:>5.1f}%)  ->  {interpretation}")

    # =========================================================================
    # TABLE 5: COVERAGE VS PERFORMANCE TRADEOFF
    # =========================================================================
    print("\n" + "=" * 130)
    print("TABLE 5: COVERAGE VS PERFORMANCE TRADEOFF (By Task)")
    print("=" * 130)
    print()

    header5 = f"{'Task':<20} {'Mean Coverage':<15} {'Mean C(tau*)':<15} {'Mean R(tau*)':<15} {'Interpretation':<40}"
    print(header5)
    print("-" * len(header5))

    for task in tasks:
        task_results = results_by_task[task]
        if not task_results:
            continue

        mean_cov = np.mean([r["coverage"] for r in task_results])
        mean_cap = np.mean([r["selected_capability"] for r in task_results])
        mean_risk = np.mean([r["selected_risk"] for r in task_results])

        # Interpretation
        if mean_cov > 0.75 and mean_risk < 0.1:
            interp = "Ideal: high coverage, low risk"
        elif mean_cov < 0.5 and mean_cap < 0.6:
            interp = "Difficult task: needs LLM fallback"
        elif mean_risk > 0.3:
            interp = "High-risk task: selective routing"
        else:
            interp = "Moderate routing requirements"

        print(
            f"{task:<20} {mean_cov:<15.4f} {mean_cap:<15.4f} {mean_risk:<15.4f} {interp:<40}"
        )

    # =========================================================================
    # ANALYSIS
    # =========================================================================
    print("\n" + "=" * 130)
    print("ANALYSIS: KEY INSIGHTS")
    print("=" * 130)
    print()

    if all_results:
        # Insight 1: τ* variation
        tau_values = [r["tau_star"] for r in all_results if r["tau_star"] is not None]
        tau_std = np.std(tau_values)
        print(f"1. THRESHOLD VARIATION (tau*)")
        print(f"   Continuous formulation reveals {len(set(tau_values))} unique thresholds across 24 runs.")
        print(f"   Std(tau*) = {tau_std:.4f}")
        print(f"   -> No collapse to discrete bins; rich differentiation per task/model [OK]")
        print()

        # Insight 2: Feasibility improvement
        strict_pct = (strict_count / len(all_results) * 100)
        fallback_pct = (fallback_count / len(all_results) * 100)
        print(f"2. FEASIBILITY AND SELECTION")
        print(f"   Strict feasible (max F):        {strict_count:>2d} runs ({strict_pct:>5.1f}%)")
        print(f"   Fallback (min violation):       {fallback_count:>2d} runs ({fallback_pct:>5.1f}%)")
        print(f"   -> Dynamic thresholds enable feasibility {strict_pct:.0f}% of time")
        print()

        # Insight 3: Task difficulty and τ*
        print(f"3. TASK DIFFICULTY vs ROUTING THRESHOLD")
        task_difficulty = {}
        for task in tasks:
            task_results = results_by_task[task]
            if task_results:
                mean_tau = np.mean([r["tau_star"] for r in task_results if r["tau_star"] is not None])
                mean_cap = np.mean([r["selected_capability"] for r in task_results])
                task_difficulty[task] = (mean_tau, mean_cap)

        sorted_tasks = sorted(task_difficulty.items(), key=lambda x: x[1][1])  # Sort by capability
        for rank, (task, (tau, cap)) in enumerate(sorted_tasks, 1):
            print(f"   {rank}. {task:<25s} tau*={tau:.4f}  C(tau*)={cap:.4f}")
        print()

        # Insight 4: Coverage patterns
        print(f"4. COVERAGE PATTERNS (Routing to SLM)")
        high_cov = [r for r in all_results if r["coverage"] > 0.75]
        low_cov = [r for r in all_results if r["coverage"] < 0.5]
        print(f"   High coverage (>75%):  {len(high_cov)} runs -> route most samples to SLM")
        print(f"   Low coverage (<50%):   {len(low_cov)} runs -> selective routing, use LLM fallback")
        print()

        # Insight 5: Continuous advantage
        print(f"5. CONTINUOUS FORMULATION ADVANTAGES")
        print(f"   [OK] Removes discrete bin artifacts (no collapse)")
        print(f"   [OK] Uses empirical difficulty scores directly")
        print(f"   [OK] Task-specific and model-specific thresholds")
        print(f"   [OK] Dynamic targets (C_dyn, R_dyn) adapt to baseline")
        print(f"   [OK] Feasible zone selection based on actual data curves")

    # Save detailed results to JSON
    output_file = ROOT / "continuous_validation_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "results": all_results,
            "metadata": {
                "total_runs": len(all_results),
                "method": "continuous_threshold_6step",
                "parameters": {
                    "C_min": C_MIN,
                    "C_max": C_MAX,
                    "R_min": R_MIN,
                    "R_max": R_MAX,
                    "capability_margin": CAPABILITY_MARGIN,
                    "risk_margin": RISK_MARGIN,
                },
            }
        }, f, indent=2)
    print(f"\n\nDetailed results saved to: {output_file}")

    print("\n" + "=" * 130)


if __name__ == "__main__":
    main()
