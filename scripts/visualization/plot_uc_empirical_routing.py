#!/usr/bin/env python3
"""
Visualize empirical UC routing results.

Creates 4-panel visualization:
1. Tier distribution (bar chart)
2. ρ̄ values by UC (with tier color coding)
3. Per-model routing divergence (stacked bars)
4. Model size effect on routing confidence
"""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    print("Error: matplotlib not installed")
    exit(1)


def load_results() -> Dict:
    """Load UC routing results from JSON."""
    results_path = Path("model_runs/uc_empirical_routing.json")
    with open(results_path) as f:
        return json.load(f)


def plot_uc_empirical_routing(results: Dict, output_path: Path = Path("model_runs/uc_empirical_routing.png")):
    """Create 4-panel visualization of empirical UC routing."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "Empirical UC Tier Assignments: Consensus Routing Ratios (ρ̄)",
        fontsize=16, fontweight="bold", y=0.995
    )

    # Extract data
    uc_names = []
    uc_order = ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]
    rho_bars = []
    tiers = []
    task_families = []
    model_rhos = {
        "qwen2.5_0.5b": [],
        "qwen2.5_3b": [],
        "qwen2.5_7b": [],
    }

    for uc in uc_order:
        result = results[uc]
        if "error" not in result:
            uc_names.append(uc)
            rho_bars.append(result["rho_bar"])
            tiers.append(result["tier"])
            task_families.append(result["task_family"])
            for model in model_rhos:
                model_rhos[model].append(result["per_model_rho"].get(model, 0))

    # Colors for tiers
    tier_colors = {"SLM": "#2ecc71", "HYBRID": "#f39c12", "LLM": "#e74c3c"}
    colors = [tier_colors[t] for t in tiers]

    # ===== Panel 1: Tier Distribution =====
    ax = axes[0, 0]
    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    for tier in tiers:
        tier_counts[tier] += 1

    tiers_list = list(tier_counts.keys())
    counts = list(tier_counts.values())
    tier_colors_list = [tier_colors[t] for t in tiers_list]

    bars = ax.bar(tiers_list, counts, color=tier_colors_list, edgecolor="black", linewidth=2)
    ax.set_ylabel("Count", fontsize=11, fontweight="bold")
    ax.set_title("Panel 1: Tier Distribution", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(counts) + 1)
    ax.grid(axis="y", alpha=0.3)

    # Add count labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f"{int(height)}", ha="center", va="bottom", fontweight="bold", fontsize=10)

    # ===== Panel 2: ρ̄ Values by UC =====
    ax = axes[0, 1]
    x_pos = np.arange(len(uc_names))
    bars = ax.bar(x_pos, rho_bars, color=colors, edgecolor="black", linewidth=1.5)
    ax.axhline(y=0.50, color="green", linestyle="--", linewidth=2, label="SLM threshold (0.50)")
    ax.axhline(y=0.30, color="red", linestyle="--", linewidth=2, label="LLM threshold (0.30)")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(uc_names, fontsize=10)
    ax.set_ylabel("ρ̄ (Consensus Routing Ratio)", fontsize=11, fontweight="bold")
    ax.set_title("Panel 2: Empirical ρ̄ by UC", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for i, (bar, rho) in enumerate(zip(bars, rho_bars)):
        ax.text(bar.get_x() + bar.get_width()/2., rho + 0.03,
                f"{rho:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # ===== Panel 3: Per-Model Routing Divergence =====
    ax = axes[1, 0]
    x_pos = np.arange(len(uc_names))
    width = 0.25
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]
    model_colors = ["#3498db", "#9b59b6", "#e67e22"]

    for i, model in enumerate(model_names):
        ax.bar(x_pos + i*width, model_rhos[model], width, label=model, color=model_colors[i], edgecolor="black", linewidth=1)

    ax.axhline(y=0.50, color="green", linestyle="--", linewidth=1.5, alpha=0.5, label="SLM threshold")
    ax.axhline(y=0.30, color="red", linestyle="--", linewidth=1.5, alpha=0.5, label="LLM threshold")
    ax.set_xticks(x_pos + width)
    ax.set_xticklabels(uc_names, fontsize=10)
    ax.set_ylabel("Per-Model ρ (Routing Ratio)", fontsize=11, fontweight="bold")
    ax.set_title("Panel 3: Per-Model Routing Divergence", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    # ===== Panel 4: Model Size Effect =====
    ax = axes[1, 1]
    divergence_values = []
    for i in range(len(uc_names)):
        rhos = [model_rhos[m][i] for m in model_names]
        divergence = max(rhos) - min(rhos)
        divergence_values.append(divergence)

    bars = ax.bar(x_pos, divergence_values, color="#95a5a6", edgecolor="black", linewidth=1.5)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(uc_names, fontsize=10)
    ax.set_ylabel("Model Divergence (max ρ - min ρ)", fontsize=11, fontweight="bold")
    ax.set_title("Panel 4: Per-Model Routing Divergence", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(divergence_values) + 0.1)
    ax.grid(axis="y", alpha=0.3)

    # Color bars by divergence severity
    for bar, div in zip(bars, divergence_values):
        if div > 0.5:
            bar.set_color("#e74c3c")  # High divergence - red
        elif div > 0.2:
            bar.set_color("#f39c12")  # Medium divergence - orange
        else:
            bar.set_color("#2ecc71")  # Low divergence - green

    # Add value labels
    for bar, div in zip(bars, divergence_values):
        ax.text(bar.get_x() + bar.get_width()/2., div + 0.02,
                f"{div:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"[OK] Visualization saved to {output_path}")
    plt.close()


def print_summary(results: Dict):
    """Print text summary of results."""
    print("\n" + "=" * 100)
    print("EMPIRICAL UC TIER ASSIGNMENTS SUMMARY")
    print("=" * 100)

    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    for uc in ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]:
        result = results[uc]
        if "error" not in result:
            tier = result["tier"]
            tier_counts[tier] += 1
            print(f"\n{uc:4s} -> {tier:6s} (rho_bar={result['rho_bar']:.4f})")
            print(f"      Task: {result['task_family']:25s} | Domain: {result['domain']}")
            print(f"      Per-model rho: {result['per_model_rho']}")

    print("\n" + "-" * 100)
    print("TIER DISTRIBUTION:")
    for tier, count in tier_counts.items():
        print(f"  {tier:6s}: {count} UCs")

    print("\n" + "=" * 100)


def main():
    """Generate empirical routing visualization."""
    print("\nLoading UC empirical routing results...")
    results = load_results()

    print("\nGenerating visualization...")
    output_path = Path("model_runs/uc_empirical_routing.png")
    plot_uc_empirical_routing(results, output_path)

    print_summary(results)


if __name__ == "__main__":
    main()
