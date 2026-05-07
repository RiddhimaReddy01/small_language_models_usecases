"""
Use Case to Task Family Mapping (Paper Section 5)

Maps the 8 enterprise use cases (UC1-UC8) to their corresponding SDDF task families,
then uses consensus routing ratios (rho_bar) from those families to assign tiers
to the use cases (not the task families).

Reference: Paper Section 5 (Task-Family Mapping) and Section 7.4 (Runtime Results)
"""

from __future__ import annotations

from typing import Any

from .frozen_thresholds import validate_task_family
from .runtime_routing import tier_from_consensus_ratio


# Paper Section 5: Use Case to Task Family Mappings
# Maps each enterprise use case to its corresponding NLP task family
USECASE_TO_TASKFAMILY: dict[str, dict[str, Any]] = {
    "UC1": {
        "name": "SMS Threat Detection",
        "description": "Classify SMS messages as threat/benign",
        "task_family": "classification",
        "domain": "cybersecurity",
    },
    "UC2": {
        "name": "Invoice Field Extraction",
        "description": "Extract fixed fields from invoice documents",
        "task_family": "information_extraction",
        "domain": "finance",
    },
    "UC3": {
        "name": "Support Ticket Routing",
        "description": "Route support tickets into fixed categories",
        "task_family": "classification",
        "domain": "customer_service",
    },
    "UC4": {
        "name": "Product Review Sentiment",
        "description": "Predict sentiment class from product reviews",
        "task_family": "classification",
        "domain": "customer_service",
    },
    "UC5": {
        "name": "Automated Code Review",
        "description": "Classify code issues and suggest fixes",
        "task_family": "code_generation",
        "domain": "developer_tools",
    },
    "UC6": {
        "name": "Clinical Triage",
        "description": "Predict patient triage priority class",
        "task_family": "classification",
        "domain": "healthcare",
    },
    "UC7": {
        "name": "Legal Contract Risk",
        "description": "Classify contract clause risk with synthesis",
        "task_family": "summarization",
        "domain": "legal",
    },
    "UC8": {
        "name": "Financial Report Drafting",
        "description": "Draft financial narratives from tabular data",
        "task_family": "text_generation",
        "domain": "finance",
    },
}


def get_usecase_info(usecase_id: str) -> dict[str, Any]:
    """Get information about a use case."""
    if usecase_id not in USECASE_TO_TASKFAMILY:
        raise ValueError(f"Unknown use case: {usecase_id}")
    return dict(USECASE_TO_TASKFAMILY[usecase_id])


def get_task_family(usecase_id: str) -> str:
    """Get the task family for a use case."""
    return get_usecase_info(usecase_id)["task_family"]


def get_all_usecases() -> list[str]:
    """Get all use case IDs."""
    return sorted(USECASE_TO_TASKFAMILY.keys())


def assign_usecase_tiers(
    taskfamily_rho_bar: dict[str, float],
    slm_threshold: float = 0.50,
    llm_threshold: float = 0.30,
) -> dict[str, dict[str, Any]]:
    """
    Assign tiers to use cases based on task family consensus ratios.

    Tier thresholds are optimized via threshold sensitivity analysis (SelectiveNet-inspired).
    Provide optimal values from your sensitivity analysis; defaults are starting points.

    Args:
        taskfamily_rho_bar: Dict mapping task_family -> rho_bar
                           (from consensus aggregation across 3 SLMs)
        slm_threshold: Minimum ρ̄ for SLM tier (default 0.70, optimize via sensitivity analysis)
        llm_threshold: Maximum ρ̄ for LLM tier (default 0.30, optimize via sensitivity analysis)

    Returns:
        Dict mapping usecase_id -> {tier, rho_bar, explanation, taskfamily}
    """
    usecase_tiers = {}

    for usecase_id in get_all_usecases():
        info = get_usecase_info(usecase_id)
        task_family = info["task_family"]

        if task_family not in taskfamily_rho_bar:
            usecase_tiers[usecase_id] = {
                "usecase_id": usecase_id,
                "name": info["name"],
                "task_family": task_family,
                "tier": "UNKNOWN",
                "rho_bar": None,
                "explanation": f"No rho_bar computed for task family: {task_family}",
                "error": True,
            }
            continue

        rho_bar = taskfamily_rho_bar[task_family]
        tier = tier_from_consensus_ratio(rho_bar, slm_threshold, llm_threshold)

        # Explain tier decision with actual thresholds
        if rho_bar >= slm_threshold:
            explanation = f"High SLM routing confidence (rho_bar={rho_bar:.4f} >= {slm_threshold})"
        elif rho_bar < llm_threshold:
            explanation = f"Low SLM routing confidence (rho_bar={rho_bar:.4f} < {llm_threshold})"
        else:
            explanation = f"Mixed routing outcomes ({llm_threshold} <= rho_bar={rho_bar:.4f} < {slm_threshold})"

        usecase_tiers[usecase_id] = {
            "usecase_id": usecase_id,
            "name": info["name"],
            "task_family": task_family,
            "domain": info["domain"],
            "description": info["description"],
            "tier": tier,
            "rho_bar": rho_bar,
            "explanation": explanation,
            "error": False,
        }

    return usecase_tiers


