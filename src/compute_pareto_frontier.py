#!/usr/bin/env python3
"""
Pareto Frontier Analysis
Identifies optimal efficiency frontier for model selection
Generates: pareto_analysis.json, pareto visualizations
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple

MODEL_CONFIG = {
    "tinyllama_1.1b": {"name": "TinyLLaMA", "params": 0.5},
    "qwen2.5_1.5b": {"name": "Qwen2.5", "params": 1.5},
    "phi3_mini": {"name": "Phi-3", "params": 3.8},
    "groq_mixtral-8x7b-32768": {"name": "Mixtral-8x7B", "params": 45},
    "llama_llama-3.3-70b-versatile": {"name": "Llama-3.3-70B", "params": 70},
}

BINS = [0, 1, 2, 3, 4]
BIN_NAMES = ["Easy", "Medium", "Hard", "Very Hard", "Hardest"]


def load_cost_data() -> pd.DataFrame:
    """Load cost analysis data"""
    cost_path = Path("analysis") / "cost_analysis.csv"
    if cost_path.exists():
        return pd.read_csv(cost_path)
    return None


def is_pareto_efficient(costs: List[Tuple[float, float, float]]) -> List[int]:
    """
    Check which points are on Pareto frontier
    Higher accuracy, lower latency, lower cost = better

    Args:
        costs: List of (accuracy, -latency, -cost) tuples

    Returns:
        List of indices that are Pareto efficient
    """
    is_efficient = [True] * len(costs)

    for i in range(len(costs)):
        if not is_efficient[i]:
            continue

        for j in range(len(costs)):
            if i == j or not is_efficient[j]:
                continue

            # j dominates i if j is better in all dimensions
            if (costs[j][0] >= costs[i][0] and
                costs[j][1] >= costs[i][1] and  # Higher (negative latency) = lower latency
                costs[j][2] >= costs[i][2] and  # Higher (negative cost) = lower cost
                not (costs[j] == costs[i])):

                is_efficient[i] = False
                break

    return is_efficient


def compute_pareto_frontier() -> Dict:
    """
    Compute Pareto-efficient frontier for each difficulty bin

    Returns: Dict with Pareto analysis per bin
    """
    cost_df = load_cost_data()
    if cost_df is None:
        print("[ERROR] Need to run compute_cost_analysis.py first")
        return None

    print("Computing Pareto frontier...")

    pareto_analysis = {}

    for bin_id in BINS:
        bin_name = BIN_NAMES[bin_id]
        bin_data = cost_df[cost_df["bin"] == bin_id].copy()
        bin_data = bin_data.sort_values("model_params")

        if bin_data.empty:
            continue

        # Prepare cost tuples (we want to maximize accuracy, minimize latency/cost)
        costs = [(row["accuracy"], -row["latency_ms"], -row["cost_per_1k_tokens"])
                 for _, row in bin_data.iterrows()]

        # Compute Pareto efficiency
        efficient_indices = is_pareto_efficient(costs)

        pareto_models = []
        dominated_models = []

        for idx, (efficient, _) in enumerate(zip(efficient_indices, bin_data.iterrows())):
            _, row = list(bin_data.iterrows())[idx]

            model_info = {
                "model_name": row["model_display"],
                "model_params": float(row["model_params"]),
                "accuracy": float(row["accuracy"]),
                "latency_ms": float(row["latency_ms"]),
                "cost_per_1k": float(row["cost_per_1k_tokens"]),
                "quality_score": float(row["quality_score"]),
                "speed_score": float(row["speed_score"]),
                "cost_score": float(row["cost_score"]),
                "composite_score": float(row["composite_score"]),
            }

            if efficient:
                pareto_models.append(model_info)
            else:
                dominated_models.append(model_info)

        # Find best model in each category
        best_accuracy = max(pareto_models, key=lambda x: x["accuracy"]) if pareto_models else None
        best_latency = min(pareto_models, key=lambda x: x["latency_ms"]) if pareto_models else None
        best_cost = min(pareto_models, key=lambda x: x["cost_per_1k"]) if pareto_models else None
        best_composite = max(pareto_models, key=lambda x: x["composite_score"]) if pareto_models else None

        pareto_analysis[f"Bin {bin_id} ({bin_name})"] = {
            "pareto_models": sorted(pareto_models, key=lambda x: x["model_params"]),
            "dominated_models": sorted(dominated_models, key=lambda x: x["model_params"]),
            "best_accuracy_model": best_accuracy,
            "best_latency_model": best_latency,
            "best_cost_model": best_cost,
            "best_overall_model": best_composite,
            "pareto_count": len(pareto_models),
            "efficiency": f"{len(pareto_models)} of {len(bin_data)} models on frontier",
        }

    return pareto_analysis


def compute_efficiency_matrix() -> pd.DataFrame:
    """
    Create efficiency matrix: models vs bins

    Returns: DataFrame showing which models are Pareto-efficient per bin
    """
    cost_df = load_cost_data()
    if cost_df is None:
        return None

    results = []

    for bin_id in BINS:
        bin_name = BIN_NAMES[bin_id]
        bin_data = cost_df[cost_df["bin"] == bin_id].copy()
        bin_data = bin_data.sort_values("model_params")

        costs = [(row["accuracy"], -row["latency_ms"], -row["cost_per_1k_tokens"])
                 for _, row in bin_data.iterrows()]

        efficient_indices = is_pareto_efficient(costs)

        for idx, (efficient, _) in enumerate(zip(efficient_indices, bin_data.iterrows())):
            _, row = list(bin_data.iterrows())[idx]

            results.append({
                "bin": bin_id,
                "bin_name": bin_name,
                "model_name": row["model_display"],
                "model_params": row["model_params"],
                "is_pareto_efficient": efficient,
                "accuracy": row["accuracy"],
                "latency_ms": row["latency_ms"],
                "cost_per_1k": row["cost_per_1k_tokens"],
                "composite_score": row["composite_score"],
            })

    df = pd.DataFrame(results)

    # Save efficiency matrix
    eff_path = Path("analysis") / "pareto_efficiency_matrix.csv"
    eff_path.parent.mkdir(exist_ok=True)
    df.to_csv(eff_path, index=False)
    print(f"[OK] Saved: {eff_path}")

    return df


def generate_pareto_summary(pareto_analysis: Dict, efficiency_df: pd.DataFrame):
    """Generate human-readable Pareto summary"""

    summary_path = Path("analysis") / "PARETO_FRONTIER_SUMMARY.md"
    summary_path.parent.mkdir(exist_ok=True)

    with open(summary_path, "w") as f:
        f.write("# Pareto Frontier Analysis\n\n")

        f.write("## Overview\n\n")
        f.write("Models on the Pareto frontier represent optimal tradeoffs between:\n")
        f.write("- **Accuracy**: Correctness of predictions\n")
        f.write("- **Latency**: Inference speed\n")
        f.write("- **Cost**: API pricing\n\n")

        f.write("A model is Pareto-efficient if no other model is better on ALL three dimensions.\n\n")

        f.write("---\n\n")

        for bin_name, analysis in pareto_analysis.items():
            f.write(f"## {bin_name}\n\n")

            f.write(f"**Efficiency**: {analysis['efficiency']}\n\n")

            f.write("### Pareto-Efficient Models\n\n")

            if analysis["pareto_models"]:
                f.write("| Model | Size | Accuracy | Latency | Cost | Score |\n")
                f.write("|-------|------|----------|---------|------|-------|\n")

                for model in analysis["pareto_models"]:
                    f.write(f"| {model['model_name']} | {model['model_params']}B | "
                           f"{model['accuracy']:.1%} | {model['latency_ms']:.0f}ms | "
                           f"${model['cost_per_1k']:.2f} | {model['composite_score']:.2f} |\n")
            else:
                f.write("*No Pareto-efficient models*\n")

            f.write("\n")

            f.write("### Model Recommendations\n\n")

            if analysis["best_accuracy_model"]:
                f.write(f"- **Best Accuracy**: {analysis['best_accuracy_model']['model_name']} "
                       f"({analysis['best_accuracy_model']['accuracy']:.1%})\n")

            if analysis["best_latency_model"]:
                f.write(f"- **Fastest**: {analysis['best_latency_model']['model_name']} "
                       f"({analysis['best_latency_model']['latency_ms']:.0f}ms)\n")

            if analysis["best_cost_model"]:
                f.write(f"- **Cheapest**: {analysis['best_cost_model']['model_name']} "
                       f"(${analysis['best_cost_model']['cost_per_1k']:.2f}/1K)\n")

            if analysis["best_overall_model"]:
                f.write(f"- **Best Overall**: {analysis['best_overall_model']['model_name']} "
                       f"(Score: {analysis['best_overall_model']['composite_score']:.2f})\n")

            f.write("\n")

            if analysis["dominated_models"]:
                f.write("### Dominated Models\n\n")
                f.write("These models are strictly worse than Pareto-efficient models:\n\n")

                for model in analysis["dominated_models"]:
                    f.write(f"- {model['model_name']} ({model['model_params']}B): "
                           f"{model['accuracy']:.1%} accuracy, "
                           f"{model['latency_ms']:.0f}ms, ${model['cost_per_1k']:.2f}/1K\n")

                f.write("\n")

            f.write("---\n\n")

    print(f"[OK] Saved: {summary_path}")


def main():
    print("="*70)
    print("PARETO FRONTIER ANALYSIS")
    print("="*70)

    # Compute Pareto frontier
    pareto_analysis = compute_pareto_frontier()

    if not pareto_analysis:
        print("[ERROR] Failed to compute Pareto frontier")
        return 1

    # Compute efficiency matrix
    efficiency_df = compute_efficiency_matrix()

    # Save Pareto analysis
    pareto_path = Path("analysis") / "pareto_analysis.json"
    pareto_path.parent.mkdir(exist_ok=True)
    with open(pareto_path, "w") as f:
        json.dump(pareto_analysis, f, indent=2)
    print(f"[OK] Saved: {pareto_path}")

    # Generate summary
    generate_pareto_summary(pareto_analysis, efficiency_df)

    print("\n" + "="*70)
    print("PARETO FRONTIER ANALYSIS COMPLETE")
    print("="*70)
    print("\nOutputs:")
    print("  - analysis/pareto_analysis.json")
    print("  - analysis/pareto_efficiency_matrix.csv")
    print("  - analysis/PARETO_FRONTIER_SUMMARY.md")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
