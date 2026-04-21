#!/usr/bin/env python3
"""
UC Tier Threshold Sensitivity Analysis - Version 2

Focus on 5 key metrics (no ground truth needed):
1. tier_diversity_score - How balanced are the tiers?
2. robustness_score - How stable are tier assignments?
3. mean_confidence - How certain are the assignments?
4. min_confidence - What's the riskiest UC?
5. gap - How much separation between tiers?
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Warning: matplotlib not available")
    plt = None


def load_uc_empirical_results() -> Dict:
    """Load UC empirical routing results."""
    results_path = Path("model_runs/uc_empirical_routing.json")
    with open(results_path) as f:
        return json.load(f)


def extract_rho_bars(uc_results: Dict) -> Dict[str, float]:
    """Extract ρ̄ values for each UC."""
    rho_bars = {}
    for uc in ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]:
        rho_bars[uc] = uc_results[uc]["rho_bar"]
    return rho_bars


def assign_uc_tiers(rho_bars: Dict[str, float], slm_threshold: float, llm_threshold: float) -> Dict:
    """Assign UCs to tiers using given thresholds."""
    assignments = {}
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}

    for uc, rho_bar in sorted(rho_bars.items()):
        if rho_bar >= slm_threshold:
            tier = "SLM"
        elif rho_bar <= llm_threshold:
            tier = "LLM"
        else:
            tier = "HYBRID"

        assignments[uc] = {"rho_bar": rho_bar, "tier": tier}
        tier_counts[tier] += 1

    return {
        "assignments": assignments,
        "tier_counts": tier_counts,
        "slm_coverage": tier_counts["SLM"] / 8,
        "llm_coverage": tier_counts["LLM"] / 8,
        "hybrid_count": tier_counts["HYBRID"],
    }


# ============================================================================
# METRIC 1: TIER DIVERSITY SCORE
# ============================================================================

def calculate_tier_diversity_score(tier_counts: Dict[str, int]) -> float:
    """
    Measure how balanced the tiers are.

    Perfect balance: 2.67 SLM, 2.67 HYBRID, 2.67 LLM
    Score: 0 (all in one tier) to 1.0 (perfectly balanced)
    """
    ideal_per_tier = 8 / 3  # 2.67 each

    counts = [tier_counts["SLM"], tier_counts["HYBRID"], tier_counts["LLM"]]
    variance = sum((c - ideal_per_tier) ** 2 for c in counts) / 3

    max_variance = ideal_per_tier ** 2  # Maximum possible variance
    diversity = max(0, 1.0 - (variance / max_variance))

    return float(diversity)


# ============================================================================
# METRIC 2: ROBUSTNESS SCORE
# ============================================================================

def calculate_robustness_score(
    rho_bars: Dict[str, float], slm_threshold: float, llm_threshold: float
) -> Tuple[float, Dict]:
    """
    Measure how stable tier assignments are.

    Robustness = average distance to nearest tier boundary
    High score = UCs far from boundaries (stable)
    Low score = UCs near boundaries (fragile)

    Returns: (robustness_score, detailed_margins)
    """
    margins = {}

    for uc, rho_bar in rho_bars.items():
        if rho_bar >= slm_threshold:
            # In SLM tier - distance to SLM boundary
            margin = rho_bar - slm_threshold
        elif rho_bar <= llm_threshold:
            # In LLM tier - distance to LLM boundary
            margin = llm_threshold - rho_bar
        else:
            # In HYBRID tier - distance to nearest boundary
            dist_to_slm = slm_threshold - rho_bar
            dist_to_llm = rho_bar - llm_threshold
            margin = min(dist_to_slm, dist_to_llm)

        margins[uc] = margin

    avg_margin = np.mean(list(margins.values()))
    # Normalize to 0-1 score (anything > 0.1 margin is excellent)
    robustness_score = min(1.0, avg_margin * 5)

    return float(robustness_score), margins


# ============================================================================
# METRIC 3: MEAN CONFIDENCE
# ============================================================================

def calculate_mean_confidence(
    rho_bars: Dict[str, float], slm_threshold: float, llm_threshold: float
) -> Tuple[float, Dict]:
    """
    Measure how confident the tier assignments are.

    Confidence = normalized distance to nearest boundary (0-100%)
    High confidence = UC far from boundary
    Low confidence = UC near boundary

    Returns: (mean_confidence, per_uc_confidence)
    """
    confidences = {}

    for uc, rho_bar in rho_bars.items():
        if rho_bar >= slm_threshold:
            # In SLM - how far above threshold?
            confidence = min(100, (rho_bar - slm_threshold) / (1.0 - slm_threshold) * 100)
        elif rho_bar <= llm_threshold:
            # In LLM - how far below threshold?
            confidence = min(100, (llm_threshold - rho_bar) / llm_threshold * 100)
        else:
            # In HYBRID - how centered?
            gap = slm_threshold - llm_threshold
            dist_to_boundary = min(rho_bar - llm_threshold, slm_threshold - rho_bar)
            confidence = (dist_to_boundary / gap * 100) if gap > 0 else 0

        confidences[uc] = confidence

    mean_confidence = float(np.mean(list(confidences.values())))
    return mean_confidence, confidences


# ============================================================================
# METRIC 4: MIN CONFIDENCE (Risk Indicator)
# ============================================================================

def calculate_min_confidence(confidences: Dict[str, float]) -> Tuple[float, str]:
    """
    Identify the riskiest UC (lowest confidence).

    Returns: (min_confidence_score, uc_name)
    """
    min_conf = min(confidences.values())
    riskiest_uc = min(confidences.keys(), key=lambda k: confidences[k])
    return float(min_conf), riskiest_uc


# ============================================================================
# METRIC 5: GAP (Tier Separation)
# ============================================================================

def calculate_gap(slm_threshold: float, llm_threshold: float) -> float:
    """
    Measure the HYBRID zone width.

    Gap = SLM_threshold - LLM_threshold
    Large gap = more room for nuance (0.40 is moderate)
    Small gap = clear tier separation (0.15 is tight)
    """
    return float(slm_threshold - llm_threshold)


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def analyze_uc_tier_sensitivity_v2(
    rho_bars: Dict[str, float],
    slm_range: Tuple[float, float] = (0.50, 0.85),
    llm_range: Tuple[float, float] = (0.10, 0.35),
    step: float = 0.05,
) -> List[Dict]:
    """
    Sweep through tier thresholds and compute 5 key metrics for each.
    """
    sweep_results = []

    slm_thresholds = np.arange(slm_range[0], slm_range[1] + step, step)
    llm_thresholds = np.arange(llm_range[0], llm_range[1] + step, step)

    for slm_thresh in slm_thresholds:
        for llm_thresh in llm_thresholds:
            if llm_thresh >= slm_thresh:
                continue

            # Assign tiers
            tier_result = assign_uc_tiers(rho_bars, slm_thresh, llm_thresh)

            # Calculate 5 metrics
            diversity = calculate_tier_diversity_score(tier_result["tier_counts"])
            robustness, margins = calculate_robustness_score(rho_bars, slm_thresh, llm_thresh)
            mean_conf, confidences = calculate_mean_confidence(rho_bars, slm_thresh, llm_thresh)
            min_conf, riskiest = calculate_min_confidence(confidences)
            gap = calculate_gap(slm_thresh, llm_thresh)

            result = {
                "slm_threshold": slm_thresh,
                "llm_threshold": llm_thresh,
                "tier_counts": tier_result["tier_counts"],
                "slm_coverage": tier_result["slm_coverage"],
                "llm_coverage": tier_result["llm_coverage"],
                "hybrid_count": tier_result["hybrid_count"],
                "gap": gap,
                # Key metrics
                "tier_diversity_score": diversity,
                "robustness_score": robustness,
                "mean_confidence": mean_conf,
                "min_confidence": min_conf,
                "riskiest_uc": riskiest,
                # Details
                "margins": margins,
                "confidences": confidences,
            }

            sweep_results.append(result)

    return sweep_results


def print_metrics_summary(sweep_results: List[Dict], rho_bars: Dict):
    """Print summary of metrics across sweep."""
    print("\n" + "=" * 100)
    print("UC TIER THRESHOLD SENSITIVITY ANALYSIS - 5 KEY METRICS")
    print("=" * 100)

    # Find optima for each metric
    best_diversity = max(sweep_results, key=lambda x: x["tier_diversity_score"])
    best_robustness = max(sweep_results, key=lambda x: x["robustness_score"])
    best_confidence = max(sweep_results, key=lambda x: x["mean_confidence"])
    lowest_risk = max(sweep_results, key=lambda x: x["min_confidence"])
    largest_gap = max(sweep_results, key=lambda x: x["gap"])

    # Paper baseline
    paper = next(
        (r for r in sweep_results if abs(r["slm_threshold"] - 0.70) < 0.01 and abs(r["llm_threshold"] - 0.30) < 0.01),
        None,
    )

    print("\nEmpirical rho_bar values:")
    for uc in sorted(rho_bars.keys()):
        print(f"  {uc}: {rho_bars[uc]:.4f}")

    print("\n" + "-" * 100)
    print("METRIC 1: TIER DIVERSITY SCORE (Balance)")
    print("-" * 100)
    print(f"Paper (0.70/0.30):")
    print(f"  Score: {paper['tier_diversity_score']:.3f}")
    print(f"  Tiers: SLM={paper['tier_counts']['SLM']}, HYBRID={paper['tier_counts']['HYBRID']}, LLM={paper['tier_counts']['LLM']}")
    print(f"\nBest Diversity ({best_diversity['slm_threshold']:.2f}/{best_diversity['llm_threshold']:.2f}):")
    print(f"  Score: {best_diversity['tier_diversity_score']:.3f}")
    print(f"  Tiers: SLM={best_diversity['tier_counts']['SLM']}, HYBRID={best_diversity['tier_counts']['HYBRID']}, LLM={best_diversity['tier_counts']['LLM']}")

    print("\n" + "-" * 100)
    print("METRIC 2: ROBUSTNESS SCORE (Stability)")
    print("-" * 100)
    print(f"Paper (0.70/0.30):")
    print(f"  Score: {paper['robustness_score']:.3f}")
    print(f"  Interpretation: Tier assignments change if thresholds move by ~{paper['robustness_score']/5:.2f}")
    print(f"\nBest Robustness ({best_robustness['slm_threshold']:.2f}/{best_robustness['llm_threshold']:.2f}):")
    print(f"  Score: {best_robustness['robustness_score']:.3f}")
    print(f"  Interpretation: Tier assignments change if thresholds move by ~{best_robustness['robustness_score']/5:.2f}")

    print("\n" + "-" * 100)
    print("METRIC 3: MEAN CONFIDENCE (Certainty)")
    print("-" * 100)
    print(f"Paper (0.70/0.30):")
    print(f"  Score: {paper['mean_confidence']:.1f}%")
    print(f"  Interpretation: UCs are on average {paper['mean_confidence']:.1f}% confident in their tier")
    print(f"\nBest Confidence ({best_confidence['slm_threshold']:.2f}/{best_confidence['llm_threshold']:.2f}):")
    print(f"  Score: {best_confidence['mean_confidence']:.1f}%")
    print(f"  Interpretation: UCs are on average {best_confidence['mean_confidence']:.1f}% confident in their tier")

    print("\n" + "-" * 100)
    print("METRIC 4: MIN CONFIDENCE (Risk Indicator)")
    print("-" * 100)
    print(f"Paper (0.70/0.30):")
    print(f"  Score: {paper['min_confidence']:.1f}%")
    print(f"  Riskiest UC: {paper['riskiest_uc']} (dangerously close to tier boundary!)")
    print(f"\nLowest Risk ({lowest_risk['slm_threshold']:.2f}/{lowest_risk['llm_threshold']:.2f}):")
    print(f"  Score: {lowest_risk['min_confidence']:.1f}%")
    print(f"  Riskiest UC: {lowest_risk['riskiest_uc']} (safer margin)")

    print("\n" + "-" * 100)
    print("METRIC 5: GAP (Tier Separation)")
    print("-" * 100)
    print(f"Paper (0.70/0.30):")
    print(f"  Gap: {paper['gap']:.2f} (moderate separation)")
    print(f"  Interpretation: HYBRID zone spans {paper['gap']:.2f} width")
    print(f"\nLargest Gap ({largest_gap['slm_threshold']:.2f}/{largest_gap['llm_threshold']:.2f}):")
    print(f"  Gap: {largest_gap['gap']:.2f} (maximum separation)")
    print(f"  Interpretation: HYBRID zone spans {largest_gap['gap']:.2f} width (more room for nuance)")


def print_detailed_comparison(sweep_results: List[Dict]):
    """Compare key configurations side-by-side."""
    print("\n" + "=" * 100)
    print("DETAILED CONFIGURATION COMPARISON")
    print("=" * 100)

    # Select interesting configs
    paper = next(
        (r for r in sweep_results if abs(r["slm_threshold"] - 0.70) < 0.01 and abs(r["llm_threshold"] - 0.30) < 0.01),
        None,
    )
    cost_opt = next((r for r in sweep_results if abs(r["slm_threshold"] - 0.50) < 0.01 and abs(r["llm_threshold"] - 0.10) < 0.01), None)
    clarity_opt = next((r for r in sweep_results if abs(r["slm_threshold"] - 0.50) < 0.01 and abs(r["llm_threshold"] - 0.35) < 0.01), None)

    configs = [
        ("Paper (0.70/0.30)", paper),
        ("Cost Opt (0.50/0.10)", cost_opt),
        ("Clarity Opt (0.50/0.35)", clarity_opt),
    ]

    print("\n{:<25} {:<12} {:<18} {:<18} {:<15} {:<12}".format(
        "Configuration", "Gap", "Diversity", "Robustness", "Confidence", "Min Conf"
    ))
    print("-" * 100)

    for name, config in configs:
        if config:
            print("{:<25} {:<12.2f} {:<18.3f} {:<18.3f} {:<15.1f}% {:<12.1f}%".format(
                name,
                config["gap"],
                config["tier_diversity_score"],
                config["robustness_score"],
                config["mean_confidence"],
                config["min_confidence"],
            ))

    print("\n" + "-" * 100)
    print("TIER DISTRIBUTION COMPARISON")
    print("-" * 100)
    print("\n{:<25} {:<15} {:<15} {:<15}".format("Configuration", "SLM", "HYBRID", "LLM"))
    print("-" * 100)

    for name, config in configs:
        if config:
            print("{:<25} {:<15} {:<15} {:<15}".format(
                name,
                f"{config['tier_counts']['SLM']} ({config['slm_coverage']*100:.0f}%)",
                f"{config['tier_counts']['HYBRID']}",
                f"{config['tier_counts']['LLM']} ({config['llm_coverage']*100:.0f}%)",
            ))


def plot_metrics(sweep_results: List[Dict], output_path: Path = Path("model_runs/uc_tier_metrics_v2.png")):
    """Visualize 5 key metrics across sweep."""
    if plt is None:
        print("Skipping visualization (matplotlib not available)")
        return

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("UC Tier Threshold Sensitivity: 5 Key Metrics", fontsize=16, fontweight="bold")

    # Extract data by SLM threshold (averaging across LLM thresholds)
    slm_thresholds = sorted(set(r["slm_threshold"] for r in sweep_results))

    metrics_by_slm = {
        "diversity": {},
        "robustness": {},
        "mean_confidence": {},
        "min_confidence": {},
        "gap": {},
        "slm_coverage": {},
    }

    for slm_t in slm_thresholds:
        configs = [r for r in sweep_results if abs(r["slm_threshold"] - slm_t) < 0.001]
        for metric_name in metrics_by_slm.keys():
            values = [c[metric_name] if metric_name != "mean_confidence" else c["mean_confidence"]
                     for c in configs if metric_name in c or metric_name == "mean_confidence"]
            if values:
                metrics_by_slm[metric_name][slm_t] = np.mean(values)

    # Panel 1: Diversity
    ax = axes[0, 0]
    ax.plot(list(metrics_by_slm["diversity"].keys()), list(metrics_by_slm["diversity"].values()),
            "o-", linewidth=2, markersize=8, color="#3498db")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("Diversity Score", fontweight="bold")
    ax.set_title("1. Tier Diversity (Balance)", fontweight="bold", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.grid(alpha=0.3)
    ax.legend()

    # Panel 2: Robustness
    ax = axes[0, 1]
    ax.plot(list(metrics_by_slm["robustness"].keys()), list(metrics_by_slm["robustness"].values()),
            "s-", linewidth=2, markersize=8, color="#2ecc71")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("Robustness Score", fontweight="bold")
    ax.set_title("2. Robustness (Stability)", fontweight="bold", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.grid(alpha=0.3)
    ax.legend()

    # Panel 3: Mean Confidence
    ax = axes[0, 2]
    ax.plot(list(metrics_by_slm["mean_confidence"].keys()), list(metrics_by_slm["mean_confidence"].values()),
            "^-", linewidth=2, markersize=8, color="#f39c12")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("Mean Confidence (%)", fontweight="bold")
    ax.set_title("3. Mean Confidence (Certainty)", fontweight="bold", fontsize=12)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend()

    # Panel 4: Min Confidence
    ax = axes[1, 0]
    ax.plot(list(metrics_by_slm["min_confidence"].keys()), list(metrics_by_slm["min_confidence"].values()),
            "d-", linewidth=2, markersize=8, color="#e74c3c")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("Min Confidence (%)", fontweight="bold")
    ax.set_title("4. Min Confidence (Risk)", fontweight="bold", fontsize=12)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.legend()

    # Panel 5: Gap
    ax = axes[1, 1]
    ax.plot(list(metrics_by_slm["gap"].keys()), list(metrics_by_slm["gap"].values()),
            "o-", linewidth=2, markersize=8, color="#9b59b6")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.axhline(y=0.40, color="red", linestyle=":", linewidth=1, alpha=0.5)
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("Gap (SLM - LLM)", fontweight="bold")
    ax.set_title("5. Gap (Tier Separation)", fontweight="bold", fontsize=12)
    ax.grid(alpha=0.3)
    ax.legend()

    # Panel 6: SLM Coverage
    ax = axes[1, 2]
    ax.plot(list(metrics_by_slm["slm_coverage"].keys()), list(metrics_by_slm["slm_coverage"].values()),
            "o-", linewidth=2, markersize=8, color="#1abc9c")
    ax.axvline(x=0.70, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontweight="bold")
    ax.set_ylabel("SLM Coverage", fontweight="bold")
    ax.set_title("SLM Coverage (%)", fontweight="bold", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.grid(alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n[OK] Visualization saved to {output_path}")
    plt.close()


def main():
    """Run sensitivity analysis with 5 key metrics."""
    print("\nLoading UC empirical routing results...")
    uc_results = load_uc_empirical_results()
    rho_bars = extract_rho_bars(uc_results)

    print("Running sensitivity analysis with 5 key metrics...")
    sweep_results = analyze_uc_tier_sensitivity_v2(rho_bars)

    print(f"Tested {len(sweep_results)} configurations")

    # Print summary
    print_metrics_summary(sweep_results, rho_bars)
    print_detailed_comparison(sweep_results)

    # Visualize
    plot_metrics(sweep_results)

    # Save results
    results_to_save = {
        "metrics_description": {
            "tier_diversity_score": "How balanced are tiers? (0-1, higher=balanced)",
            "robustness_score": "How stable are assignments? (0-1, higher=stable)",
            "mean_confidence": "How certain are assignments? (0-100%, higher=certain)",
            "min_confidence": "What's the riskiest UC? (0-100%, higher=safer)",
            "gap": "HYBRID zone width (higher=more separation)",
        },
        "sweep_results": [
            {
                "slm_threshold": r["slm_threshold"],
                "llm_threshold": r["llm_threshold"],
                "tier_diversity_score": r["tier_diversity_score"],
                "robustness_score": r["robustness_score"],
                "mean_confidence": r["mean_confidence"],
                "min_confidence": r["min_confidence"],
                "riskiest_uc": r["riskiest_uc"],
                "gap": r["gap"],
                "tier_counts": r["tier_counts"],
                "slm_coverage": r["slm_coverage"],
            }
            for r in sweep_results
        ],
    }

    output_path = Path("model_runs/uc_tier_metrics_v2.json")
    with open(output_path, "w") as f:
        json.dump(results_to_save, f, indent=2)

    print(f"\n[OK] Results saved to {output_path}")


if __name__ == "__main__":
    main()
