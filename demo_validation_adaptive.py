#!/usr/bin/env python3
"""
Demo: SDDF Validation with Adaptive Percentile-Based Targets

Shows the difference between:
1. OLD: Fixed cap_static=0.65, risk_static=0.30 for all tasks
2. NEW: Adaptive targets derived from capability and risk percentiles
"""

import json
from sddf.validation_dynamic import run_validation


def demo_adaptive_validation():
    """
    Simulate validation for two tasks with different characteristics.
    """

    # Example 1: CODE_GENERATION (high capability, low risk)
    code_gen_samples = []
    code_gen_scores = {}

    for i in range(100):
        sample_id = f"cg_{i}"
        # Most samples succeed (high baseline capability)
        correct = (i % 7 != 0)  # ~86% success
        code_gen_samples.append({
            "sample_id": sample_id,
            "slm_correct": correct,
            "llm_correct": True,
            "failure_category": "logic_error" if not correct else None,
        })
        # Difficulty increases with index
        code_gen_scores[sample_id] = i / 100.0

    # Example 2: MATHS (low capability, high risk)
    maths_samples = []
    maths_scores = {}

    for i in range(100):
        sample_id = f"math_{i}"
        # Most samples fail (low baseline capability)
        correct = (i % 6 == 0)  # ~17% success
        maths_samples.append({
            "sample_id": sample_id,
            "slm_correct": correct,
            "llm_correct": True,
            "failure_category": "arithmetic_error" if not correct else None,
        })
        maths_scores[sample_id] = i / 100.0

    print("\n" + "=" * 80)
    print("ADAPTIVE PERCENTILE-BASED VALIDATION DEMO")
    print("=" * 80)

    # ===== CODE_GENERATION with ADAPTIVE targets =====
    print("\n1. CODE_GENERATION (Adaptive Percentile Targets)")
    print("-" * 80)

    result_adaptive = run_validation(
        code_gen_samples,
        code_gen_scores,
        task="code_generation",
        use_adaptive=True,
        cap_percentile=50.0,  # Median capability
        risk_percentile=75.0,  # 75th percentile risk
    )

    print(f"Baseline Capability: {result_adaptive['baseline_capability']:.4f}")
    print(f"Baseline Risk: {result_adaptive['baseline_risk']:.4f}")
    print(f"\nAdaptive Targets:")
    print(f"  cap_target (50th percentile): {result_adaptive['cap_target']:.4f}")
    print(f"  risk_target (75th percentile): {result_adaptive['risk_target']:.4f}")
    print(f"\nSelected TAU: {result_adaptive['selected_tau_score']:.4f}")
    print(f"  Expected Capability: {result_adaptive['selected_capability']:.4f}")
    print(f"  Expected Risk: {result_adaptive['selected_risk']:.4f}")
    print(f"  Feasible Zone Size: {result_adaptive['feasible_tau_count']}")
    print(f"  Source: {result_adaptive['tau_source']}")

    # ===== CODE_GENERATION with FIXED targets (old approach) =====
    print("\n2. CODE_GENERATION (Fixed Targets - Old Approach)")
    print("-" * 80)

    result_fixed = run_validation(
        code_gen_samples,
        code_gen_scores,
        task="code_generation",
        use_adaptive=False,
        cap_static=0.65,
        risk_static=0.30,
    )

    print(f"Fixed Targets:")
    print(f"  cap_static: {result_fixed['cap_static']:.4f}")
    print(f"  risk_static: {result_fixed['risk_static']:.4f}")
    print(f"  (Adjusted by baseline)")
    print(f"  cap_dynamic: {result_fixed['cap_dynamic']:.4f}")
    print(f"  risk_dynamic: {result_fixed['risk_dynamic']:.4f}")
    print(f"\nSelected TAU: {result_fixed['selected_tau_score']:.4f}")
    print(f"  Expected Capability: {result_fixed['selected_capability']:.4f}")
    print(f"  Expected Risk: {result_fixed['selected_risk']:.4f}")
    print(f"  Feasible Zone Size: {result_fixed['feasible_tau_count']}")
    print(f"  Source: {result_fixed['tau_source']}")

    # ===== MATHS with ADAPTIVE targets =====
    print("\n3. MATHS (Adaptive Percentile Targets)")
    print("-" * 80)

    result_maths_adaptive = run_validation(
        maths_samples,
        maths_scores,
        task="maths",
        use_adaptive=True,
        cap_percentile=50.0,
        risk_percentile=75.0,
    )

    print(f"Baseline Capability: {result_maths_adaptive['baseline_capability']:.4f}")
    print(f"Baseline Risk: {result_maths_adaptive['baseline_risk']:.4f}")
    print(f"\nAdaptive Targets:")
    print(f"  cap_target (50th percentile): {result_maths_adaptive['cap_target']:.4f}")
    print(f"  risk_target (75th percentile): {result_maths_adaptive['risk_target']:.4f}")
    print(f"\nSelected TAU: {result_maths_adaptive['selected_tau_score']:.4f}")
    print(f"  Expected Capability: {result_maths_adaptive['selected_capability']:.4f}")
    print(f"  Expected Risk: {result_maths_adaptive['selected_risk']:.4f}")
    print(f"  Feasible Zone Size: {result_maths_adaptive['feasible_tau_count']}")
    print(f"  Source: {result_maths_adaptive['tau_source']}")

    # ===== COMPARISON: Different Percentile Levels =====
    print("\n4. SENSITIVITY: Different Percentile Levels (CODE_GENERATION)")
    print("-" * 80)

    for cap_p in [40, 50, 60]:
        for risk_p in [50, 75, 90]:
            result = run_validation(
                code_gen_samples,
                code_gen_scores,
                task="code_generation",
                use_adaptive=True,
                cap_percentile=cap_p,
                risk_percentile=risk_p,
            )
            print(
                f"P={cap_p:2d}, Q={risk_p:2d}: "
                f"cap_target={result['cap_target']:.3f}, "
                f"risk_target={result['risk_target']:.3f}, "
                f"tau={result['selected_tau_score']:.3f}, "
                f"zone_size={result['feasible_tau_count']:2d}"
            )

    print("\n" + "=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print("✓ Adaptive targets adjust per model/task (no fixed 0.65/0.30)")
    print("✓ High-capability models get high targets automatically")
    print("✓ Low-capability models get low targets automatically")
    print("✓ Percentile levels control conservatism (P, Q)")
    print("✓ Everything stays probability-based and generalizable")


if __name__ == "__main__":
    demo_adaptive_validation()
