"""
Threshold Sensitivity Analysis for Tier Assignment
Inspired by SelectiveNet's risk-coverage tradeoff analysis

Sweeps different ρ̄ thresholds to find optimal tier boundaries based on:
1. Coverage: % of queries handled by each tier
2. Accuracy: Performance on each tier
3. Marginal benefit: Accuracy gain vs coverage loss

Reference: SelectiveNet paper - confidence-coverage tradeoff
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def analyze_threshold_sensitivity(
    test_results: dict[str, Any],
    threshold_range: tuple[float, float] = (0.2, 0.9),
    step: float = 0.05,
) -> dict[str, Any]:
    """
    Analyze tier assignment sensitivity to different ρ̄ thresholds.

    Sweeps thresholds to find optimal tier boundaries based on:
    - Coverage: % of queries assigned to each tier
    - Accuracy: Performance within each tier
    - Marginal performance: Accuracy gain vs coverage tradeoff

    Args:
        test_results: Output from test_with_frozen.py with per-task metrics
        threshold_range: (min_threshold, max_threshold) to sweep
        step: Threshold increment for sweep

    Returns:
        Dict with analysis results:
            {
                'sweep_results': [{
                    'slm_threshold': float,
                    'llm_threshold': float,
                    'tier_distribution': {...},
                    'avg_accuracy': float,
                    'coverage_metrics': {...},
                }],
                'optimal_thresholds': {
                    'slm_threshold': float,
                    'llm_threshold': float,
                    'reason': str,
                }
            }
    """
    task_results = test_results.get("results", {})
    min_thresh, max_thresh = threshold_range

    # Collect per-task rho_bar values
    task_rho_bars = {}
    task_accuracies = {}

    for task_family, result in task_results.items():
        if "error" in result:
            continue
        rho_bar = result.get("consensus_rho", 0.5)
        task_rho_bars[task_family] = rho_bar

        # Average accuracy across tiers
        metrics = result.get("aggregate_metrics", {})
        slm_acc = metrics.get("slm_accuracy", 0.0)
        llm_acc = metrics.get("llm_accuracy", 0.0)
        avg_acc = (slm_acc + llm_acc) / 2
        task_accuracies[task_family] = avg_acc

    # Sweep thresholds
    thresholds = np.arange(min_thresh, max_thresh + step, step)
    sweep_results = []

    for slm_threshold in thresholds:
        for llm_threshold in thresholds:
            # Skip invalid configurations
            if llm_threshold >= slm_threshold:
                continue

            # Assign tiers with these thresholds
            tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
            tier_accuracies = {"SLM": [], "HYBRID": [], "LLM": []}
            tier_coverage = {"SLM": 0, "HYBRID": 0, "LLM": 0}

            for task_family, rho_bar in task_rho_bars.items():
                # Assign tier with current thresholds
                if rho_bar >= slm_threshold:
                    tier = "SLM"
                elif rho_bar <= llm_threshold:
                    tier = "LLM"
                else:
                    tier = "HYBRID"

                tier_counts[tier] += 1
                tier_coverage[tier] += 1
                tier_accuracies[tier].append(task_accuracies[task_family])

            # Compute metrics
            total_tasks = len(task_rho_bars)
            coverage_pct = {
                t: tier_coverage[t] / total_tasks if total_tasks > 0 else 0.0
                for t in ["SLM", "HYBRID", "LLM"]
            }

            avg_accuracies = {
                t: (
                    np.mean(tier_accuracies[t])
                    if tier_accuracies[t]
                    else 0.0
                )
                for t in ["SLM", "HYBRID", "LLM"]
            }

            overall_accuracy = (
                sum(avg_accuracies[t] * coverage_pct[t] for t in ["SLM", "HYBRID", "LLM"])
                if total_tasks > 0
                else 0.0
            )

            sweep_results.append(
                {
                    "slm_threshold": float(slm_threshold),
                    "llm_threshold": float(llm_threshold),
                    "tier_distribution": tier_counts,
                    "coverage_pct": coverage_pct,
                    "avg_accuracy_per_tier": avg_accuracies,
                    "overall_weighted_accuracy": overall_accuracy,
                    "slm_coverage": coverage_pct["SLM"],
                    "hybrid_coverage": coverage_pct["HYBRID"],
                    "llm_coverage": coverage_pct["LLM"],
                }
            )

    # Find optimal thresholds (maximize overall accuracy)
    best = max(sweep_results, key=lambda x: x["overall_weighted_accuracy"])

    return {
        "summary": {
            "total_sweep_points": len(sweep_results),
            "threshold_range": threshold_range,
            "step": step,
        },
        "optimal_thresholds": {
            "slm_threshold": best["slm_threshold"],
            "llm_threshold": best["llm_threshold"],
            "overall_accuracy": best["overall_weighted_accuracy"],
            "tier_distribution": best["tier_distribution"],
            "coverage_pct": best["coverage_pct"],
            "reason": "Maximizes overall weighted accuracy across all tiers",
        },
        "current_thresholds": {
            "slm_threshold": 0.70,
            "llm_threshold": 0.30,
            "note": "Original frozen threshold values",
        },
        "sweep_results": sweep_results,
    }


def print_threshold_sensitivity_report(analysis: dict[str, Any]) -> None:
    """Print human-readable threshold sensitivity report."""
    print("\n" + "=" * 100)
    print("THRESHOLD SENSITIVITY ANALYSIS (SelectiveNet Inspired)")
    print("=" * 100)

    print(f"\nSweep Configuration:")
    summary = analysis.get("summary", {})
    print(f"  Total sweep points: {summary.get('total_sweep_points', 0)}")
    print(f"  Threshold range: {summary.get('threshold_range', (0, 1))}")
    print(f"  Step size: {summary.get('step', 0.05)}")

    print(f"\nCurrent Thresholds (Paper Table 6.3):")
    current = analysis.get("current_thresholds", {})
    print(f"  SLM threshold (rho_bar >= X): {current.get('slm_threshold', 0.70):.4f}")
    print(f"  LLM threshold (rho_bar <= X): {current.get('llm_threshold', 0.30):.4f}")
    print(f"  Tier assignment: SLM | HYBRID | LLM")

    print(f"\nOptimal Thresholds (Risk-Coverage Tradeoff):")
    optimal = analysis.get("optimal_thresholds", {})
    print(f"  SLM threshold (rho_bar >= X): {optimal.get('slm_threshold', 0.70):.4f}")
    print(f"  LLM threshold (rho_bar <= X): {optimal.get('llm_threshold', 0.30):.4f}")
    print(f"  Overall weighted accuracy: {optimal.get('overall_accuracy', 0):.4f}")
    print(f"  Reason: {optimal.get('reason', 'N/A')}")

    print(f"\nOptimal Tier Distribution:")
    dist = optimal.get("tier_distribution", {})
    coverage = optimal.get("coverage_pct", {})
    print(f"  SLM tier:   {dist.get('SLM', 0):2d} tasks ({coverage.get('SLM', 0):.1%})")
    print(f"  HYBRID tier: {dist.get('HYBRID', 0):2d} tasks ({coverage.get('HYBRID', 0):.1%})")
    print(f"  LLM tier:   {dist.get('LLM', 0):2d} tasks ({coverage.get('LLM', 0):.1%})")

    print(f"\nComparison: Current vs Optimal")
    current_dist = current.get("tier_distribution", {}) if "tier_distribution" in current else "N/A"
    print(f"  Current SLM threshold: {current.get('slm_threshold', 0.70):.4f}")
    print(f"  Optimal SLM threshold: {optimal.get('slm_threshold', 0.70):.4f}")
    print(f"  Difference: {optimal.get('slm_threshold', 0.70) - current.get('slm_threshold', 0.70):+.4f}")

    print(f"\n  Current LLM threshold: {current.get('llm_threshold', 0.30):.4f}")
    print(f"  Optimal LLM threshold: {optimal.get('llm_threshold', 0.30):.4f}")
    print(f"  Difference: {optimal.get('llm_threshold', 0.30) - current.get('llm_threshold', 0.30):+.4f}")

    print("\n" + "=" * 100)


def save_sensitivity_analysis(analysis: dict[str, Any], output_path: Path | str) -> None:
    """Save sensitivity analysis to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"Sensitivity analysis saved to {output_path}")


