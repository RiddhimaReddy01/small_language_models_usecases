from __future__ import annotations

from sddf.s3_feature_scoring import S3ScoringInput, score_s3_dimensions


def test_s3_dimension_scores_in_range() -> None:
    payload = S3ScoringInput(
        task="retrieval_grounded",
        prompt="Summarize patient records in strict JSON schema and include source citations.",
        expected_format="json",
        business_critical=True,
        data_classification="restricted",
        contains_pii=True,
        target_p99_ms=400,
        qps=120.0,
    )
    scores = score_s3_dimensions(payload)
    assert set(scores.keys()) == {"TC", "OS", "SK", "DS", "LT", "VL"}
    for value in scores.values():
        assert 1 <= value <= 5


def test_overrides_take_precedence() -> None:
    payload = S3ScoringInput(
        task="classification",
        prompt="Classify sentiment of short reviews.",
        overrides={"SK": 5, "LT": 1},
    )
    scores = score_s3_dimensions(payload)
    assert scores["SK"] == 5
    assert scores["LT"] == 1


def test_sensitive_prompt_pushes_ds() -> None:
    payload = S3ScoringInput(
        task="information_extraction",
        prompt="Extract SSN and bank account details from customer forms.",
        data_classification="confidential",
    )
    scores = score_s3_dimensions(payload)
    assert scores["DS"] >= 4

