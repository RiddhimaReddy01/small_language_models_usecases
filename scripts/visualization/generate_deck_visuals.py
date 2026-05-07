#!/usr/bin/env python3
"""
Generate 4 presentation-quality visualizations from actual SDDF results data.

Outputs:
- fig1_uc_tier_summary.png: Tier distribution + ρ̄ per UC
- fig2_model_consensus.png: Per-model routing divergence per UC
- fig3_task_capability_heatmap.png: Capability scores heatmap (8 tasks × 3 models)
- fig4_routing_coverage.png: Stacked bars (SLM vs LLM) + SLM routing % per task
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_RUNS = PROJECT_ROOT / "model_runs"
OUTPUT_DIR = MODEL_RUNS / "deck_visuals"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Consistent color scheme
TIER_COLORS = {"SLM": "#2ecc71", "HYBRID": "#f39c12", "LLM": "#e74c3c"}
MODEL_COLORS = {
    "qwen2.5_0.5b": "#e74c3c",   # red
    "qwen2.5_3b": "#e67e22",      # orange
    "qwen2.5_7b": "#2ecc71",      # green
}

# Data files
UC_EMPIRICAL_FILE = MODEL_RUNS / "uc_empirical_routing.json"
TEST_RESULTS_FILE = MODEL_RUNS / "test_results.json"
TRAINING_SUMMARY_FILE = MODEL_RUNS / "training_summary.json"


# ============================================================================
# LOADERS
# ============================================================================

def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    if not filepath.exists():
        raise FileNotFoundError(f"Required data file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)


def load_uc_data() -> Dict[str, Dict]:
    """Load UC empirical routing data."""
    return load_json(UC_EMPIRICAL_FILE)


def load_test_results() -> Dict[str, Dict]:
    """Load per-task test results with routing counts."""
    return load_json(TEST_RESULTS_FILE)


def load_training_summary() -> List[Dict]:
    """Load training summary (list of capability records)."""
    return load_json(TRAINING_SUMMARY_FILE)


# ============================================================================
# FIGURE 1: UC TIER SUMMARY (2-panel)
# ============================================================================

def generate_fig1_uc_tier_summary():
    """
    Left: Donut chart of tier distribution (5 SLM / 2 HYBRID / 1 LLM)
    Right: Horizontal bar chart of ρ̄ per UC with threshold lines
    """
    uc_data = load_uc_data()

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("UC Tier Assignment Summary", fontsize=14, fontweight="bold")

    # Extract tier distribution
    uc_names = sorted(uc_data.keys())
    rho_bars = [uc_data[uc]["rho_bar"] for uc in uc_names]
    tiers = [uc_data[uc]["tier"] for uc in uc_names]

    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    for tier in tiers:
        tier_counts[tier] += 1

    # LEFT PANEL: Donut chart
    tier_list = ["SLM", "HYBRID", "LLM"]
    counts = [tier_counts[t] for t in tier_list]
    colors = [TIER_COLORS[t] for t in tier_list]

    wedges, texts, autotexts = ax_left.pie(
        counts, labels=tier_list, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"fontsize": 11, "fontweight": "bold"}
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax_left.set_title(f"Tier Distribution (n={len(uc_names)} UCs)", fontweight="bold")

    # Add count labels
    for i, (tier, count) in enumerate(zip(tier_list, counts)):
        texts[i].set_text(f"{tier}\n({count})")

    # RIGHT PANEL: Horizontal bars with threshold lines
    y_pos = np.arange(len(uc_names))
    colors_right = [TIER_COLORS[tiers[i]] for i in range(len(uc_names))]

    ax_right.barh(y_pos, rho_bars, color=colors_right, edgecolor="black", linewidth=1)
    ax_right.axvline(x=0.50, color="green", linestyle="--", linewidth=2, label="SLM threshold (0.50)")
    ax_right.axvline(x=0.30, color="red", linestyle="--", linewidth=2, label="LLM threshold (0.30)")

    ax_right.set_yticks(y_pos)
    ax_right.set_yticklabels(uc_names, fontsize=10)
    ax_right.set_xlabel("ρ̄ (Consensus Routing Ratio)", fontsize=11, fontweight="bold")
    ax_right.set_title("Empirical ρ̄ by Use Case", fontweight="bold")
    ax_right.set_xlim(0, 1.05)
    ax_right.legend(loc="lower right", fontsize=9)
    ax_right.grid(axis="x", alpha=0.3)

    # Add value labels on bars
    for i, (rho, tier) in enumerate(zip(rho_bars, tiers)):
        ax_right.text(rho + 0.02, i, f"{rho:.3f}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig1_uc_tier_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Generated fig1_uc_tier_summary.png")


# ============================================================================
# FIGURE 2: MODEL CONSENSUS DIVERGENCE
# ============================================================================

def generate_fig2_model_consensus():
    """
    Grouped bar chart: 3 bars per UC showing per-model routing ratios.
    Reveals consensus vs. divergence (UC5 perfect; UC2 extreme divergence).
    """
    uc_data = load_uc_data()

    uc_names = sorted(uc_data.keys())
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

    # Extract per-model rho values
    data_by_model = {model: [] for model in model_names}
    for uc in uc_names:
        per_model_rho = uc_data[uc]["per_model_rho"]
        for model in model_names:
            data_by_model[model].append(per_model_rho.get(model, 0.0))

    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(uc_names))
    width = 0.25

    for i, model in enumerate(model_names):
        offset = width * (i - 1)
        ax.bar(x + offset, data_by_model[model], width, label=model,
               color=MODEL_COLORS[model], edgecolor="black", linewidth=0.5)

    ax.set_ylabel("Per-model rho (Routing Ratio)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Use Case", fontsize=11, fontweight="bold")
    ax.set_title("Model Consensus: Per-Model Routing Ratios Across UCs", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(uc_names, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # Highlight divergence
    for i, uc in enumerate(uc_names):
        ratios = list(uc_data[uc]["per_model_rho"].values())
        divergence = max(ratios) - min(ratios)
        if divergence > 0.5:
            ax.text(i, 1.08, f"<> {divergence:.2f}", ha="center", fontsize=8, color="red", fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig2_model_consensus.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Generated fig2_model_consensus.png")


# ============================================================================
# FIGURE 3: TASK CAPABILITY HEATMAP
# ============================================================================

def generate_fig3_capability_heatmap():
    """
    Heatmap: 8 tasks × 3 models, cells = test_capability scores.
    """
    training_data = load_training_summary()

    task_families = [
        "classification", "code_generation", "information_extraction",
        "instruction_following", "maths", "retrieval_grounded",
        "summarization", "text_generation"
    ]
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

    # Build capability matrix
    capability_matrix = np.zeros((len(task_families), len(model_names)))

    # training_data is {task_family: {model: {test_capability: ...}}}
    for task, models_dict in training_data.items():
        if task in task_families:
            ti = task_families.index(task)
            for model, record in models_dict.items():
                if model in model_names:
                    mi = model_names.index(model)
                    test_cap = record.get("test_capability", None)
                    if test_cap is not None:
                        capability_matrix[ti, mi] = test_cap

    fig, ax = plt.subplots(figsize=(10, 8))

    im = ax.imshow(capability_matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(np.arange(len(model_names)))
    ax.set_yticks(np.arange(len(task_families)))
    ax.set_xticklabels(model_names, fontsize=10)
    ax.set_yticklabels(task_families, fontsize=10)

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Annotate cells with capability values
    for i in range(len(task_families)):
        for j in range(len(model_names)):
            value = capability_matrix[i, j]
            if value > 0:
                text = ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                              color="white" if value > 0.5 else "black", fontweight="bold")

    ax.set_title("Test Capability Scores: Tasks × Models", fontweight="bold", fontsize=12)
    ax.set_ylabel("Task Family", fontweight="bold")
    ax.set_xlabel("SLM Model", fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, label="Test Capability (0-1)")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig3_task_capability_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Generated fig3_task_capability_heatmap.png")


# ============================================================================
# FIGURE 4: ROUTING COVERAGE ANALYSIS
# ============================================================================

def generate_fig4_routing_coverage():
    """
    Left: Stacked bar per task (SLM vs LLM routed query counts)
    Right: SLM routing % per task family (sorted descending)
    """
    test_results = load_test_results()

    task_families = [
        "classification", "code_generation", "information_extraction",
        "instruction_following", "maths", "retrieval_grounded",
        "summarization", "text_generation"
    ]

    # Extract routing counts and compute percentages
    slm_routed = []
    llm_routed = []
    slm_pct = []

    for task in task_families:
        if task in test_results:
            slm = test_results[task].get("slm_routed", 0)
            llm = test_results[task].get("llm_routed", 0)
            total = slm + llm
            slm_routed.append(slm)
            llm_routed.append(llm)
            slm_pct.append(100 * slm / total if total > 0 else 0)
        else:
            slm_routed.append(0)
            llm_routed.append(0)
            slm_pct.append(0)

    # Sort by SLM percentage descending
    sorted_indices = sorted(range(len(slm_pct)), key=lambda i: slm_pct[i], reverse=True)
    sorted_tasks = [task_families[i] for i in sorted_indices]
    sorted_slm = [slm_routed[i] for i in sorted_indices]
    sorted_llm = [llm_routed[i] for i in sorted_indices]
    sorted_pct = [slm_pct[i] for i in sorted_indices]

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Routing Coverage: SLM vs LLM Query Distribution", fontsize=14, fontweight="bold")

    # LEFT PANEL: Stacked bars
    x = np.arange(len(sorted_tasks))
    ax_left.bar(x, sorted_slm, label="SLM Routed", color="#2ecc71", edgecolor="black", linewidth=0.5)
    ax_left.bar(x, sorted_llm, bottom=sorted_slm, label="LLM Routed", color="#e74c3c", edgecolor="black", linewidth=0.5)

    ax_left.set_ylabel("Query Count", fontsize=11, fontweight="bold")
    ax_left.set_title("Stacked: SLM vs LLM Routed Queries", fontweight="bold")
    ax_left.set_xticks(x)
    ax_left.set_xticklabels(sorted_tasks, rotation=45, ha="right")
    ax_left.legend(loc="upper right")
    ax_left.grid(axis="y", alpha=0.3)

    # RIGHT PANEL: SLM percentage bars
    colors_right = ["#2ecc71" if pct > 50 else "#f39c12" if pct > 0 else "#e74c3c"
                    for pct in sorted_pct]
    ax_right.barh(x, sorted_pct, color=colors_right, edgecolor="black", linewidth=1)
    ax_right.axvline(x=50, color="gray", linestyle="--", linewidth=1, alpha=0.7)

    ax_right.set_ylabel("Task Family", fontsize=11, fontweight="bold")
    ax_right.set_xlabel("SLM Routing %", fontsize=11, fontweight="bold")
    ax_right.set_title("SLM Routing Rate (sorted)", fontweight="bold")
    ax_right.set_yticks(x)
    ax_right.set_yticklabels(sorted_tasks, fontsize=10)
    ax_right.set_xlim(0, 100)
    ax_right.grid(axis="x", alpha=0.3)

    # Add percentage labels
    for i, pct in enumerate(sorted_pct):
        ax_right.text(pct + 2, i, f"{pct:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig4_routing_coverage.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Generated fig4_routing_coverage.png")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Generate all 4 deck visualizations."""
    print(f"\nGenerating deck visuals in {OUTPUT_DIR}")
    print("=" * 60)

    try:
        generate_fig1_uc_tier_summary()
        generate_fig2_model_consensus()
        generate_fig3_capability_heatmap()
        generate_fig4_routing_coverage()

        print("=" * 60)
        print(f"[SUCCESS] All 4 figures generated successfully!")
        print(f"  Location: {OUTPUT_DIR}/")
        return 0

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
