"""
Runtime Routing with Consensus Aggregation (Paper Section 7)

Implements the query-level and use-case-level routing decisions using:
1. Frozen τ^consensus thresholds (Table 6.3)
2. Per-query failure probability from difficulty scoring
3. Consensus aggregation across three SLM models
4. Tier decision from aggregated routing ratio ρ̄

Reference: Sections 7.2-7.4 of the paper
"""

from __future__ import annotations

from typing import Literal

from .frozen_thresholds import get_frozen_threshold, validate_task_family

RouteDecision = Literal["SLM", "LLM"]
TierDecision = Literal["SLM", "HYBRID", "LLM"]


def route_query(
    p_fail: float,
    task_family: str,
) -> RouteDecision:
    """
    Route a single query based on failure probability (Paper Section 7.2).

    Args:
        p_fail: Predicted failure probability [0, 1]
        task_family: Task family name (e.g., "classification")

    Returns:
        "SLM" if p_fail < τ^consensus, else "LLM"

    Raises:
        ValueError if task_family not found in frozen thresholds
    """
    if not validate_task_family(task_family):
        raise ValueError(f"Unknown task family: {task_family}")

    tau = get_frozen_threshold(task_family)

    return "SLM" if p_fail < tau else "LLM"


def aggregate_routing_ratio(
    routes: list[RouteDecision],
) -> float:
    """
    Compute SLM routing ratio ρ = fraction routed to SLM (Paper Section 7.3).

    Args:
        routes: List of routing decisions for all queries

    Returns:
        ρ ∈ [0, 1] = (# SLM routes) / (# total routes)
    """
    if not routes:
        return 0.0

    slm_count = sum(1 for route in routes if route == "SLM")
    return float(slm_count) / len(routes)


def consensus_routing_ratio(
    ratios: dict[str, float],
) -> float:
    """
    Compute consensus routing ratio across three SLM models (Paper Section 7.3).

    Args:
        ratios: Dict mapping model names to ρ values
                Expected keys: qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b

    Returns:
        ρ̄ = (1/3) × Σ ρ(m)
    """
    if not ratios:
        return 0.0

    # Average across all provided models
    return sum(ratios.values()) / len(ratios)


def tier_from_consensus_ratio(
    rho_bar: float,
    slm_threshold: float = 0.50,
    llm_threshold: float = 0.30,
) -> TierDecision:
    """
    Map consensus routing ratio to deployment tier.

    Defaults match the paper runtime bands. Sensitivity analysis can override
    them for a deployment-specific operating point.

    Args:
        rho_bar: Consensus routing ratio ρ̄ ∈ [0, 1]
        slm_threshold: Minimum ρ̄ for SLM tier (default 0.70, optimized via sensitivity analysis)
        llm_threshold: Maximum ρ̄ for LLM tier (default 0.30, optimized via sensitivity analysis)

    Returns:
        Tier decision: "SLM", "HYBRID", or "LLM"

    Decision ranges:
        - SLM    if ρ̄ ≥ slm_threshold
        - HYBRID if llm_threshold < ρ̄ < slm_threshold
        - LLM    if ρ̄ ≤ llm_threshold
    """
    if rho_bar >= slm_threshold:
        return "SLM"
    elif rho_bar < llm_threshold:
        return "LLM"
    else:
        return "HYBRID"


