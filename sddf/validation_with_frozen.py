"""
Validation Pipeline with Frozen Thresholds (Paper Table 6.3)

Instead of learning thresholds from validation data, this module:
1. Uses frozen tau^consensus values directly from the paper
2. Applies them to compute per-model routing metrics
3. Validates that frozen thresholds work on the data
4. Generates consensus routing ratios (rho_bar)

Reference: Paper Section 7 (Runtime Deployment)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .frozen_thresholds import (
    FROZEN_TAU_CONSENSUS,
    get_frozen_threshold,
    validate_task_family,
)
from .runtime_routing import (
    route_query,
    aggregate_routing_ratio,
    consensus_routing_ratio,
    tier_from_consensus_ratio,
)


def validate_frozen_thresholds_on_task(
    task_family: str,
    model_names: list[str],
    query_difficulties: dict[str, dict[str, float]],
    query_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate frozen thresholds on a task family across multiple models.

    Args:
        task_family: Task family name (e.g., "classification")
        model_names: List of model names (typically 3 SLMs)
        query_difficulties: Dict[model_name -> Dict[query_id -> difficulty_score]]
        query_results: Dict[query_id -> Dict with "slm_correct", "llm_correct", etc.]

    Returns:
        Dict with per-model metrics and consensus aggregation:
            {
                'task_family': str,
                'tau_frozen': float,
                'per_model_metrics': {
                    'model_name': {
                        'rho': float,  # SLM routing ratio
                        'slm_routed': int,
                        'llm_routed': int,
                        'routes': list[str],  # "SLM" or "LLM" per query
                    }
                },
                'consensus_metrics': {
                    'rho_bar': float,  # Consensus routing ratio
                    'tier': str,       # SLM, HYBRID, or LLM
                    'explanation': str,
                },
                'quality_metrics': {
                    'slm_accuracy': float,
                    'llm_accuracy': float,
                    'slm_failures': int,
                    'total_queries': int,
                }
            }
    """
    if not validate_task_family(task_family):
        raise ValueError(f"Unknown task family: {task_family}")

    tau_frozen = get_frozen_threshold(task_family)

    # Route queries for each model
    per_model_metrics = {}
    per_model_rho = {}

    for model_name in model_names:
        if model_name not in query_difficulties:
            continue

        difficulties = query_difficulties[model_name]
        routes = []

        for query_id, difficulty in difficulties.items():
            decision = route_query(difficulty, task_family)
            routes.append(decision)

        rho = aggregate_routing_ratio(routes)
        slm_count = sum(1 for r in routes if r == "SLM")
        llm_count = len(routes) - slm_count

        per_model_metrics[model_name] = {
            "rho": rho,
            "slm_routed": slm_count,
            "llm_routed": llm_count,
            "routes": routes,
        }
        per_model_rho[model_name] = rho

    # Consensus aggregation
    rho_bar = consensus_routing_ratio(per_model_rho) if per_model_rho else 0.0
    tier = tier_from_consensus_ratio(rho_bar)

    # Explain tier
    if rho_bar >= 0.70:
        explanation = f"High SLM routing confidence (rho_bar={rho_bar:.4f} >= 0.70)"
    elif rho_bar <= 0.30:
        explanation = f"Low SLM routing confidence (rho_bar={rho_bar:.4f} <= 0.30)"
    else:
        explanation = f"Mixed routing outcomes (0.30 < rho_bar={rho_bar:.4f} < 0.70)"

    # Quality metrics
    slm_correct_count = 0
    llm_correct_count = 0
    slm_failures = 0
    total_queries = 0

    for query_id, result in query_results.items():
        total_queries += 1
        if result.get("slm_correct", False):
            slm_correct_count += 1
        if result.get("llm_correct", False):
            llm_correct_count += 1
        if not result.get("slm_correct", False):
            slm_failures += 1

    slm_accuracy = slm_correct_count / total_queries if total_queries > 0 else 0.0
    llm_accuracy = llm_correct_count / total_queries if total_queries > 0 else 0.0

    return {
        "task_family": task_family,
        "tau_frozen": tau_frozen,
        "per_model_metrics": per_model_metrics,
        "consensus_metrics": {
            "rho_bar": rho_bar,
            "tier": tier,
            "explanation": explanation,
        },
        "quality_metrics": {
            "slm_accuracy": slm_accuracy,
            "llm_accuracy": llm_accuracy,
            "slm_failures": slm_failures,
            "total_queries": total_queries,
        },
    }


def validate_all_tasks(
    task_families: list[str],
    model_names: list[str],
    query_difficulties_by_task: dict[str, dict[str, dict[str, float]]],
    query_results_by_task: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """
    Validate frozen thresholds across all task families.

    Returns:
        {
            'summary': {
                'tasks_validated': int,
                'slm_tier_count': int,
                'hybrid_tier_count': int,
                'llm_tier_count': int,
            },
            'results': {
                'task_family': {validation results}
            }
        }
    """
    results = {}
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}

    for task_family in task_families:
        if task_family not in query_difficulties_by_task:
            continue

        try:
            task_result = validate_frozen_thresholds_on_task(
                task_family,
                model_names,
                query_difficulties_by_task[task_family],
                query_results_by_task.get(task_family, {}),
            )
            results[task_family] = task_result
            tier = task_result["consensus_metrics"]["tier"]
            tier_counts[tier] += 1
        except Exception as e:
            results[task_family] = {"error": str(e)}

    return {
        "summary": {
            "tasks_validated": len(results),
            "slm_tier_count": tier_counts["SLM"],
            "hybrid_tier_count": tier_counts["HYBRID"],
            "llm_tier_count": tier_counts["LLM"],
        },
        "results": results,
    }


def save_validation_report(
    validation_results: dict[str, Any],
    output_path: Path | str,
) -> None:
    """Save validation results with frozen thresholds to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(validation_results, f, indent=2)

    print(f"Validation report saved to {output_path}")


def print_validation_summary(validation_results: dict[str, Any]) -> None:
    """Print human-readable validation summary."""
    summary = validation_results.get("summary", {})

    print("\n" + "=" * 80)
    print("FROZEN THRESHOLD VALIDATION SUMMARY")
    print("=" * 80)

    print(f"\nTasks validated: {summary.get('tasks_validated', 0)}")
    print(f"SLM tier:       {summary.get('slm_tier_count', 0)}")
    print(f"HYBRID tier:    {summary.get('hybrid_tier_count', 0)}")
    print(f"LLM tier:       {summary.get('llm_tier_count', 0)}")

    print("\nPer-task results:")
    for task_family, result in validation_results.get("results", {}).items():
        if "error" in result:
            print(f"  {task_family}: ERROR - {result['error']}")
            continue

        tau = result.get("tau_frozen", 0)
        rho_bar = result["consensus_metrics"]["rho_bar"]
        tier = result["consensus_metrics"]["tier"]
        explanation = result["consensus_metrics"]["explanation"]

        print(f"\n  {task_family}:")
        print(f"    tau_frozen: {tau:.4f}")
        print(f"    rho_bar:    {rho_bar:.4f} => {tier}")
        print(f"    {explanation}")

    print("\n" + "=" * 80)
