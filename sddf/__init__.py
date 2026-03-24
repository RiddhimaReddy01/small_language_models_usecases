from .curves import compute_ratio_curve, smooth_ratio_curve
from .difficulty import (
    annotate_dominant_dimension,
    compute_constraint_count,
    compute_dependency_distance,
    compute_entropy,
    compute_n_in,
    compute_parametric_dependence,
    compute_reasoning_proxy,
    make_difficulty_bins,
)
from .difficulty_weights import DifficultyWeightLearner
from .failure_taxonomy import FailureTaxonomy
from .gates import apply_quality_gate, evaluate_quality_gate, label_slm_acceptability
from .matching import match_model_outputs
from .routing import learn_routing_thresholds, route_example, route_example_three_way
from .tipping import estimate_tipping_point
from .zones import assign_deployment_zone

__all__ = [
    "annotate_dominant_dimension",
    "make_difficulty_bins",
    "compute_n_in",
    "compute_entropy",
    "compute_constraint_count",
    "compute_reasoning_proxy",
    "compute_parametric_dependence",
    "compute_dependency_distance",
    "DifficultyWeightLearner",
    "compute_ratio_curve",
    "smooth_ratio_curve",
    "label_slm_acceptability",
    "apply_quality_gate",
    "evaluate_quality_gate",
    "learn_routing_thresholds",
    "route_example",
    "route_example_three_way",
    "estimate_tipping_point",
    "assign_deployment_zone",
    "match_model_outputs",
    "FailureTaxonomy",
]
