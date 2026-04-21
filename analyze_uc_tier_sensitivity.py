#!/usr/bin/env python3
"""
UC Tier Threshold Sensitivity Analysis

Optimize the tier assignment boundaries (currently 0.70/0.30) using empirical ρ̄ values.

For each (SLM_threshold, LLM_threshold) pair:
1. Assign all 8 UCs to tiers using those thresholds
2. Compute tier distribution and metrics
3. Find configuration that optimizes for different objectives
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Warning: matplotlib not available - skipping visualization")
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
    """
    Assign UCs to tiers using given thresholds.

    ρ̄ >= slm_threshold → SLM
    ρ̄ <= llm_threshold → LLM
    else → HYBRID
    """
    assignments = {}
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}

    for uc, rho_bar in sorted(rho_bars.items()):
        if rho_bar >= slm_threshold:
            tier = "SLM"
        elif rho_bar <= llm_threshold:
            tier = "LLM"
        else:
            tier = "HYBRID"

        assignments[uc] = {
            "rho_bar": rho_bar,
            "tier": tier,
        }
        tier_counts[tier] += 1

    return {
        "assignments": assignments,
        "tier_counts": tier_counts,
        "slm_coverage": tier_counts["SLM"] / 8,
        "hybrid_count": tier_counts["HYBRID"],
        "llm_coverage": tier_counts["LLM"] / 8,
    }


def analyze_uc_tier_sensitivity(
    rho_bars: Dict[str, float],
    slm_range: Tuple[float, float] = (0.50, 0.85),
    llm_range: Tuple[float, float] = (0.10, 0.35),
    step: float = 0.05,
) -> Dict:
    """
    Sweep through different tier thresholds and analyze results.

    Returns metrics for each (SLM_threshold, LLM_threshold) pair.
    """
    sweep_results = []

    slm_thresholds = np.arange(slm_range[0], slm_range[1] + step, step)
    llm_thresholds = np.arange(llm_range[0], llm_range[1] + step, step)

    for slm_thresh in slm_thresholds:
        for llm_thresh in llm_thresholds:
            # Skip invalid configs (LLM threshold must be < SLM threshold)
            if llm_thresh >= slm_thresh:
                continue

            result = assign_uc_tiers(rho_bars, slm_thresh, llm_thresh)
            result["slm_threshold"] = slm_thresh
            result["llm_threshold"] = llm_thresh

            # Compute metrics
            result["gap"] = slm_thresh - llm_thresh  # Width of HYBRID zone
            result["hybrid_ratio"] = result["tier_counts"]["HYBRID"] / 8
            result["is_valid"] = llm_thresh < slm_thresh

            sweep_results.append(result)

    return sweep_results


def find_optimal_configurations(sweep_results: List[Dict]) -> Dict:
    """
    Find optimal thresholds for different objectives.
    """
    optimal = {}

    # Objective 1: Minimize HYBRID tier (clearest classification)
    by_hybrid = sorted(sweep_results, key=lambda x: (x["hybrid_ratio"], x["gap"]))
    optimal["minimize_hybrid"] = by_hybrid[0]

    # Objective 2: Maximize SLM coverage (lowest cost)
    by_slm_coverage = sorted(sweep_results, key=lambda x: -x["slm_coverage"])
    optimal["maximize_slm"] = by_slm_coverage[0]

    # Objective 3: Maximize gap (clearer tier separation)
    by_gap = sorted(sweep_results, key=lambda x: -x["gap"])
    optimal["maximize_gap"] = by_gap[0]

    # Objective 4: Closest to paper thresholds (0.70/0.30)
    by_paper_distance = sorted(
        sweep_results,
        key=lambda x: abs(x["slm_threshold"] - 0.70) + abs(x["llm_threshold"] - 0.30)
    )
    optimal["closest_to_paper"] = by_paper_distance[0]

    return optimal


def print_summary(rho_bars: Dict, optimal_configs: Dict, paper_config: Dict):
    """Print summary of findings."""
    print("\n" + "=" * 100)
    print("UC TIER THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 100)

    print("\nEmpirical rho_bar values (from UC routing):")
    for uc in sorted(rho_bars.keys()):
        print(f"  {uc}: {rho_bars[uc]:.4f}")

    print("\n" + "-" * 100)
    print("PAPER BASELINE (0.70/0.30):")
    print("-" * 100)
    print(f"  SLM threshold:    {paper_config['slm_threshold']:.2f}")
    print(f"  LLM threshold:    {paper_config['llm_threshold']:.2f}")
    print(f"  Gap (HYBRID zone): {paper_config['gap']:.2f}")
    print(f"  Tier distribution: SLM={paper_config['tier_counts']['SLM']}, "
          f"HYBRID={paper_config['tier_counts']['HYBRID']}, "
          f"LLM={paper_config['tier_counts']['LLM']}")
    print(f"  SLM coverage:     {paper_config['slm_coverage']:.1%}")
    print(f"  HYBRID count:     {paper_config['hybrid_ratio']:.1%} ({paper_config['tier_counts']['HYBRID']} UCs)")

    print("\n" + "-" * 100)
    print("OPTIMAL CONFIGURATIONS:")
    print("-" * 100)

    # Objective 1: Minimize HYBRID
    opt1 = optimal_configs["minimize_hybrid"]
    print(f"\n1. MINIMIZE HYBRID TIER (clearest classification):")
    print(f"   Thresholds: {opt1['slm_threshold']:.2f} / {opt1['llm_threshold']:.2f}")
    print(f"   Gap:        {opt1['gap']:.2f}")
    print(f"   Tiers:      SLM={opt1['tier_counts']['SLM']}, "
          f"HYBRID={opt1['tier_counts']['HYBRID']}, "
          f"LLM={opt1['tier_counts']['LLM']}")
    print(f"   Benefit:    Reduces HYBRID from {paper_config['tier_counts']['HYBRID']} to {opt1['tier_counts']['HYBRID']} UCs")

    # Objective 2: Maximize SLM coverage
    opt2 = optimal_configs["maximize_slm"]
    print(f"\n2. MAXIMIZE SLM COVERAGE (lowest cost):")
    print(f"   Thresholds: {opt2['slm_threshold']:.2f} / {opt2['llm_threshold']:.2f}")
    print(f"   Gap:        {opt2['gap']:.2f}")
    print(f"   Tiers:      SLM={opt2['tier_counts']['SLM']}, "
          f"HYBRID={opt2['tier_counts']['HYBRID']}, "
          f"LLM={opt2['tier_counts']['LLM']}")
    print(f"   Benefit:    Increases SLM coverage from {paper_config['slm_coverage']:.1%} to {opt2['slm_coverage']:.1%}")

    # Objective 3: Maximize gap
    opt3 = optimal_configs["maximize_gap"]
    print(f"\n3. MAXIMIZE GAP (clearest tier separation):")
    print(f"   Thresholds: {opt3['slm_threshold']:.2f} / {opt3['llm_threshold']:.2f}")
    print(f"   Gap:        {opt3['gap']:.2f} (Paper: {paper_config['gap']:.2f})")
    print(f"   Tiers:      SLM={opt3['tier_counts']['SLM']}, "
          f"HYBRID={opt3['tier_counts']['HYBRID']}, "
          f"LLM={opt3['tier_counts']['LLM']}")
    print(f"   Benefit:    Wider HYBRID zone allows clearer tier separation")

    # Objective 4: Closest to paper
    opt4 = optimal_configs["closest_to_paper"]
    dist = abs(opt4['slm_threshold'] - 0.70) + abs(opt4['llm_threshold'] - 0.30)
    print(f"\n4. CLOSEST TO PAPER THRESHOLDS (minimal change):")
    print(f"   Thresholds: {opt4['slm_threshold']:.2f} / {opt4['llm_threshold']:.2f}")
    print(f"   Gap:        {opt4['gap']:.2f}")
    print(f"   Tiers:      SLM={opt4['tier_counts']['SLM']}, "
          f"HYBRID={opt4['tier_counts']['HYBRID']}, "
          f"LLM={opt4['tier_counts']['LLM']}")
    print(f"   Distance from paper: {dist:.2f}")

    print("\n" + "=" * 100)


def print_detailed_tier_assignments(sweep_results: List[Dict], rho_bars: Dict):
    """Show tier assignments for interesting configurations."""
    print("\n" + "=" * 100)
    print("DETAILED TIER ASSIGNMENTS FOR KEY CONFIGURATIONS")
    print("=" * 100)

    # Show a few interesting configs
    interesting_configs = []

    # Config 1: Paper (0.70/0.30)
    for config in sweep_results:
        if abs(config["slm_threshold"] - 0.70) < 0.01 and abs(config["llm_threshold"] - 0.30) < 0.01:
            interesting_configs.append(("PAPER (0.70/0.30)", config))
            break

    # Config 2: Minimize hybrid
    config = min(sweep_results, key=lambda x: x["hybrid_ratio"])
    interesting_configs.append(("MINIMIZE HYBRID", config))

    # Config 3: Maximize SLM
    config = max(sweep_results, key=lambda x: x["slm_coverage"])
    interesting_configs.append(("MAXIMIZE SLM", config))

    # Config 4: Maximize gap
    config = max(sweep_results, key=lambda x: x["gap"])
    interesting_configs.append(("MAXIMIZE GAP", config))

    for label, config in interesting_configs:
        print(f"\n{label}")
        print(f"Thresholds: {config['slm_threshold']:.2f} / {config['llm_threshold']:.2f} "
              f"(gap={config['gap']:.2f})")
        print("-" * 100)

        for uc in sorted(config["assignments"].keys()):
            assignment = config["assignments"][uc]
            rho_bar = assignment["rho_bar"]
            tier = assignment["tier"]

            # Visual indicator
            if tier == "SLM":
                marker = "-> SLM  [OK]"
            elif tier == "LLM":
                marker = "-> LLM  [REQUIRED]"
            else:
                marker = "-> HYBRID [MIXED]"

            print(f"  {uc}: rho_bar={rho_bar:.4f}  {marker}")

        counts = config["tier_counts"]
        print(f"\n  Distribution: SLM={counts['SLM']}, HYBRID={counts['HYBRID']}, LLM={counts['LLM']}")


def plot_uc_tier_sensitivity(sweep_results: List[Dict], rho_bars: Dict, paper_config: Dict):
    """Visualize UC tier threshold sensitivity analysis."""
    if plt is None:
        print("Skipping visualization (matplotlib not available)")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("UC Tier Threshold Sensitivity Analysis", fontsize=16, fontweight="bold")

    # Extract data
    slm_thresholds = sorted(set(c["slm_threshold"] for c in sweep_results))

    # Panel 1: Tier Distribution vs SLM Threshold
    ax = axes[0, 0]
    slm_coverage_by_slm = {}
    hybrid_ratio_by_slm = {}
    llm_coverage_by_slm = {}

    for slm_t in slm_thresholds:
        configs_for_t = [c for c in sweep_results if abs(c["slm_threshold"] - slm_t) < 0.001]
        if configs_for_t:
            # Average across LLM thresholds
            avg_slm = np.mean([c["slm_coverage"] for c in configs_for_t])
            avg_hybrid = np.mean([c["hybrid_ratio"] for c in configs_for_t])
            avg_llm = np.mean([c["llm_coverage"] for c in configs_for_t])

            slm_coverage_by_slm[slm_t] = avg_slm
            hybrid_ratio_by_slm[slm_t] = avg_hybrid
            llm_coverage_by_slm[slm_t] = avg_llm

    ax.plot(list(slm_coverage_by_slm.keys()), list(slm_coverage_by_slm.values()),
            "o-", label="SLM coverage", linewidth=2, markersize=8, color="#2ecc71")
    ax.plot(list(hybrid_ratio_by_slm.keys()), list(hybrid_ratio_by_slm.values()),
            "s-", label="HYBRID ratio", linewidth=2, markersize=8, color="#f39c12")
    ax.plot(list(llm_coverage_by_slm.keys()), list(llm_coverage_by_slm.values()),
            "^-", label="LLM coverage", linewidth=2, markersize=8, color="#e74c3c")

    ax.axvline(x=paper_config["slm_threshold"], color="red", linestyle="--", linewidth=2, alpha=0.7, label="Paper (0.70)")
    ax.set_xlabel("SLM Threshold", fontsize=11, fontweight="bold")
    ax.set_ylabel("Proportion of UCs", fontsize=11, fontweight="bold")
    ax.set_title("Panel 1: Tier Coverage vs SLM Threshold", fontsize=12, fontweight="bold")
    ax.legend(loc="right", fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 1.0)

    # Panel 2: HYBRID Count vs Thresholds
    ax = axes[0, 1]
    hybrid_counts = [c["tier_counts"]["HYBRID"] for c in sweep_results]
    gaps = [c["gap"] for c in sweep_results]

    scatter = ax.scatter(gaps, hybrid_counts, c=[c["slm_threshold"] for c in sweep_results],
                        cmap="RdYlGn_r", s=100, alpha=0.6, edgecolor="black", linewidth=1)

    # Mark paper config
    ax.scatter([paper_config["gap"]], [paper_config["tier_counts"]["HYBRID"]],
              color="red", s=300, marker="*", edgecolor="black", linewidth=2, label="Paper (0.70/0.30)", zorder=5)

    # Mark optimal (minimize hybrid)
    optimal_min_hybrid = min(sweep_results, key=lambda x: x["hybrid_ratio"])
    ax.scatter([optimal_min_hybrid["gap"]], [optimal_min_hybrid["tier_counts"]["HYBRID"]],
              color="green", s=300, marker="D", edgecolor="black", linewidth=2, label="Optimal (minimize HYBRID)", zorder=5)

    ax.set_xlabel("Gap (SLM - LLM threshold)", fontsize=11, fontweight="bold")
    ax.set_ylabel("HYBRID Count", fontsize=11, fontweight="bold")
    ax.set_title("Panel 2: HYBRID Tier Size vs Gap", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("SLM Threshold", fontsize=10)

    # Panel 3: SLM Coverage vs LLM Threshold
    ax = axes[1, 0]
    llm_thresholds = sorted(set(c["llm_threshold"] for c in sweep_results))
    slm_coverage_by_llm = {}

    for llm_t in llm_thresholds:
        configs_for_t = [c for c in sweep_results if abs(c["llm_threshold"] - llm_t) < 0.001]
        if configs_for_t:
            avg_slm = np.mean([c["slm_coverage"] for c in configs_for_t])
            slm_coverage_by_llm[llm_t] = avg_slm

    ax.plot(list(slm_coverage_by_llm.keys()), list(slm_coverage_by_llm.values()),
            "o-", linewidth=2, markersize=10, color="#3498db")
    ax.axhline(y=paper_config["slm_coverage"], color="red", linestyle="--", linewidth=2, alpha=0.7, label=f"Paper ({paper_config['slm_coverage']:.1%})")
    ax.set_xlabel("LLM Threshold", fontsize=11, fontweight="bold")
    ax.set_ylabel("SLM Coverage", fontsize=11, fontweight="bold")
    ax.set_title("Panel 3: SLM Coverage vs LLM Threshold", fontsize=12, fontweight="bold")
    ax.legend(loc="lower left", fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 1.0)

    # Panel 4: Configuration Matrix
    ax = axes[1, 1]

    # Create a heatmap-style view
    config_labels = [
        "Paper (0.70/0.30)",
        "Min HYBRID",
        "Max SLM",
        "Max GAP"
    ]

    optimal_min_hybrid = min(sweep_results, key=lambda x: x["hybrid_ratio"])
    optimal_max_slm = max(sweep_results, key=lambda x: x["slm_coverage"])
    optimal_max_gap = max(sweep_results, key=lambda x: x["gap"])

    configs = [
        paper_config,
        optimal_min_hybrid,
        optimal_max_slm,
        optimal_max_gap
    ]

    y_pos = np.arange(len(config_labels))
    colors_slm = [c["slm_coverage"] for c in configs]
    colors_hybrid = [c["hybrid_ratio"] for c in configs]
    colors_llm = [c["llm_coverage"] for c in configs]

    bars1 = ax.barh(y_pos - 0.25, colors_slm, 0.25, label="SLM", color="#2ecc71")
    bars2 = ax.barh(y_pos, colors_hybrid, 0.25, label="HYBRID", color="#f39c12")
    bars3 = ax.barh(y_pos + 0.25, colors_llm, 0.25, label="LLM", color="#e74c3c")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(config_labels, fontsize=10)
    ax.set_xlabel("Proportion of UCs", fontsize=11, fontweight="bold")
    ax.set_title("Panel 4: Configuration Comparison", fontsize=12, fontweight="bold")
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim(0, 1.0)
    ax.grid(axis="x", alpha=0.3)

    # Add value labels
    for i, (slm, hybrid, llm) in enumerate(zip(colors_slm, colors_hybrid, colors_llm)):
        ax.text(slm/2, i - 0.25, f"{slm:.1%}", va="center", ha="center", fontweight="bold", fontsize=9, color="white")
        ax.text(slm + hybrid/2, i, f"{hybrid:.1%}", va="center", ha="center", fontweight="bold", fontsize=9, color="white")
        ax.text(slm + hybrid + llm/2, i + 0.25, f"{llm:.1%}", va="center", ha="center", fontweight="bold", fontsize=9, color="white")

    plt.tight_layout()
    output_path = Path("model_runs/uc_tier_sensitivity.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n[OK] Visualization saved to {output_path}")
    plt.close()


def main():
    """Run UC tier threshold sensitivity analysis."""
    print("\nLoading UC empirical routing results...")
    uc_results = load_uc_empirical_results()
    rho_bars = extract_rho_bars(uc_results)

    # Paper baseline
    paper_config = assign_uc_tiers(rho_bars, 0.70, 0.30)
    paper_config["slm_threshold"] = 0.70
    paper_config["llm_threshold"] = 0.30
    paper_config["gap"] = 0.40
    paper_config["hybrid_ratio"] = paper_config["tier_counts"]["HYBRID"] / 8

    print("Running sensitivity analysis...")
    sweep_results = analyze_uc_tier_sensitivity(rho_bars)

    print(f"Tested {len(sweep_results)} configurations")

    # Find optimal
    optimal_configs = find_optimal_configurations(sweep_results)

    # Print results
    print_summary(rho_bars, optimal_configs, paper_config)
    print_detailed_tier_assignments(sweep_results, rho_bars)

    # Visualize
    plot_uc_tier_sensitivity(sweep_results, rho_bars, paper_config)

    # Save results
    results = {
        "paper_baseline": {
            "slm_threshold": 0.70,
            "llm_threshold": 0.30,
            "gap": 0.40,
            "tier_counts": paper_config["tier_counts"],
            "slm_coverage": paper_config["slm_coverage"],
        },
        "optimal_configurations": {
            "minimize_hybrid": {
                "slm_threshold": optimal_configs["minimize_hybrid"]["slm_threshold"],
                "llm_threshold": optimal_configs["minimize_hybrid"]["llm_threshold"],
                "gap": optimal_configs["minimize_hybrid"]["gap"],
                "tier_counts": optimal_configs["minimize_hybrid"]["tier_counts"],
                "reason": "Clearest tier classification (fewest UCs in HYBRID)",
            },
            "maximize_slm": {
                "slm_threshold": optimal_configs["maximize_slm"]["slm_threshold"],
                "llm_threshold": optimal_configs["maximize_slm"]["llm_threshold"],
                "gap": optimal_configs["maximize_slm"]["gap"],
                "tier_counts": optimal_configs["maximize_slm"]["tier_counts"],
                "reason": "Lowest cost (most UCs use SLM)",
            },
            "maximize_gap": {
                "slm_threshold": optimal_configs["maximize_gap"]["slm_threshold"],
                "llm_threshold": optimal_configs["maximize_gap"]["llm_threshold"],
                "gap": optimal_configs["maximize_gap"]["gap"],
                "tier_counts": optimal_configs["maximize_gap"]["tier_counts"],
                "reason": "Widest HYBRID zone (most room for nuance)",
            },
        },
        "sweep_summary": {
            "total_configs": len(sweep_results),
            "slm_threshold_range": [0.50, 0.85],
            "llm_threshold_range": [0.10, 0.35],
            "step": 0.05,
        }
    }

    output_path = Path("model_runs/uc_tier_sensitivity.json")
    with open(output_path, "w") as f:
        import json as json_lib
        json_lib.dump(results, f, indent=2)

    print(f"\n[OK] Results saved to {output_path}")


if __name__ == "__main__":
    main()
