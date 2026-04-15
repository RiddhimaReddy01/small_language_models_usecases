#!/usr/bin/env python3
"""
Demonstration of SDDF Validation Phase with Synthetic Data.

Shows all steps of:
1. Per-sample metrics computation
2. Difficulty curve building
3. Dynamic threshold calculation
4. Feasible set discovery
5. Strict TAU selection with fallback

Run: python demo_validation.py
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.validation_dynamic import (
    compute_per_sample_metrics,
    build_difficulty_curves,
    find_operational_zone,
)


def create_synthetic_validation_data(n_samples: int = 53) -> tuple[list[dict], dict[str, float]]:
    """
    Create realistic synthetic validation samples.

    Pattern: harder samples (higher score) = higher SLM failure rate
    """
    import random

    random.seed(42)
    samples = []
    scores = {}

    for i in range(n_samples):
        sample_id = f"val_{i:04d}"

        # Score roughly uniformly distributed [0, 1]
        score = random.random()

        # Higher score = higher SLM failure probability
        slm_fails_prob = score ** 1.5  # Convex: harder samples are even harder
        baseline_fails_prob = 0.15  # Strong baseline (15% failure rate)

        slm_correct = random.random() > slm_fails_prob
        llm_correct = random.random() > baseline_fails_prob

        sample = {
            "sample_id": sample_id,
            "slm_correct": slm_correct,
            "llm_correct": llm_correct,
        }
        samples.append(sample)
        scores[sample_id] = score

    return samples, scores


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)


def main() -> None:
    print("\n" + "*" * 80)
    print("*  SDDF VALIDATION PHASE DEMONSTRATION")
    print("*" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Create synthetic data
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 1: Generate Synthetic Validation Data")

    samples, scores = create_synthetic_validation_data(n_samples=53)
    print(f"\nGenerated {len(samples)} validation samples")
    print(f"Score range: [{min(scores.values()):.3f}, {max(scores.values()):.3f}]")

    # Show first 5 samples
    print("\nFirst 5 samples:")
    print("  ID        | Score | SLM OK? | LLM OK? |")
    print("  " + "-" * 40)
    for i in range(5):
        s = samples[i]
        score = scores[s["sample_id"]]
        print(f"  {s['sample_id']} | {score:.3f} | {'OK' if s['slm_correct'] else 'FAIL':<7} | {'OK' if s['llm_correct'] else 'FAIL':<7} |")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Compute per-sample metrics
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 2: Compute Per-Sample Metrics")

    metrics, baseline_cap, baseline_risk = compute_per_sample_metrics(
        samples,
        scores,
        task="maths"  # Use math task risk model
    )

    print(f"\nBaseline capability (always use LLM): {baseline_cap:.1%}")
    print(f"Baseline risk (LLM failure severity):  {baseline_risk:.3f}")

    print(f"\nMetrics computed for {len(metrics)} samples:")
    print("  Sample    | Score | SLM OK? | LLM OK? | Capability | Risk    |")
    print("  " + "-" * 68)
    for i in range(5):
        m = metrics[i]
        print(f"  {m['sample_id']} | {m['score']:.3f} | {'OK' if m['slm_correct'] else 'FAIL':<7} | "
              f"{'OK' if m['llm_correct'] else 'FAIL':<7} | {m['capability']:>10.1f} | {m['risk']:>7.4f} |")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Build difficulty curves
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 3: Build Difficulty Curves (Isotonic Regression)")

    cap_curve, risk_curve, coverage = build_difficulty_curves(metrics, n_bins=5)

    print("\nDifficulty bins (isotonic-fitted curves):")
    print("  Bin | Cap^(d) | Risk^(d) | Coverage |")
    print("  " + "-" * 45)

    difficulties = sorted(cap_curve.keys())
    for d in difficulties:
        cap = cap_curve[d]
        risk = risk_curve[d]
        cov = coverage[d]
        print(f"   {d}  |  {cap:.3f}  |  {risk:.3f}  |  {cov:>4}   |")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Determine dynamic thresholds
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 4: Compute Dynamic Thresholds")

    cap_static = 0.65
    risk_static = 0.35

    print(f"\nStatic thresholds (business requirement):")
    print(f"  Capability: >= {cap_static:.0%}")
    print(f"  Risk:       <= {risk_static:.0%}")

    print(f"\nBaseline achieved:")
    print(f"  Capability: {baseline_cap:.1%}")
    print(f"  Risk:       {baseline_risk:.3f}")

    # Dynamic capability threshold
    mcap = 0.05
    cap_dyn_raw = min(cap_static, baseline_cap - mcap)
    cap_dyn = max(0.40, min(cap_dyn_raw, 1.00))

    print(f"\nDynamic Capability Threshold:")
    print(f"  cap_dyn = clamp(min({cap_static}, {baseline_cap} - {mcap}), 0.40, 1.00)")
    print(f"          = clamp(min({cap_static}, {baseline_cap - mcap}), 0.40, 1.00)")
    print(f"          = clamp({cap_dyn_raw:.2f}, 0.40, 1.00)")
    print(f"          = {cap_dyn:.2f}")

    # Dynamic risk threshold
    mrisk = 0.05
    risk_dyn_raw = max(risk_static, baseline_risk + mrisk)
    risk_dyn = max(0.00, min(risk_dyn_raw, 1.00))

    print(f"\nDynamic Risk Threshold:")
    print(f"  risk_dyn = clamp(max({risk_static}, {baseline_risk:.3f} + {mrisk}), 0.00, 1.00)")
    print(f"           = clamp(max({risk_static}, {baseline_risk + mrisk:.3f}), 0.00, 1.00)")
    print(f"           = clamp({risk_dyn_raw:.2f}, 0.00, 1.00)")
    print(f"           = {risk_dyn:.2f}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Find feasible set
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 5: Find Feasible Set")

    coverage_max = 0.70
    feasible = []
    violations = {}

    print(f"\nConstraints to satisfy:")
    print(f"  1. Capability >= {cap_dyn:.2f}")
    print(f"  2. Risk <= {risk_dyn:.2f}")
    print(f"  3. Coverage <= {coverage_max:.0%}")

    print(f"\nChecking each difficulty level:")
    print("  D | Cap^(d) | Risk^(d) | Cov | Cap-OK | Risk-OK | Cov-OK | FEASIBLE?")
    print("  " + "-" * 60)

    total_coverage = sum(coverage.values())
    for d in difficulties:
        cap_d = cap_curve[d]
        risk_d = risk_curve[d]
        cov_d = coverage[d] / total_coverage

        cap_ok = cap_d >= cap_dyn
        risk_ok = risk_d <= risk_dyn
        cov_ok = cov_d <= coverage_max
        is_feasible = cap_ok and risk_ok and cov_ok

        if is_feasible:
            feasible.append(d)

        # Violation score
        cap_viol = max(0.0, cap_dyn - cap_d)
        risk_viol = max(0.0, risk_d - risk_dyn)
        violations[d] = cap_viol + risk_viol

        status = "YES" if is_feasible else "NO"
        print(f"  {d} | {cap_d:.3f}  | {risk_d:.3f}  | {cov_d:.0%} | "
              f"{'Y' if cap_ok else 'N':<4} | {'Y' if risk_ok else 'N':<5} | "
              f"{'Y' if cov_ok else 'N':<4} | {status}")

    print(f"\nFeasible set F: {feasible}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6: Pick TAU
    # ─────────────────────────────────────────────────────────────────────────

    print_section("STEP 6: Select TAU Threshold")

    if feasible:
        strict_tau = max(feasible)
        print(f"\nFeasible set is NOT EMPTY")
        print(f"  Strict TAU = max(F) = max({feasible}) = {strict_tau}")
        print(f"\n  Achieved at τ*:")
        print(f"    Capability: {cap_curve[strict_tau]:.1%} (meets >={cap_dyn:.0%})")
        print(f"    Risk:       {risk_curve[strict_tau]:.3f} (meets <={risk_dyn:.2f})")
        print(f"    Coverage:   {coverage[strict_tau] / total_coverage:.0%} (< {coverage_max:.0%})")
        tau_selected = strict_tau
    else:
        print(f"\nFeasible set is EMPTY - using fallback")
        # Tie-break: lower risk, then higher coverage, then higher difficulty
        fallback_tau = min(violations.keys(),
                          key=lambda d: (violations[d], risk_curve[d], -coverage[d], -d))
        print(f"  Violations: {violations}")
        print(f"  Fallback TAU = arg_min(V(d)) = {fallback_tau}")
        print(f"\n  Trade-offs at tau_fb:")
        print(f"    Capability: {cap_curve[fallback_tau]:.1%} (needs >={cap_dyn:.0%}) - "
              f"short by {cap_dyn - cap_curve[fallback_tau]:.1%}")
        print(f"    Risk:       {risk_curve[fallback_tau]:.3f} (needs <={risk_dyn:.2f}) - "
              f"over by {max(0, risk_curve[fallback_tau] - risk_dyn):.3f}")
        tau_selected = fallback_tau

    # Final Summary
    print_section("VALIDATION RESULTS")

    result = {
        "task": "maths",
        "model": "qwen2.5_0.5b",
        "n_val_samples": len(samples),
        "baseline_capability": baseline_cap,
        "baseline_risk": baseline_risk,
        "cap_static": cap_static,
        "risk_static": risk_static,
        "cap_dynamic": cap_dyn,
        "risk_dynamic": risk_dyn,
        "feasible_set": feasible,
        "strict_tau": max(feasible) if feasible else None,
        "fallback_tau": (max(feasible) if feasible else
                        min(violations.keys(),
                           key=lambda d: (violations[d], risk_curve[d], -coverage[d], -d))),
        "violations_at_tau": violations,
    }

    print(json.dumps(result, indent=2))

    print("\n" + "=" * 80)
    print("INTERPRETATION FOR PRODUCTION")
    print("=" * 80)
    print(f"\nUsing tau* = {tau_selected}:")
    print(f"\n  Routing Policy:")
    print(f"    if score <= {tau_selected} -> USE SLM (cheap, safe)")
    print(f"    if score > {tau_selected} -> USE BASELINE (expensive, reliable)")
    print(f"\n  Operational Zone:")
    print(f"    Easy queries (score <= {tau_selected}):")
    print(f"      - {cap_curve[tau_selected]:.1%} of SLM failures caught")
    print(f"      - {risk_curve[tau_selected]:.1%} risk of incorrect answers")
    print(f"\n    Hard queries (score > {tau_selected}):")
    print(f"      - Route to baseline for safety")
    print(f"      - Accept baseline's {baseline_cap:.1%} error rate")
    print(f"\n  Coverage:")
    print(f"    - {coverage[tau_selected] / total_coverage:.0%} of queries use SLM (fast + cheap)")
    print(f"    - {1 - coverage[tau_selected] / total_coverage:.0%} of queries use baseline (safe)")

    print("\n" + "*" * 80)
    print("*  DEMONSTRATION COMPLETE")
    print("*" * 80 + "\n")


if __name__ == "__main__":
    main()
