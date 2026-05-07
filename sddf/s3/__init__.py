"""S3 subpackage: Scoring, Governance, and Policy modules."""

from .governance import (
    GateResult,
    compute_s3_score,
    decide_s3_and_route,
    prescreen_gate,
    recommend_s3_score_overrides,
    recommend_task_tier_thresholds,
    tier_from_s3,
)
from .policy import enforce_runtime_policy
from .scoring import (
    DEFAULT_S3_WEIGHTS,
    S3ScoringInput,
    build_s3_task_config,
    build_task_scores,
    normalize_weights,
    score_data_sensitivity,
    score_latency_tolerance,
    score_output_structure,
    score_s3_dimensions,
    score_stakes,
    score_task_complexity,
    score_volume_load,
)

__all__ = [
    # Scoring exports
    "S3ScoringInput",
    "DEFAULT_S3_WEIGHTS",
    "score_task_complexity",
    "score_output_structure",
    "score_stakes",
    "score_data_sensitivity",
    "score_latency_tolerance",
    "score_volume_load",
    "score_s3_dimensions",
    "normalize_weights",
    "build_task_scores",
    "build_s3_task_config",
    # Governance exports
    "GateResult",
    "prescreen_gate",
    "compute_s3_score",
    "tier_from_s3",
    "decide_s3_and_route",
    "recommend_task_tier_thresholds",
    "recommend_s3_score_overrides",
    # Policy exports
    "enforce_runtime_policy",
]
