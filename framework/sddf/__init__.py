from .curves import compute_ratio_curve, smooth_ratio_curve
from .difficulty import (
    TASK_DIMENSION_MAP,
    annotate_dominant_dimension,
    compute_constraint_count,
    compute_entropy,
    compute_n_in,
    compute_reasoning_proxy,
    make_difficulty_bins,
)
from .gates import apply_quality_gate, evaluate_quality_gate, label_slm_acceptability
from .ingest import (
    infer_model_family,
    normalize_classification_results,
    normalize_code_generation_results,
    normalize_ie_predictions,
    normalize_instruction_following_results,
    normalize_maths_results,
    normalize_retrieval_grounded_predictions,
    normalize_summarization_results,
    normalize_text_generation_results,
)
from .matching import match_model_outputs
from .pipeline import run_sddf_postprocess
from .reporting import generate_part_b_report
from .routing import learn_routing_thresholds, route_example, route_example_three_way
from .schema import REQUIRED_RESULT_COLUMNS, validate_results_schema
from .setup_reporting import generate_part_a_report
from .tipping import DEFAULT_TIPPING_THRESHOLDS, estimate_tipping_point, tipping_sensitivity
from .uncertainty import bootstrap_ratio_curve, bootstrap_tipping_point
from .zones import assign_deployment_zone, assign_zone_capability_ops

__all__ = [
    "REQUIRED_RESULT_COLUMNS",
    "TASK_DIMENSION_MAP",
    "annotate_dominant_dimension",
    "apply_quality_gate",
    "assign_deployment_zone",
    "assign_zone_capability_ops",
    "bootstrap_ratio_curve",
    "bootstrap_tipping_point",
    "compute_constraint_count",
    "compute_entropy",
    "compute_n_in",
    "compute_ratio_curve",
    "compute_reasoning_proxy",
    "DEFAULT_TIPPING_THRESHOLDS",
    "estimate_tipping_point",
    "evaluate_quality_gate",
    "generate_part_b_report",
    "generate_part_a_report",
    "infer_model_family",
    "label_slm_acceptability",
    "learn_routing_thresholds",
    "make_difficulty_bins",
    "match_model_outputs",
    "normalize_classification_results",
    "normalize_code_generation_results",
    "normalize_ie_predictions",
    "normalize_instruction_following_results",
    "normalize_maths_results",
    "normalize_retrieval_grounded_predictions",
    "normalize_summarization_results",
    "normalize_text_generation_results",
    "route_example",
    "route_example_three_way",
    "run_sddf_postprocess",
    "smooth_ratio_curve",
    "tipping_sensitivity",
    "validate_results_schema",
]
