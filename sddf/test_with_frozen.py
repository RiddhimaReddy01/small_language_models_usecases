"""
Test Phase with Frozen Thresholds (Paper Section 7)

Applies frozen tau^consensus values to test set and evaluates:
1. Per-model routing decisions
2. Consensus aggregation
3. Tier assignment
4. Quality metrics (accuracy, failures, etc.)

Reference: Paper Section 7 (Runtime Deployment)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .frozen_thresholds import FROZEN_TAU_CONSENSUS
from .runtime_routing import route_use_case_multimodel


def evaluate_frozen_thresholds_on_test(
    task_family: str,
    model_names: list[str],
    test_samples: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """
    Evaluate frozen thresholds on test set.

    Args:
        task_family: Task family name
        model_names: List of model names
        test_samples: Dict[model_name -> Dict[query_id -> sample_dict]]
                     sample_dict must have: "p_fail", "slm_correct", "llm_correct"

    Returns:
        Dict with complete test evaluation:
            {
                'task_family': str,
                'tau_frozen': float,
                'total_queries': int,
                'tier_decision': str,
                'consensus_rho': float,
                'per_model_results': {
                    'model_name': {
                        'rho': float,
                        'slm_routed': int,
                        'llm_routed': int,
                        'accuracy_on_slm_routes': float,
                        'accuracy_on_llm_routes': float,
                    }
                },
                'aggregate_metrics': {
                    'slm_accuracy': float,
                    'llm_accuracy': float,
                    'slm_failures': int,
                    'total_failures': int,
                    'failure_rate': float,
                }
            }
    """
    tau = FROZEN_TAU_CONSENSUS[task_family]

    # Prepare failure probabilities for routing
    query_failures_by_model = {}
    for model_name in model_names:
        if model_name not in test_samples:
            continue
        query_failures_by_model[model_name] = {
            qid: sample.get("p_fail", 0.5)
            for qid, sample in test_samples[model_name].items()
        }

    # Route using consensus
    routing_result = route_use_case_multimodel(query_failures_by_model, task_family)

    # Compute quality metrics
    per_model_results = {}
    total_slm_correct = 0
    total_llm_correct = 0
    total_failures = 0
    total_queries = 0

    for model_name in model_names:
        if model_name not in test_samples:
            continue

        samples = test_samples[model_name]
        routes = routing_result["per_model_routes"][model_name]

        slm_correct_on_slm = 0
        llm_correct_on_llm = 0
        slm_routed = 0
        llm_routed = 0

        for (query_id, sample), route in zip(samples.items(), routes):
            total_queries += 1
            slm_correct = sample.get("slm_correct", False)
            llm_correct = sample.get("llm_correct", False)

            if slm_correct:
                total_slm_correct += 1
            if llm_correct:
                total_llm_correct += 1
            if not slm_correct:
                total_failures += 1

            if route == "SLM":
                slm_routed += 1
                if slm_correct:
                    slm_correct_on_slm += 1
            else:
                llm_routed += 1
                if llm_correct:
                    llm_correct_on_llm += 1

        slm_acc = slm_correct_on_slm / slm_routed if slm_routed > 0 else 0.0
        llm_acc = llm_correct_on_llm / llm_routed if llm_routed > 0 else 0.0

        per_model_results[model_name] = {
            "rho": routing_result["per_model_rho"][model_name],
            "slm_routed": slm_routed,
            "llm_routed": llm_routed,
            "accuracy_on_slm_routes": slm_acc,
            "accuracy_on_llm_routes": llm_acc,
        }

    # Aggregate metrics
    overall_slm_acc = total_slm_correct / total_queries if total_queries > 0 else 0.0
    overall_llm_acc = total_llm_correct / total_queries if total_queries > 0 else 0.0
    failure_rate = total_failures / total_queries if total_queries > 0 else 0.0

    return {
        "task_family": task_family,
        "tau_frozen": tau,
        "total_queries": total_queries,
        "tier_decision": routing_result["tier"],
        "consensus_rho": routing_result["rho_bar"],
        "per_model_results": per_model_results,
        "aggregate_metrics": {
            "slm_accuracy": overall_slm_acc,
            "llm_accuracy": overall_llm_acc,
            "slm_failures": total_failures,
            "total_failures": total_failures,
            "failure_rate": failure_rate,
        },
    }


def run_test_phase(
    task_families: list[str],
    model_names: list[str],
    test_samples_by_task: dict[str, dict[str, dict[str, dict[str, Any]]]],
) -> dict[str, Any]:
    """
    Run complete test phase for all task families.

    Args:
        task_families: List of task family names
        model_names: List of model names
        test_samples_by_task: Dict[task_family -> Dict[model_name -> Dict[query_id -> sample]]]

    Returns:
        Complete test results with summary and per-task details
    """
    results = {}

    for task_family in task_families:
        if task_family not in test_samples_by_task:
            continue

        try:
            task_result = evaluate_frozen_thresholds_on_test(
                task_family,
                model_names,
                test_samples_by_task[task_family],
            )
            results[task_family] = task_result
        except Exception as e:
            results[task_family] = {"error": str(e)}

    # Summary statistics
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    total_failures = 0
    total_queries = 0

    for task_result in results.values():
        if "error" not in task_result:
            tier = task_result.get("tier_decision", "UNKNOWN")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            total_failures += task_result.get("aggregate_metrics", {}).get("slm_failures", 0)
            total_queries += task_result.get("total_queries", 0)

    return {
        "summary": {
            "tasks_evaluated": len([r for r in results.values() if "error" not in r]),
            "tier_distribution": tier_counts,
            "total_queries": total_queries,
            "total_failures": total_failures,
            "overall_failure_rate": total_failures / total_queries if total_queries > 0 else 0.0,
        },
        "frozen_thresholds": dict(FROZEN_TAU_CONSENSUS),
        "results": results,
    }


def save_test_results(test_results: dict[str, Any], output_path: Path | str) -> None:
    """Save test results to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"Test results saved to {output_path}")


