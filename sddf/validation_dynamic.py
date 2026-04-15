from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression


def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(x, b))


def _slm_correct(sample: dict[str, Any]) -> bool:
    if "slm_correct" in sample:
        return bool(sample.get("slm_correct"))
    if "correct" in sample:
        return bool(sample.get("correct"))
    status = str(sample.get("status", "")).lower()
    valid = bool(sample.get("valid", False))
    failure_category = sample.get("failure_category")
    error = sample.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return not fail


def _severity_multiplier(sample: dict[str, Any]) -> float:
    for key in ("severity_score", "risk_weight", "severity"):
        if key not in sample:
            continue
        try:
            raw = float(sample[key])
        except Exception:
            continue
        if raw > 1.0:
            raw = raw / 5.0
        return clamp(raw, 0.0, 1.0)
    return 1.0


def _failure_category_multiplier(sample: dict[str, Any]) -> float:
    category = str(sample.get("failure_category") or sample.get("failure_type") or "").strip().lower()
    cat_mul = {
        "logic_error": 1.00,
        "arithmetic_error": 1.10,
        "runtime_error": 1.15,
        "constraint_violation": 0.95,
        "wrong_label": 0.90,
        "answer_mismatch": 0.90,
        "missing_field": 0.85,
        "low_relevance": 0.80,
        "incomplete_output": 0.75,
    }
    return float(cat_mul.get(category, 1.0))


def compute_per_sample_metrics(
    samples: list[dict],
    scores: dict[str, float],
    task: str,
) -> tuple[list[dict], float, float]:
    """
    Returns:
      - per-sample dicts with capability/risk
      - baseline_cap (LLM reference accuracy)
      - baseline_risk (mean SLM failure-severity risk)
    """
    risk_per_task = {
        "classification": 0.56,
        "maths": 0.855,
        "code_generation": 0.9025,
        "instruction_following": 0.525,
        "information_extraction": 0.60,
        "retrieval_grounded": 0.68,
        "summarization": 0.2475,
        "text_generation": 0.18,
    }

    task_risk_base = risk_per_task.get(task, 0.50)
    metrics: list[dict[str, Any]] = []

    for sample in samples:
        sample_id = str(sample.get("sample_id", ""))
        score = float(scores.get(sample_id, 0.5))
        slm_correct = _slm_correct(sample)
        llm_correct = bool(sample.get("llm_correct", False))

        capability = 1.0 if slm_correct else 0.0
        if slm_correct:
            risk = 0.0
        else:
            severity_mul = _severity_multiplier(sample)
            category_mul = _failure_category_multiplier(sample)
            risk = clamp(task_risk_base * severity_mul * category_mul, 0.0, 1.0)

        metrics.append(
            {
                "sample_id": sample_id,
                "score": score,
                "slm_correct": slm_correct,
                "llm_correct": llm_correct,
                "capability": capability,
                "risk": risk,
            }
        )

    baseline_cap = sum(m["llm_correct"] for m in metrics) / len(metrics) if metrics else 0.0
    baseline_risk = sum(m["risk"] for m in metrics) / len(metrics) if metrics else 0.0
    return metrics, baseline_cap, baseline_risk


