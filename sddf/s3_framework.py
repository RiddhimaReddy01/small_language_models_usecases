from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Dimension = Literal["TC", "OS", "SK", "DS", "LT", "VL"]
Tier = Literal["pure_slm", "hybrid", "llm_only", "disqualified"]

REQUIRED_DIMS: tuple[Dimension, ...] = ("TC", "OS", "SK", "DS", "LT", "VL")


@dataclass(frozen=True)
class GateResult:
    disqualified: bool
    min_tier: Tier | None
    reason: str


def _validate_1_to_5(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 1 or value > 5:
        raise ValueError(f"{name} must be an integer in [1,5], got: {value!r}")


def _validate_dimensions(mapping: dict[Dimension, int], label: str) -> None:
    missing = [d for d in REQUIRED_DIMS if d not in mapping]
    if missing:
        raise ValueError(f"{label} missing dimensions: {missing}")
    for d in REQUIRED_DIMS:
        _validate_1_to_5(f"{label}[{d}]", int(mapping[d]))


def prescreen_gate(scores: dict[Dimension, int]) -> GateResult:
    """Hard gate from S3 section 3.5/3.6."""
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
    S3 = [sum_i(scores_i * w_i) / sum_i(5 * w_i)] * 5
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
    gate = prescreen_gate(scores)
    if gate.disqualified:
        return {
            "disqualified": True,
            "gate_reason": gate.reason,
            "tier": "disqualified",
            "s3_score": 5.0,
            "tau_route": -1.0,
        }

    s3 = compute_s3_score(scores, weights)
    tier = tier_from_s3(s3, gate, tau1=tau1, tau2=tau2)
    tau_route = route_limit_from_sddf(tau_risk=tau_risk, tau_cap=tau_cap)
    return {
        "disqualified": False,
        "gate_reason": gate.reason,
        "tier": tier,
        "s3_score": s3,
        "tau_route": tau_route,
    }