def plot_threshold_sensitivity(analysis: dict[str, Any], output_path: Path | str | None = None) -> None:
    """
    Plot risk-coverage tradeoff curves.

    Creates a visualization showing how accuracy and coverage change with thresholds.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping plot generation")
        return

    sweep_results = analysis.get("sweep_results", [])
    if not sweep_results:
        return

    # Extract metrics
    slm_thresholds = [r["slm_threshold"] for r in sweep_results]
    overall_accuracies = [r["overall_weighted_accuracy"] for r in sweep_results]
    slm_coverage = [r["slm_coverage"] for r in sweep_results]
    hybrid_coverage = [r["hybrid_coverage"] for r in sweep_results]
    llm_coverage = [r["llm_coverage"] for r in sweep_results]

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Overall accuracy vs SLM threshold
    ax = axes[0, 0]
    ax.plot(slm_thresholds, overall_accuracies, "b-", linewidth=2, label="Overall Accuracy")
    ax.axvline(x=0.70, color="r", linestyle="--", label="Current (0.70)")
    ax.set_xlabel("SLM Threshold (rho_bar >= X)")
    ax.set_ylabel("Overall Weighted Accuracy")
    ax.set_title("Risk-Accuracy Tradeoff")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Coverage distribution
    ax = axes[0, 1]
    ax.plot(slm_thresholds, slm_coverage, "g-", label="SLM Coverage")
    ax.plot(slm_thresholds, hybrid_coverage, "orange", label="HYBRID Coverage")
    ax.plot(slm_thresholds, llm_coverage, "r-", label="LLM Coverage")
    ax.axvline(x=0.70, color="k", linestyle="--", alpha=0.5, label="Current (0.70)")
    ax.set_xlabel("SLM Threshold (rho_bar >= X)")
    ax.set_ylabel("Coverage Fraction")
    ax.set_title("Tier Coverage Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Accuracy-Coverage Frontier
    ax = axes[1, 0]
    ax.scatter(slm_coverage, overall_accuracies, c=slm_thresholds, cmap="viridis", s=50)
    ax.set_xlabel("SLM Coverage")
    ax.set_ylabel("Overall Accuracy")
    ax.set_title("Accuracy-Coverage Frontier")
    cbar = plt.colorbar(ax.collections[0], ax=ax)
    cbar.set_label("SLM Threshold")
    ax.grid(True, alpha=0.3)

    # Plot 4: Marginal benefit analysis
    ax = axes[1, 1]
    if len(slm_thresholds) > 1:
        marginal_accuracy = np.diff(overall_accuracies)
        marginal_threshold = np.array(slm_thresholds[:-1])
        ax.bar(marginal_threshold, marginal_accuracy, width=0.03, alpha=0.7)
        ax.axvline(x=0.70, color="r", linestyle="--", label="Current (0.70)")
        ax.set_xlabel("SLM Threshold (rho_bar >= X)")
        ax.set_ylabel("Marginal Accuracy Gain")
        ax.set_title("Marginal Benefit of Threshold Change")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Sensitivity plot saved to {output_path}")
    else:
        plt.show()


if __name__ == "__main__":
    # Example usage (requires test_with_frozen results)
    import sys
    from pathlib import Path

    test_results_path = Path("model_runs/test_with_frozen_thresholds/test_with_frozen.json")
    if not test_results_path.exists():
        print(f"Test results not found: {test_results_path}")
        sys.exit(1)

    with open(test_results_path) as f:
        test_results = json.load(f)

    analysis = analyze_threshold_sensitivity(test_results)
    print_threshold_sensitivity_report(analysis)
    save_sensitivity_analysis(analysis, "model_runs/test_with_frozen_thresholds/threshold_sensitivity.json")
    plot_threshold_sensitivity(analysis, "model_runs/test_with_frozen_thresholds/threshold_sensitivity.png")
