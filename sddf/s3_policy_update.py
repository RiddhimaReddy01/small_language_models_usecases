from __future__ import annotations

from collections import defaultdict
from typing import Any


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, v)))


def recommend_task_tier_thresholds(
    current_thresholds: dict[str, Any],
    test_report: dict[str, Any],
    min_tau1: float = 2.0,
    max_tau2: float = 4.5,
) -> dict[str, Any]:
    """
    Recommend per-task tau1/tau2 updates from SDDF test evidence.

    Heuristic:
    - Higher failure/uncertainty -> lower tau1/tau2 (more hybrid/llm_only)
    - Strong performance -> allow slightly higher tau1/tau2 (more pure_slm)
    """
    base = dict(current_thresholds or {})
    default = dict(base.get("*", {"tau1": 3.2, "tau2": 4.0}))
    by_task_fail: dict[str, list[float]] = defaultdict(list)
    by_task_f1: dict[str, list[float]] = defaultdict(list)
    by_task_ece: dict[str, list[float]] = defaultdict(list)

    for run in test_report.get("runs", []):
        task = str(run.get("task", "")).strip()
        if not task:
            continue
        m = run.get("test_metrics", {}) or {}
        by_task_fail[task].append(float(m.get("positive_rate", 0.0)))
        by_task_f1[task].append(float(m.get("f1", 0.0)))
        by_task_ece[task].append(float(m.get("ece_10bin", 0.0)))

    out: dict[str, Any] = {"*": {"tau1": float(default.get("tau1", 3.2)), "tau2": float(default.get("tau2", 4.0))}}
    for task in sorted(by_task_fail.keys()):
        fail = _mean(by_task_fail[task])
        f1 = _mean(by_task_f1[task])
        ece = _mean(by_task_ece[task])

        # Conservative pressure term from observed runtime evidence.
        pressure = 0.0
        pressure += max(0.0, fail - 0.35) * 2.2
        pressure += max(0.0, 0.70 - f1) * 1.4
        pressure += max(0.0, ece - 0.20) * 1.0

        # Relief term for very strong performance.
        relief = 0.0
        relief += max(0.0, f1 - 0.85) * 0.8
        relief += max(0.0, 0.20 - fail) * 0.6

        delta = pressure - relief
        tau1_base = float(base.get(task, {}).get("tau1", default["tau1"]))
        tau2_base = float(base.get(task, {}).get("tau2", default["tau2"]))
        tau1_new = _clamp(tau1_base - delta, min_tau1, max_tau2 - 0.5)
        tau2_new = _clamp(tau2_base - delta, tau1_new + 0.4, max_tau2)
        out[task] = {
            "tau1": round(tau1_new, 3),
            "tau2": round(tau2_new, 3),
            "evidence": {
                "avg_failure_rate": round(fail, 4),
                "avg_f1": round(f1, 4),
                "avg_ece": round(ece, 4),
                "delta_applied": round(delta, 4),
            },
        }
    return out


def recommend_s3_score_overrides(
    bridge_output: dict[str, Any],
    val_report: dict[str, Any],
) -> dict[str, Any]:
    """
    Recommend dimension overrides per task based on calibration pressure.
    """
    by_task_tau_pressure: dict[str, list[float]] = defaultdict(list)
    for run in val_report.get("runs", []):
        task = str(run.get("task", "")).strip()
        if not task:
            continue
        tau_cap = run.get("tau_cap", None)
        tau_risk = run.get("tau_risk", None)
        tcap = float(tau_cap) if tau_cap is not None else 9.0
        trisk = float(tau_risk) if tau_risk is not None else 9.0
        by_task_tau_pressure[task].append(min(tcap, trisk))

    by_task_s3: dict[str, float] = {}
    for r in bridge_output.get("results", []):
        t = str(r.get("task", ""))
        s3 = float((r.get("decision", {}) or {}).get("s3_score", 0.0))
        by_task_s3[t] = s3

    rec: dict[str, Any] = {}
    for task, s3 in sorted(by_task_s3.items()):
        tau_route_avg = _mean(by_task_tau_pressure.get(task, []))
        # Lower tau_route implies stronger runtime caution; reflect in S3 SK/TC bump suggestion.
        if tau_route_avg <= 0.2:
            rec[task] = {"SK": 4, "TC": 4}
        elif tau_route_avg <= 0.5:
            rec[task] = {"SK": 3, "TC": 3}
        elif s3 < 2.2:
            rec[task] = {"SK": 2, "TC": 2}
    return rec