def print_usecase_tier_summary(usecase_tiers: dict[str, dict[str, Any]]) -> None:
    """Print human-readable summary of use case tiers."""
    print("\n" + "=" * 100)
    print("USE CASE TIER ASSIGNMENTS (Paper Table 7.4 equivalent)")
    print("=" * 100)

    # Count tiers
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    for uc_result in usecase_tiers.values():
        if not uc_result.get("error", False):
            tier = uc_result.get("tier", "UNKNOWN")
            if tier in tier_counts:
                tier_counts[tier] += 1

    print(f"\nSummary:")
    print(f"  SLM tier:    {tier_counts['SLM']}")
    print(f"  HYBRID tier: {tier_counts['HYBRID']}")
    print(f"  LLM tier:    {tier_counts['LLM']}")

    # Print per-UC details
    print(f"\nPer-Use Case Results:")
    for usecase_id in get_all_usecases():
        result = usecase_tiers[usecase_id]

        if result.get("error", False):
            print(
                f"\n  {usecase_id} ({result.get('name', 'UNKNOWN')}): ERROR - {result.get('explanation', 'Unknown error')}"
            )
            continue

        print(f"\n  {usecase_id} ({result['name']}):")
        print(f"    Domain:       {result.get('domain', 'unknown')}")
        print(f"    Task family:  {result['task_family']}")
        print(f"    Consensus rho_bar: {result['rho_bar']:.4f}")
        print(f"    Tier:         {result['tier']}")
        print(f"    Explanation:  {result['explanation']}")

    print("\n" + "=" * 100)


def save_usecase_tier_results(
    usecase_tiers: dict[str, dict[str, Any]],
    output_path: Any,
) -> None:
    """Save use case tier results to JSON."""
    import json
    from pathlib import Path

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(usecase_tiers, f, indent=2)

    print(f"Use case tier results saved to {output_path}")


def map_taskfamily_results_to_usecases(
    taskfamily_results: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Convert task family results to use case tier assignments.

    Args:
        taskfamily_results: Dict from validation/test phase with
                           task_family -> {rho_bar, tier, ...}

    Returns:
        Dict mapping usecase_id -> {tier, rho_bar, explanation, ...}
    """
    # Extract rho_bar values per task family
    taskfamily_rho_bar = {}
    for task_family, result in taskfamily_results.items():
        if "consensus_metrics" in result:
            # From validation_with_frozen results
            taskfamily_rho_bar[task_family] = result["consensus_metrics"]["rho_bar"]
        elif "consensus_rho" in result:
            # From test_with_frozen results
            taskfamily_rho_bar[task_family] = result["consensus_rho"]
        elif "rho_bar" in result:
            # Direct rho_bar field
            taskfamily_rho_bar[task_family] = result["rho_bar"]

    # Assign tiers to use cases
    return assign_usecase_tiers(taskfamily_rho_bar)


def create_usecase_tier_report(
    validation_results: dict[str, Any],
    test_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Create comprehensive use case tier report from validation and test results.

    Args:
        validation_results: From validation_with_frozen pipeline
        test_results: From test_with_frozen pipeline

    Returns:
        Complete use case tier report with validation and test tiers
    """
    # Map validation task family results to use cases
    val_taskfamily_results = validation_results.get("results", {})
    val_usecase_tiers = map_taskfamily_results_to_usecases(val_taskfamily_results)

    # Map test task family results to use cases
    test_taskfamily_results = test_results.get("results", {})
    test_usecase_tiers = map_taskfamily_results_to_usecases(test_taskfamily_results)

    # Count agreements
    agreements = 0
    for usecase_id in get_all_usecases():
        val_tier = val_usecase_tiers[usecase_id].get("tier")
        test_tier = test_usecase_tiers[usecase_id].get("tier")
        if val_tier == test_tier and val_tier != "UNKNOWN":
            agreements += 1

    return {
        "summary": {
            "total_usecases": len(get_all_usecases()),
            "validation_tiers": {
                "SLM": sum(
                    1
                    for r in val_usecase_tiers.values()
                    if r.get("tier") == "SLM"
                ),
                "HYBRID": sum(
                    1
                    for r in val_usecase_tiers.values()
                    if r.get("tier") == "HYBRID"
                ),
                "LLM": sum(
                    1
                    for r in val_usecase_tiers.values()
                    if r.get("tier") == "LLM"
                ),
            },
            "test_tiers": {
                "SLM": sum(
                    1
                    for r in test_usecase_tiers.values()
                    if r.get("tier") == "SLM"
                ),
                "HYBRID": sum(
                    1
                    for r in test_usecase_tiers.values()
                    if r.get("tier") == "HYBRID"
                ),
                "LLM": sum(
                    1
                    for r in test_usecase_tiers.values()
                    if r.get("tier") == "LLM"
                ),
            },
            "tier_agreement": f"{agreements}/{len(get_all_usecases())}",
        },
        "validation": val_usecase_tiers,
        "test": test_usecase_tiers,
    }
