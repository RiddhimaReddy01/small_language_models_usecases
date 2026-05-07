from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal


Dimension = Literal["TC", "OS", "SK", "DS", "LT", "VL"]
Tier = Literal["pure_slm", "hybrid", "llm_only", "disqualified"]

REQUIRED_DIMS: tuple[Dimension, ...] = ("TC", "OS", "SK", "DS", "LT", "VL")


@dataclass(frozen=True)
class GateResult:
    """Result of hard gating check from S3 prescreen."""
    disqualified: bool
    min_tier: Tier | None
    reason: str


def _validate_1_to_5(name: str, value: int) -> None:
    """Validate that value is an integer in [1, 5]."""
    if not isinstance(value, int) or value < 1 or value > 5:
        raise ValueError(f"{name} must be an integer in [1,5], got: {value!r}")


def _validate_dimensions(mapping: dict[Dimension, int], label: str) -> None:
    """Validate that all required dimensions are present and valid."""
    missing = [d for d in REQUIRED_DIMS if d not in mapping]
    if missing:
        raise ValueError(f"{label} missing dimensions: {missing}")
    for d in REQUIRED_DIMS:
        _validate_1_to_5(f"{label}[{d}]", int(mapping[d]))


def prescreen_gate(scores: dict[Dimension, int]) -> GateResult:
    """
    Hard gate from S3 section 3.5/3.6.

    Applies hard rules to disqualify tasks from pure SLM routing.
    """
    _validate_dimensions(scores, "scores")
    tc = int(scores["TC"])
    sk = int(scores["SK"])

    if sk == 5:
        return GateResult(disqualified=True, min_tier="disqualified", reason="Hard Rule 1: SK=5")
    if tc == 5 and sk >= 4:
        return GateResult(disqualified=True, min_tier="disqualified", reason="Hard Rule 2: TC=5 and SK>=4")
    if sk >= 4:
        return GateResult(disqualified=False, min_tier="hybrid", reason="Flag Rule: SK>=4")
    return GateResult(disqualified=False, min_tier=None, reason="Gate pass")


def compute_s3_score(scores: dict[Dimension, int], weights: dict[Dimension, int]) -> float:
    """
    Compute S3 score: S3 = [sum_i(scores_i * w_i) / sum_i(5 * w_i)] * 5
    """
    _validate_dimensions(scores, "scores")
    _validate_dimensions(weights, "weights")
    if int(weights["SK"]) < int(weights["TC"]):
        raise ValueError("Invalid weight profile: must satisfy w_SK >= w_TC")

    num = 0.0
    den = 0.0
    for d in REQUIRED_DIMS:
        s = float(scores[d])
        w = float(weights[d])
        num += s * w
        den += 5.0 * w
    if den <= 0.0:
        raise ValueError("Invalid denominator in S3 score")
    return (num / den) * 5.0


def tier_from_s3(s3_score: float, gate: GateResult, tau1: float = 3.2, tau2: float = 4.0) -> Tier:
    """
    Determine tier from S3 score and gating result.

    Thresholds tau1 and tau2 divide the S3 score range into tiers.
    """
    if gate.disqualified:
        return "disqualified"

    if s3_score <= tau1:
        tier: Tier = "pure_slm"
    elif s3_score <= tau2:
        tier = "hybrid"
    else:
        tier = "llm_only"

    if gate.min_tier == "hybrid" and tier == "pure_slm":
        return "hybrid"
    return tier


def route_limit_from_sddf(tau_risk: float, tau_cap: float) -> float:
    """Bridge formula from S3 -> SDDF runtime limit."""
    return min(float(tau_risk), float(tau_cap))


def decide_s3_and_route(
    scores: dict[Dimension, int],
    weights: dict[Dimension, int],
    tau_risk: float,
    tau_cap: float,
    tau1: float = 3.2,
    tau2: float = 4.0,
) -> dict[str, float | str | bool]:
    """
    Full S3 decision pipeline: gate, score, tier, and route.

    Returns a decision dict with S3 score, tier assignments, and routing limit.
    """
    gate = prescreen_gate(scores)
    if gate.disqualified:
        return {
            "disqualified": True,
            "gate_reason": gate.reason,
            "gate_min_tier": "disqualified",
            "formula_tier": "disqualified",
            "final_tier": "disqualified",
            "tier": "disqualified",
            "s3_score": 5.0,
            "tau_route": -1.0,
        }

    s3 = compute_s3_score(scores, weights)
    formula_tier = tier_from_s3(s3, GateResult(disqualified=False, min_tier=None, reason=gate.reason), tau1=tau1, tau2=tau2)
    final_tier = tier_from_s3(s3, gate, tau1=tau1, tau2=tau2)
    tau_route = route_limit_from_sddf(tau_risk=tau_risk, tau_cap=tau_cap)
    return {
        "disqualified": False,
        "gate_reason": gate.reason,
        "gate_min_tier": str(gate.min_tier) if gate.min_tier is not None else "none",
        "formula_tier": formula_tier,
        "final_tier": final_tier,
        "tier": final_tier,
        "s3_score": s3,
        "tau_route": tau_route,
    }


def _mean(values: list[float]) -> float:
    """Compute mean of values list."""
    return float(sum(values) / len(values)) if values else 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi] range."""
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
