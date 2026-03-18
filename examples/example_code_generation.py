#!/usr/bin/env python3
"""
Example: Complete Routing System for Code Generation

Demonstrates Phase 0 (Analysis), Phase 1 (Production), and Phase 2 (Monitoring).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.routing import ProductionRouter, AnalysisResult


def main():
    """Complete example workflow"""

    print("=" * 80)
    print("CODE GENERATION ROUTING EXAMPLE")
    print("=" * 80)

    # ========== PHASE 0: Analysis ==========
    print("\nPHASE 0: Analysis (One-time)")
    print("-" * 80)

    # Simulate analysis results from benchmarks
    qwen_analysis = AnalysisResult(
        task="code_generation",
        model="qwen",
        capability_curve={
            0: 0.67,  # Bin 0 (easy): 67% accuracy
            1: 0.80,  # Bin 1 (medium): 80% accuracy
            2: 0.80,  # Bin 2 (med-hard): 80% accuracy
            3: 0.67,  # Bin 3 (hard): 67% accuracy
            4: 0.73   # Bin 4 (very hard): 73% accuracy
        },
        risk_curve={
            0: 0.33,  # Bin 0: 33% failure rate
            1: 0.20,  # Bin 1: 20% failure rate
            2: 0.20,  # Bin 2: 20% failure rate
            3: 0.33,  # Bin 3: 33% failure rate
            4: 0.27   # Bin 4: 27% failure rate
        },
        tau_cap=2,              # Capable through bin 2
        tau_risk=0,             # Risky from bin 0
        zone="Q4",              # Low capability + High risk
        empirical_tau_c=0.80,
        empirical_tau_r=0.20
    )

    router = ProductionRouter()
    router.add_analysis_result(qwen_analysis)

    print("[OK] Registered analysis for " + qwen_analysis.model)
    print("  - Capability curve: " + str(qwen_analysis.capability_curve))
    print("  - Risk curve: " + str(qwen_analysis.risk_curve))
    print("  - tau_cap = {}, tau_risk = {}".format(qwen_analysis.tau_cap, qwen_analysis.tau_risk))
    print("  - Zone: " + qwen_analysis.zone)

    # ========== PHASE 1: Production Routing ==========
    print("\n\nPHASE 1: Production Routing (Per-request)")
    print("-" * 80)

    def code_difficulty(text: str) -> float:
        """Difficulty metric for code generation based on input length"""
        return min(len(text) / 1000, 1.0)

    test_requests = [
        ("Write a function to reverse a list", "easy"),
        ("Implement quicksort algorithm", "easy"),
        ("Build a web crawler", "medium"),
        ("Implement distributed consensus", "hard"),
    ]

    for prompt, expected_difficulty in test_requests:
        model, decision = router.route(
            input_text=prompt,
            task="code_generation",
            difficulty_metric=code_difficulty,
            preferred_model="qwen"
        )

        print("\nRequest: " + prompt)
        print("  Expected difficulty: " + expected_difficulty)
        print("  Actual difficulty: {:.3f}".format(decision.difficulty))
        print("  Assigned bin: {}".format(decision.bin_id))
        print("  Capability: {:.0%}, Risk: {:.0%}".format(decision.capability, decision.risk))
        print("  Zone: " + decision.zone)
        print("  Routed to: " + model.upper())
        print("  Expected success rate: {:.0%}".format(decision.expected_success_rate))

    # ========== PHASE 2: Monitoring ==========
    print("\n\nPHASE 2: Monitoring (Daily)")
    print("-" * 80)

    alerts = router.daily_monitoring_check()

    if alerts:
        print("[ALERT] ALERTS DETECTED:")
        for alert in alerts:
            print("  - " + alert)
    else:
        print("[OK] No degradation detected - all systems nominal")

    # ========== Summary ==========
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    summary = router.get_routing_summary()
    print("Total requests routed: {}".format(summary['total_requests']))
    print("By model: {}".format(summary['by_model']))
    print("By zone: {}".format(summary['by_zone']))
    print("Average difficulty: {:.2f}".format(summary['average_difficulty']))
    print("Average expected success: {:.0%}".format(summary['average_expected_success']))


if __name__ == "__main__":
    main()
