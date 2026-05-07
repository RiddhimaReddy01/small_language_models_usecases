from __future__ import annotations

from sddf.s3 import decide_s3_and_route


def test_gate_override_exposes_formula_and_final_tier() -> None:
    # Low formula score but SK=4 should force final tier to hybrid.
    decision = decide_s3_and_route(
        scores={"TC": 2, "OS": 2, "SK": 4, "DS": 2, "LT": 2, "VL": 2},
        weights={"TC": 3, "OS": 2, "SK": 4, "DS": 2, "LT": 3, "VL": 1},
        tau_risk=0.4,
        tau_cap=0.5,
        tau1=3.2,
        tau2=4.0,
    )
    assert decision["disqualified"] is False
    assert decision["formula_tier"] == "pure_slm"
    assert decision["final_tier"] == "hybrid"
    assert decision["tier"] == "hybrid"


def test_disqualified_case_sets_both_tiers_disqualified() -> None:
    decision = decide_s3_and_route(
        scores={"TC": 5, "OS": 3, "SK": 4, "DS": 2, "LT": 2, "VL": 2},
        weights={"TC": 3, "OS": 2, "SK": 4, "DS": 2, "LT": 3, "VL": 1},
        tau_risk=0.4,
        tau_cap=0.5,
        tau1=3.2,
        tau2=4.0,
    )
    assert decision["disqualified"] is True
    assert decision["formula_tier"] == "disqualified"
    assert decision["final_tier"] == "disqualified"
    assert decision["tier"] == "disqualified"