def build_difficulty_curves(
    metrics: list[dict],
    n_bins: int = 10,
) -> tuple[dict[int, float], dict[int, float], dict[int, int]]:
    if not metrics:
        return {}, {}, {}

    sorted_metrics = sorted(metrics, key=lambda m: m["score"])
    n = len(sorted_metrics)
    bin_size = max(1, n // n_bins)

    cap_by_bin: dict[int, float] = {}
    risk_by_bin: dict[int, float] = {}
    coverage_by_bin: dict[int, int] = {}

    for b in range(n_bins):
        start_idx = b * bin_size
        end_idx = (b + 1) * bin_size if b < n_bins - 1 else n
        if start_idx >= n:
            break

        bin_samples = sorted_metrics[start_idx:end_idx]
        cap = sum(m["capability"] for m in bin_samples) / len(bin_samples) if bin_samples else 0.0
        risk = sum(m["risk"] for m in bin_samples) / len(bin_samples) if bin_samples else 0.0

        cap_by_bin[b] = cap
        risk_by_bin[b] = risk
        coverage_by_bin[b] = len(bin_samples)

    difficulties = sorted(cap_by_bin.keys())
    if not difficulties:
        return {}, {}, {}

    cap_values = [cap_by_bin[d] for d in difficulties]
    risk_values = [risk_by_bin[d] for d in difficulties]

    try:
        iso_cap = IsotonicRegression(increasing=True, out_of_bounds="clip")
        iso_cap.fit(difficulties, cap_values)
        cap_curve = {d: float(iso_cap.predict([d])[0]) for d in difficulties}
    except Exception:
        cap_curve = cap_by_bin

    try:
        iso_risk = IsotonicRegression(increasing=False, out_of_bounds="clip")
        iso_risk.fit(difficulties, risk_values)
        risk_curve = {d: float(iso_risk.predict([d])[0]) for d in difficulties}
    except Exception:
        risk_curve = risk_by_bin

    return cap_curve, risk_curve, coverage_by_bin


def find_operational_zone(
    cap_curve: dict[int, float],
    risk_curve: dict[int, float],
    coverage: dict[int, int],
    cap_static: float,
    risk_static: float,
    baseline_cap: float,
    baseline_risk: float,
    mcap: float = 0.05,
    mrisk: float = 0.05,
    cap_min: float = 0.40,
    cap_max: float = 1.00,
    risk_min: float = 0.00,
    risk_max: float = 1.00,
    coverage_max: float = 0.70,
) -> dict[str, Any]:
    cap_dyn = clamp(min(cap_static, baseline_cap - mcap), cap_min, cap_max)
    risk_dyn = clamp(max(risk_static, baseline_risk + mrisk), risk_min, risk_max)

    feasible: list[int] = []
    violations: dict[int, float] = {}

    total_cov = float(sum(coverage.values())) if coverage else 0.0
    for d in sorted(cap_curve.keys()):
        cap_d = cap_curve.get(d, 0.0)
        risk_d = risk_curve.get(d, 1.0)
        cov = (coverage.get(d, 0) / total_cov) if total_cov > 0 else 0.0

        cap_ok = cap_d >= cap_dyn
        risk_ok = risk_d <= risk_dyn
        cov_ok = cov <= coverage_max
        if cap_ok and risk_ok and cov_ok:
            feasible.append(d)

        cap_violation = max(0.0, cap_dyn - cap_d)
        risk_violation = max(0.0, risk_d - risk_dyn)
        violations[d] = cap_violation + risk_violation

    strict_tau = max(feasible) if feasible else None
    if not feasible:
        def fallback_key(d: int) -> tuple[float, float, float, float]:
            return (violations[d], risk_curve.get(d, 1.0), -coverage.get(d, 0), -d)

        fallback_tau = min(violations.keys(), key=fallback_key) if violations else None
    else:
        fallback_tau = strict_tau

    selected_tau = strict_tau if strict_tau is not None else fallback_tau
    tau_source = "strict_feasible_max" if strict_tau is not None else "fallback_min_violation"

    return {
        "cap_dyn": cap_dyn,
        "risk_dyn": risk_dyn,
        "feasible_set": feasible,
        "strict_tau": strict_tau,
        "fallback_tau": fallback_tau,
        "selected_tau": selected_tau,
        "tau_source": tau_source,
        "violations": violations,
        "cap_curve": cap_curve,
        "risk_curve": risk_curve,
    }


def run_validation(
    val_samples: list[dict],
    scores: dict[str, float],
    task: str,
    cap_static: float = 0.65,
    risk_static: float = 0.30,
) -> dict[str, Any]:
    metrics, baseline_cap, baseline_risk = compute_per_sample_metrics(val_samples, scores, task)
    cap_curve, risk_curve, coverage = build_difficulty_curves(metrics)

    zone = find_operational_zone(
        cap_curve,
        risk_curve,
        coverage,
        cap_static,
        risk_static,
        baseline_cap,
        baseline_risk,
    )

    return {
        "task": task,
        "n_val_samples": len(val_samples),
        "n_metrics": len(metrics),
        "baseline_capability": baseline_cap,
        "baseline_risk": baseline_risk,
        "cap_static": cap_static,
        "risk_static": risk_static,
        "cap_dynamic": zone["cap_dyn"],
        "risk_dynamic": zone["risk_dyn"],
        "feasible_set": zone["feasible_set"],
        "strict_tau": zone["strict_tau"],
        "fallback_tau": zone["fallback_tau"],
        "selected_tau": zone["selected_tau"],
        "tau_source": zone["tau_source"],
        "violations": zone["violations"],
        "cap_curve": zone["cap_curve"],
        "risk_curve": zone["risk_curve"],
        "metrics": metrics,
    }
