#!/usr/bin/env python3
"""
Demonstration of Dynamic Operational Zones with Three Strategies.

Shows:
1. Operational zone for each task family
2. Conservative, Balanced, Aggressive options
3. What each strategy achieves (capability, risk, coverage)
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.validation_dynamic import select_tau_strategy, get_strategy_rationale


def demo_task(task_name: str, model_name: str, feasible_set: list,
              cap_curve: dict, risk_curve: dict, coverage: dict) -> None:
    """Demonstrate operational zone for a task-model pair."""

    print("\n" + "="*90)
    print(f"{task_name.upper()} / {model_name}")
    print("="*90)

    if not feasible_set:
        print("\nOPERATIONAL ZONE: EMPTY (no safe routing region)")
        print("\nRecommendation: Always use baseline/LLM")
        print("Reason: Cannot meet both capability and risk thresholds simultaneously")
        return

    # Get strategy info
    strategy_info = select_tau_strategy(feasible_set)
    rationale = get_strategy_rationale(strategy_info["zone_size"])

    # Print zone info
    print(f"\nOPERATIONAL ZONE: [{strategy_info['zone_min']:.1f}, {strategy_info['zone_max']:.1f}]")
    print(f"Zone Size: {strategy_info['zone_size']:.1f}")
    print(f"Recommended Strategy: {strategy_info['strategy'].upper()}")
    print(f"\nRationale: {rationale}")

    # Print three options
    print("\n" + "-"*90)
    print("THREE ROUTING OPTIONS:")
    print("-"*90)

    options = [
        ("CONSERVATIVE", strategy_info["tau_conservative"]),
        ("BALANCED", strategy_info["tau_balanced"]),
        ("AGGRESSIVE", strategy_info["tau_aggressive"]),
    ]

    for strategy_name, tau in options:
        if tau is None:
            continue

        # Find closest difficulty level in curves
        diffs = sorted(cap_curve.keys())
        closest_d = min(diffs, key=lambda d: abs(d - tau))

        cap = cap_curve.get(closest_d, 0.5)
        risk = risk_curve.get(closest_d, 0.5)
        cov = coverage.get(closest_d, 0) / sum(coverage.values()) if coverage else 0

        recommended = " <- RECOMMENDED" if strategy_name == strategy_info["strategy"].upper() else ""

        print(f"\n{strategy_name}{recommended}")
        print(f"  TAU: {tau:.2f}")
        print(f"  Capability: {cap*100:.1f}% (SLM succeeds this often)")
        print(f"  Risk: {risk:.3f} (expected loss per routed query)")
        print(f"  Coverage: {cov*100:.1f}% (% of queries routed to SLM)")


def main():
    print("\n" + "*"*90)
    print("DYNAMIC OPERATIONAL ZONES: DEMONSTRATION")
    print("*"*90)

    # Example 1: EASY Task (SUMMARIZATION)
    demo_task(
        task_name="SUMMARIZATION",
        model_name="qwen2.5_0.5b",
        feasible_set=[0, 1, 2, 3, 4],  # Wide zone
        cap_curve={0: 0.96, 1: 0.92, 2: 0.85, 3: 0.75, 4: 0.65},
        risk_curve={0: 0.01, 1: 0.02, 2: 0.04, 3: 0.06, 4: 0.08},
        coverage={0: 10, 1: 15, 2: 20, 3: 25, 4: 30},
    )

    # Example 2: MEDIUM Task (CODE_GENERATION)
    demo_task(
        task_name="CODE_GENERATION",
        model_name="qwen2.5_0.5b",
        feasible_set=[0, 1, 2],  # Medium zone
        cap_curve={0: 0.88, 1: 0.73, 2: 0.61, 3: 0.48, 4: 0.35},
        risk_curve={0: 0.10, 1: 0.15, 2: 0.20, 3: 0.28, 4: 0.35},
        coverage={0: 8, 1: 12, 2: 15, 3: 18, 4: 20},
    )

    # Example 3: HARD Task (RETRIEVAL_GROUNDED)
    demo_task(
        task_name="RETRIEVAL_GROUNDED",
        model_name="qwen2.5_3b",
        feasible_set=[0, 1],  # Narrow zone
        cap_curve={0: 0.92, 1: 0.78, 2: 0.65, 3: 0.55, 4: 0.42},
        risk_curve={0: 0.05, 1: 0.10, 2: 0.15, 3: 0.20, 4: 0.25},
        coverage={0: 5, 1: 10, 2: 15, 3: 20, 4: 25},
    )

    # Example 4: IMPOSSIBLE Task (CLASSIFICATION)
    demo_task(
        task_name="CLASSIFICATION",
        model_name="qwen2.5_0.5b",
        feasible_set=[],  # Empty zone
        cap_curve={},
        risk_curve={},
        coverage={},
    )

    # Summary table
    print("\n\n" + "="*90)
    print("SUMMARY TABLE: OPERATIONAL ZONES BY TASK")
    print("="*90)
    print("\n{:<20} | {:<10} | {:<15} | {:<20} | {:<15}".format(
        "Task", "Zone Size", "Strategy", "Recommended TAU", "Flexibility"))
    print("-"*90)

    examples = [
        ("SUMMARIZATION", 4.0, "aggressive", 4.0, "WIDE - aggressive routing"),
        ("CODE_GENERATION", 2.0, "balanced", 1.0, "MEDIUM - balanced routing"),
        ("RETRIEVAL_GROUNDED", 1.0, "conservative", 0.0, "NARROW - conservative routing"),
        ("CLASSIFICATION", 0.0, "none", "None", "EMPTY - no routing"),
    ]

    for task, zone_size, strategy, tau, flexibility in examples:
        tau_str = f"{tau:.1f}" if isinstance(tau, float) else str(tau)
        print("{:<20} | {:<10.1f} | {:<15} | {:<20} | {:<15}".format(
            task, zone_size, strategy, tau_str, flexibility))

    print("\n" + "="*90)
    print("KEY INSIGHT")
    print("="*90)
    print("""
Zone Size tells you how flexible routing is for that task:

  Zone Size = 4.0:  EASY task, many routing options, aggressive strategy
  Zone Size = 2.0:  MEDIUM task, moderate options, balanced strategy (RECOMMENDED)
  Zone Size = 1.0:  HARD task, few options, conservative strategy
  Zone Size = 0.0:  IMPOSSIBLE, no routing possible

For MEDIUM tasks (Zone Size = 2.0):

  Choose BALANCED strategy:
    - TAU = (0 + 2) / 2 = 1.0
    - Routes medium difficulty queries
    - Balances cost savings with quality
    - This is the RECOMMENDED approach for most tasks
""")

    print("\n" + "*"*90)
    print("DEMONSTRATION COMPLETE")
    print("*"*90 + "\n")


if __name__ == "__main__":
    main()