def route_use_case(
    query_failures: dict[str, float],
    task_family: str,
    model_names: list[str] | None = None,
) -> dict[str, float | str | list[str]]:
    """
    Complete use-case routing workflow (Paper Sections 7.2-7.4).

    Args:
        query_failures: Dict mapping query_id → p_fail value
        task_family: Task family (e.g., "classification")
        model_names: Optional list of model names for consensus aggregation.
                    If None, uses default SLM models from paper.

    Returns:
        Dict with:
            - 'tier': Final tier decision (SLM/HYBRID/LLM)
            - 'rho_bar': Consensus routing ratio
            - 'slm_routes': List of query IDs routed to SLM
            - 'llm_routes': List of query IDs routed to LLM
    """
    if not validate_task_family(task_family):
        raise ValueError(f"Unknown task family: {task_family}")

    if model_names is None:
        model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

    # Route all queries
    slm_routes = []
    llm_routes = []

    for query_id, p_fail in query_failures.items():
        decision = route_query(p_fail, task_family)
        if decision == "SLM":
            slm_routes.append(query_id)
        else:
            llm_routes.append(query_id)

    # Compute routing ratio (would be per-model in full implementation)
    rho = aggregate_routing_ratio(
        ["SLM" if qid in slm_routes else "LLM" for qid in query_failures.keys()]
    )

    # Consensus (simplified: using single aggregate as ρ̄)
    rho_bar = rho

    # Tier decision
    tier = tier_from_consensus_ratio(rho_bar)

    return {
        "task_family": task_family,
        "tier": tier,
        "rho_bar": rho_bar,
        "slm_count": len(slm_routes),
        "llm_count": len(llm_routes),
        "total_queries": len(query_failures),
        "slm_routes": slm_routes,
        "llm_routes": llm_routes,
    }


def route_query_multimodel(
    p_fails_by_model: dict[str, float],
    task_family: str,
) -> dict[str, RouteDecision]:
    """
    Route a query across multiple models (Paper Section 7.2 extended).

    Args:
        p_fails_by_model: Dict mapping model_name → p_fail value
        task_family: Task family name

    Returns:
        Dict mapping model_name → route decision
    """
    if not validate_task_family(task_family):
        raise ValueError(f"Unknown task_family: {task_family}")

    return {
        model: route_query(p_fail, task_family)
        for model, p_fail in p_fails_by_model.items()
    }


def route_use_case_multimodel(
    query_failures_by_model: dict[str, dict[str, float]],
    task_family: str,
    slm_threshold: float = 0.50,
    llm_threshold: float = 0.30,
) -> dict[str, float | str]:
    """
    Complete multimodel use-case routing with consensus (Paper Sections 7.2-7.4).

    Tier thresholds are optimized via threshold sensitivity analysis. Values provided
    here are defaults; optimal values should be determined from sensitivity analysis.

    Args:
        query_failures_by_model: Dict mapping model_name → {query_id → p_fail}
        task_family: Task family name
        slm_threshold: Minimum ρ̄ for SLM tier (default 0.70, from sensitivity analysis)
        llm_threshold: Maximum ρ̄ for LLM tier (default 0.30, from sensitivity analysis)

    Returns:
        Dict with:
            - 'tier': Final tier decision based on optimal thresholds
            - 'rho_bar': Consensus ratio across models
            - 'per_model_rho': Dict of rho per model
            - 'per_model_routes': Dict of routing decisions per model
    """
    if not validate_task_family(task_family):
        raise ValueError(f"Unknown task_family: {task_family}")

    per_model_rho = {}
    per_model_routes = {}

    # Route queries for each model
    for model_name, query_failures in query_failures_by_model.items():
        routes = [
            route_query(p_fail, task_family)
            for p_fail in query_failures.values()
        ]
        rho = aggregate_routing_ratio(routes)
        per_model_rho[model_name] = rho
        per_model_routes[model_name] = routes

    # Consensus aggregation across models
    rho_bar = consensus_routing_ratio(per_model_rho)

    # Tier decision using optimal thresholds from sensitivity analysis
    tier = tier_from_consensus_ratio(rho_bar, slm_threshold, llm_threshold)

    return {
        "task_family": task_family,
        "tier": tier,
        "rho_bar": rho_bar,
        "per_model_rho": per_model_rho,
        "per_model_routes": per_model_routes,
        "thresholds": {
            "slm_threshold": slm_threshold,
            "llm_threshold": llm_threshold,
        },
    }
