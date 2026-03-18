#!/usr/bin/env python3
"""
Cost-Benefit Analysis
Analyzes latency, quality, and deployment cost tradeoffs
Generates: cost_analysis.csv, cost_benefit_matrix.json
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict

# Model metadata with costs
MODEL_CONFIG = {
    "tinyllama_1.1b": {
        "name": "TinyLLaMA",
        "params": 0.5,
        "type": "SLM-Local",
        "cost_per_1k": 0.0,  # Local - free (CPU)
        "latency_estimate_ms": 5,
        "tokens_per_sec": 200,
    },
    "qwen2.5_1.5b": {
        "name": "Qwen2.5",
        "params": 1.5,
        "type": "SLM-Local",
        "cost_per_1k": 0.0,  # Local - free (CPU)
        "latency_estimate_ms": 10,
        "tokens_per_sec": 100,
    },
    "phi3_mini": {
        "name": "Phi-3",
        "params": 3.8,
        "type": "SLM-Local",
        "cost_per_1k": 0.0,  # Local - free (CPU)
        "latency_estimate_ms": 12,
        "tokens_per_sec": 80,
    },
    "groq_mixtral-8x7b-32768": {
        "name": "Mixtral-8x7B",
        "params": 45,
        "type": "Medium-Cloud",
        "cost_per_1k": 0.27,  # Groq pricing
        "latency_estimate_ms": 2,
        "tokens_per_sec": 5000,
    },
    "llama_llama-3.3-70b-versatile": {
        "name": "Llama-3.3-70B",
        "params": 70,
        "type": "LLM-Cloud",
        "cost_per_1k": 0.40,  # Groq pricing
        "latency_estimate_ms": 3,
        "tokens_per_sec": 3000,
    },
}

TASKS = [
    "text_generation",
    "code_generation",
    "classification",
    "maths",
    "summarization",
    "retrieval_grounded",
    "instruction_following",
    "information_extraction",
]

BINS = [0, 1, 2, 3, 4]
BIN_NAMES = ["Easy", "Medium", "Hard", "Very Hard", "Hardest"]


def load_accuracy_data() -> pd.DataFrame:
    """Load accuracy data from capability curves"""
    curves_path = Path("analysis") / "average_capability_curves.csv"
    if curves_path.exists():
        return pd.read_csv(curves_path)
    return None


def compute_cost_benefit() -> pd.DataFrame:
    """
    Compute cost-benefit matrix for all models

    Returns: DataFrame with model, bin, accuracy, latency, cost metrics
    """
    accuracy_df = load_accuracy_data()
    if accuracy_df is None:
        print("[ERROR] Need to run compute_capability_curves.py first")
        return None

    results = []

    print("Computing cost-benefit analysis...")

    for _, row in accuracy_df.iterrows():
        model_name = row["model_name"]
        model_display = row["model_display"]
        bin_id = int(row["bin"])
        bin_name = row["bin_name"]
        accuracy = row["avg_accuracy"]

        if model_name not in MODEL_CONFIG:
            continue

        config = MODEL_CONFIG[model_name]

        # Cost metrics
        cost_per_1k = config["cost_per_1k"]
        latency_ms = row["avg_latency_ms"] if row["avg_latency_ms"] > 0 else config["latency_estimate_ms"]

        # Cost-benefit ratios
        if accuracy > 0:
            cost_per_accuracy_point = (cost_per_1k * 100) / (accuracy * 100) if accuracy > 0 else float('inf')
        else:
            cost_per_accuracy_point = 0

        quality_score = accuracy  # 0-1
        speed_score = 1.0 / (latency_ms / 10.0)  # normalized (higher latency = lower score)
        cost_score = 1.0 / (cost_per_1k + 0.01) if cost_per_1k > 0 else 1000  # lower cost = higher score

        # Weighted composite score (quality is most important)
        composite_score = (quality_score * 0.6) + (speed_score * 0.2) + (cost_score * 0.2)

        results.append({
            "model_name": model_name,
            "model_display": model_display,
            "model_params": config["params"],
            "model_type": config["type"],
            "bin": bin_id,
            "bin_name": bin_name,
            "accuracy": accuracy,
            "latency_ms": latency_ms,
            "cost_per_1k_tokens": cost_per_1k,
            "cost_per_accuracy_point": cost_per_accuracy_point,
            "quality_score": quality_score,
            "speed_score": speed_score,
            "cost_score": cost_score,
            "composite_score": composite_score,
        })

    df = pd.DataFrame(results)

    # Save detailed analysis
    cost_path = Path("analysis") / "cost_analysis.csv"
    cost_path.parent.mkdir(exist_ok=True)
    df.to_csv(cost_path, index=False)
    print(f"[OK] Saved: {cost_path}")

    return df


def compute_pareto_efficient_models(cost_df: pd.DataFrame) -> Dict:
    """
    Find Pareto-efficient models (no other model is better on all metrics)

    Returns: Dict with pareto-efficient model recommendations per bin
    """
    pareto = {}

    print("Computing Pareto-efficient frontiers...")

    for bin_id in BINS:
        bin_data = cost_df[cost_df["bin"] == bin_id].copy()
        bin_data = bin_data.sort_values("model_params")

        efficient_models = []

        for idx, row in bin_data.iterrows():
            is_efficient = True

            # Check if any other model is better on all dimensions
            for other_idx, other_row in bin_data.iterrows():
                if idx == other_idx:
                    continue

                # Better if: higher accuracy AND lower cost AND lower latency
                if (other_row["accuracy"] >= row["accuracy"] and
                    other_row["latency_ms"] <= row["latency_ms"] and
                    other_row["cost_per_1k_tokens"] <= row["cost_per_1k_tokens"] and
                    not (other_row["accuracy"] == row["accuracy"] and
                         other_row["latency_ms"] == row["latency_ms"] and
                         other_row["cost_per_1k_tokens"] == row["cost_per_1k_tokens"])):

                    is_efficient = False
                    break

            if is_efficient:
                efficient_models.append({
                    "model_name": row["model_display"],
                    "params": row["model_params"],
                    "accuracy": float(row["accuracy"]),
                    "latency_ms": float(row["latency_ms"]),
                    "cost_per_1k": float(row["cost_per_1k_tokens"]),
                    "composite_score": float(row["composite_score"]),
                })

        pareto[f"Bin {bin_id} ({BIN_NAMES[bin_id]})"] = efficient_models

    return pareto


def generate_cost_summary(cost_df: pd.DataFrame, pareto: Dict):
    """Generate human-readable cost-benefit summary"""

    summary_path = Path("analysis") / "COST_BENEFIT_SUMMARY.md"
    summary_path.parent.mkdir(exist_ok=True)

    with open(summary_path, "w") as f:
        f.write("# Cost-Benefit Analysis\n\n")

        f.write("## Cost per 1K Tokens (Pricing)\n\n")

        f.write("| Model | Type | $/1K Tokens | Cost per Accuracy Point |\n")
        f.write("|-------|------|-------------|------------------------|\n")

        for model_name in MODEL_CONFIG.keys():
            if model_name not in cost_df["model_name"].values:
                continue

            model_data = cost_df[cost_df["model_name"] == model_name].iloc[0]
            f.write(f"| {model_data['model_display']} | {model_data['model_type']} | "
                   f"${model_data['cost_per_1k_tokens']:.2f} | "
                   f"${model_data['cost_per_accuracy_point']:.4f} |\n")

        f.write("\n## Latency Comparison\n\n")

        f.write("| Model | Avg Latency (ms) | Tokens/sec |\n")
        f.write("|-------|-----------------|------------|\n")

        for model_name in MODEL_CONFIG.keys():
            if model_name not in cost_df["model_name"].values:
                continue

            config = MODEL_CONFIG[model_name]
            model_data = cost_df[cost_df["model_name"] == model_name].iloc[0]
            f.write(f"| {config['name']} | {model_data['latency_ms']:.1f} | "
                   f"{config['tokens_per_sec']:.0f} |\n")

        f.write("\n## Pareto-Efficient Models by Difficulty\n\n")

        for bin_name, efficient_models in pareto.items():
            f.write(f"### {bin_name}\n\n")

            f.write("Recommended models (best tradeoff):\n\n")

            for model in efficient_models:
                f.write(f"- **{model['model_name']} ({model['params']}B)**\n")
                f.write(f"  - Accuracy: {model['accuracy']:.1%}\n")
                f.write(f"  - Latency: {model['latency_ms']:.1f}ms\n")
                f.write(f"  - Cost: ${model['cost_per_1k']:.2f}/1K tokens\n")
                f.write(f"  - Score: {model['composite_score']:.2f}\n\n")

    print(f"[OK] Saved: {summary_path}")


def main():
    print("="*70)
    print("COST-BENEFIT ANALYSIS")
    print("="*70)

    # Load accuracy data
    cost_df = compute_cost_benefit()

    if cost_df is None or cost_df.empty:
        print("[ERROR] Failed to compute cost-benefit analysis")
        return 1

    # Compute Pareto frontier
    pareto = compute_pareto_efficient_models(cost_df)

    # Save Pareto analysis
    pareto_path = Path("analysis") / "pareto_frontier.json"
    pareto_path.parent.mkdir(exist_ok=True)
    with open(pareto_path, "w") as f:
        json.dump(pareto, f, indent=2)
    print(f"[OK] Saved: {pareto_path}")

    # Generate summary
    generate_cost_summary(cost_df, pareto)

    print("\n" + "="*70)
    print("COST-BENEFIT ANALYSIS COMPLETE")
    print("="*70)
    print("\nOutputs:")
    print("  - analysis/cost_analysis.csv")
    print("  - analysis/pareto_frontier.json")
    print("  - analysis/COST_BENEFIT_SUMMARY.md")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
