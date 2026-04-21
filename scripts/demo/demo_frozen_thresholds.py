#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo: Using Frozen Thresholds and Runtime Routing with Consensus Aggregation

This script demonstrates:
1. Using frozen tau^consensus from Table 6.3
2. Query-level routing decisions
3. Consensus aggregation across models
4. Tier assignment from aggregated routing ratio

Reference: Paper Sections 7.2-7.4
"""

from sddf import (
    FROZEN_TAU_CONSENSUS,
    get_frozen_threshold,
    route_query,
    aggregate_routing_ratio,
    consensus_routing_ratio,
    tier_from_consensus_ratio,
    route_use_case_multimodel,
)


def demo_frozen_thresholds():
    """Demo 1: Show frozen thresholds from Table 6.3"""
    print("\n" + "=" * 80)
    print("DEMO 1: Frozen Thresholds (Paper Table 6.3)")
    print("=" * 80)

    print("\nAll frozen tau^consensus values:")
    for task_family, tau in sorted(FROZEN_TAU_CONSENSUS.items()):
        print(f"  {task_family:25s}: tau_consensus = {tau:.4f}")

    print("\nFrozen thresholds loaded successfully")


def demo_query_level_routing():
    """Demo 2: Single query routing decision"""
    print("\n" + "=" * 80)
    print("DEMO 2: Query-Level Routing (Paper Section 7.2)")
    print("=" * 80)

    task_family = "classification"
    tau = get_frozen_threshold(task_family)

    print(f"\nTask family: {task_family}")
    print(f"Frozen threshold tau_consensus: {tau:.4f}")

    # Test different failure probabilities
    test_cases = [
        ("Low difficulty query", 0.2),
        ("Medium difficulty query", 0.5),
        ("High difficulty query", 0.8),
    ]

    print("\nRouting decisions:")
    for desc, p_fail in test_cases:
        decision = route_query(p_fail, task_family)
        comparison = "< tau" if p_fail < tau else ">= tau"
        print(f"  p_fail={p_fail:.2f} {comparison} {tau:.4f} => Route: {decision}")

    print("\nQuery-level routing working")


def demo_aggregation():
    """Demo 3: Consensus aggregation across models"""
    print("\n" + "=" * 80)
    print("DEMO 3: Consensus Aggregation (Paper Section 7.3)")
    print("=" * 80)

    # Simulated routing ratios from three SLM models
    per_model_rho = {
        "qwen2.5_0.5b": 0.68,
        "qwen2.5_3b": 0.76,
        "qwen2.5_7b": 0.56,
    }

    print("\nPer-model routing ratios rho(m):")
    for model, rho in per_model_rho.items():
        print(f"  {model}: rho = {rho:.4f}")

    # Consensus aggregation
    rho_bar = consensus_routing_ratio(per_model_rho)
    print(f"\nConsensus aggregation:")
    print(f"  rho_bar = (1/3) * Sum[rho(m)] = {rho_bar:.4f}")

    # Tier decision
    tier = tier_from_consensus_ratio(rho_bar)
    print(f"\nTier decision from rho_bar = {rho_bar:.4f}:")
    print(f"  => Tier = {tier}")

    print("\nConsensus aggregation working")


def demo_multimodel_routing():
    """Demo 4: Complete multimodel use-case routing"""
    print("\n" + "=" * 80)
    print("DEMO 4: Complete Use-Case Routing with Consensus (Paper Sections 7.2-7.4)")
    print("=" * 80)

    task_family = "classification"
    tau = get_frozen_threshold(task_family)

    # Simulated failure probabilities for 10 queries across 3 models
    query_failures_by_model = {
        "qwen2.5_0.5b": {
            f"query_{i}": 0.3 + i * 0.05 for i in range(10)
        },
        "qwen2.5_3b": {
            f"query_{i}": 0.4 + i * 0.03 for i in range(10)
        },
        "qwen2.5_7b": {
            f"query_{i}": 0.35 + i * 0.04 for i in range(10)
        },
    }

    print(f"\nTask family: {task_family}")
    print(f"Frozen threshold tau_consensus: {tau:.4f}")
    print(f"Number of queries: 10")
    print(f"Number of models: 3")

    # Route the use case
    result = route_use_case_multimodel(query_failures_by_model, task_family)

    print(f"\nPer-model routing ratios:")
    for model, rho in result["per_model_rho"].items():
        slm_count = sum(
            1
            for route in result["per_model_routes"][model]
            if route == "SLM"
        )
        print(f"  {model}: rho = {rho:.4f} ({slm_count}/10 to SLM)")

    print(f"\nConsensus aggregation:")
    print(f"  rho_bar = {result['rho_bar']:.4f}")

    print(f"\nTier decision:")
    print(f"  => {result['tier']}")

    # Explain tier decision
    rho_bar = result["rho_bar"]
    if rho_bar >= 0.70:
        explanation = "High SLM routing confidence (rho_bar >= 0.70)"
    elif rho_bar <= 0.30:
        explanation = "Low SLM routing confidence (rho_bar <= 0.30)"
    else:
        explanation = "Mixed routing outcomes (0.30 < rho_bar < 0.70)"

    print(f"  ({explanation})")

    print("\nComplete multimodel routing working")


def demo_comparison():
    """Demo 5: Show difference between paper frozen and old code learned values"""
    print("\n" + "=" * 80)
    print("DEMO 5: Paper (Frozen) vs Code (Learned) Thresholds")
    print("=" * 80)

    # Old code-learned values (from earlier comparison)
    code_learned = {
        "classification": 0.15,  # avg of learned values
        "code_generation": 0.002,
        "information_extraction": 0.236,
        "instruction_following": 0.142,
        "maths": 0.0,
        "retrieval_grounded": 0.348,
        "summarization": 0.012,
        "text_generation": 0.081,
    }

    print("\nThreshold comparison:")
    print(f"{'Task Family':<25} {'Paper Frozen':>15} {'Code Learned':>15} {'Difference':>12}")
    print("-" * 70)

    total_diff = 0
    for task in sorted(FROZEN_TAU_CONSENSUS.keys()):
        paper = FROZEN_TAU_CONSENSUS[task]
        code = code_learned.get(task, 0.0)
        diff = abs(paper - code)
        total_diff += diff
        print(f"{task:<25} {paper:>15.4f} {code:>15.4f} {diff:>12.4f}")

    avg_diff = total_diff / len(FROZEN_TAU_CONSENSUS)
    print(f"\nAverage absolute difference: {avg_diff:.4f}")
    max_code = max(code_learned.values()) if max(code_learned.values()) > 0 else 1.0
    print(f"Scale factor: Paper values are ~{max(FROZEN_TAU_CONSENSUS.values()) / max_code:.1f}x larger")

    print("\nFrozen thresholds are significantly different from old learned values")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FROZEN THRESHOLDS & CONSENSUS AGGREGATION DEMO")
    print("Paper: A Unified Framework for Enterprise SLM Deployment (v3)")
    print("=" * 80)

    demo_frozen_thresholds()
    demo_query_level_routing()
    demo_aggregation()
    demo_multimodel_routing()
    demo_comparison()

    print("\n" + "=" * 80)
    print("ALL DEMOS COMPLETED SUCCESSFULLY [OK]")
    print("=" * 80)
    print("\nKey takeaways:")
    print("1. Frozen tau^consensus from Table 6.3 are now available")
    print("2. Query-level routing uses frozen thresholds (not learned values)")
    print("3. Consensus aggregation computes rho_bar across models")
    print("4. Tier decisions come from aggregated rho_bar")
    print("\nNext steps:")
    print("- Integrate frozen thresholds into validation/test pipeline")
    print("- Update runtime routing to use consensus aggregation")
    print("- Regenerate results with frozen thresholds")
    print()
