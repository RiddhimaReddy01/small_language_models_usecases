from __future__ import annotations

from sddf.s3 import recommend_s3_score_overrides, recommend_task_tier_thresholds


def test_recommend_task_tier_thresholds_lowers_on_high_failure() -> None:
    current = {"*": {"tau1": 3.2, "tau2": 4.0}}
    test_report = {
        "runs": [
            {"task": "code_generation", "test_metrics": {"positive_rate": 0.75, "f1": 0.50, "ece_10bin": 0.30}},
            {"task": "code_generation", "test_metrics": {"positive_rate": 0.70, "f1": 0.55, "ece_10bin": 0.28}},
        ]
    }
    rec = recommend_task_tier_thresholds(current_thresholds=current, test_report=test_report)
    assert "code_generation" in rec
    assert rec["code_generation"]["tau1"] < 3.2
    assert rec["code_generation"]["tau2"] < 4.0


def test_recommend_s3_score_overrides_from_tau_pressure() -> None:
    bridge = {
        "results": [
            {"task": "maths", "decision": {"s3_score": 2.4}},
            {"task": "classification", "decision": {"s3_score": 2.0}},
        ]
    }
    val = {
        "runs": [
            {"task": "maths", "tau_cap": 0.1, "tau_risk": 0.2},
            {"task": "classification", "tau_cap": 9, "tau_risk": 9},
        ]
    }
    rec = recommend_s3_score_overrides(bridge_output=bridge, val_report=val)
    assert rec["maths"]["SK"] >= 3
    assert rec["maths"]["TC"] >= 3