def print_test_summary(test_results: dict[str, Any]) -> None:
    """Print human-readable test summary."""
    summary = test_results.get("summary", {})

    print("\n" + "=" * 80)
    print("FROZEN THRESHOLD TEST RESULTS")
    print("=" * 80)

    print(f"\nTasks evaluated:  {summary.get('tasks_evaluated', 0)}")
    print(f"Total queries:    {summary.get('total_queries', 0)}")
    print(f"Total failures:   {summary.get('total_failures', 0)}")
    print(f"Failure rate:     {summary.get('overall_failure_rate', 0):.2%}")

    tiers = summary.get("tier_distribution", {})
    print(f"\nTier distribution:")
    print(f"  SLM:            {tiers.get('SLM', 0)}")
    print(f"  HYBRID:         {tiers.get('HYBRID', 0)}")
    print(f"  LLM:            {tiers.get('LLM', 0)}")

    print(f"\nFrozen thresholds used:")
    for task, tau in sorted(test_results.get("frozen_thresholds", {}).items()):
        print(f"  {task:25s}: tau = {tau:.4f}")

    print("\nPer-task results:")
    for task_family, result in test_results.get("results", {}).items():
        if "error" in result:
            print(f"\n  {task_family}: ERROR - {result['error']}")
            continue

        metrics = result.get("aggregate_metrics", {})
        print(f"\n  {task_family}:")
        print(f"    Tier:           {result.get('tier_decision', 'UNKNOWN')}")
        print(f"    Consensus rho:  {result.get('consensus_rho', 0):.4f}")
        print(f"    SLM accuracy:   {metrics.get('slm_accuracy', 0):.2%}")
        print(f"    LLM accuracy:   {metrics.get('llm_accuracy', 0):.2%}")
        print(f"    Failures:       {metrics.get('slm_failures', 0)}/{result.get('total_queries', 0)}")

    print("\n" + "=" * 80)
