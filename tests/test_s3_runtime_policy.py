from __future__ import annotations

from sddf.s3_runtime_policy import enforce_runtime_policy


def test_disqualified_forces_baseline() -> None:
    assert enforce_runtime_policy("disqualified", "SLM") == "BASELINE"
    assert enforce_runtime_policy("disqualified", "HYBRID_ABSTAIN") == "BASELINE"


def test_llm_only_forces_baseline() -> None:
    assert enforce_runtime_policy("llm_only", "SLM") == "BASELINE"


def test_hybrid_allows_slm_or_escalation() -> None:
    assert enforce_runtime_policy("hybrid", "SLM") == "SLM"
    assert enforce_runtime_policy("hybrid", "HYBRID_ABSTAIN") == "HYBRID_ABSTAIN"
    assert enforce_runtime_policy("hybrid", "BASELINE") == "BASELINE"


def test_pure_slm_blocks_escalation_when_disabled() -> None:
    assert enforce_runtime_policy("pure_slm", "BASELINE", allow_pure_slm_escalation=False) == "SLM"

