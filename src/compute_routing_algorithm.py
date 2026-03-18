#!/usr/bin/env python3
"""
Compute Routing Algorithm
Generates decision rules for dynamic model selection based on difficulty
Generates: routing_policy.json, routing_validation.csv
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List

MODEL_CONFIG = {
    "tinyllama_1.1b": {"name": "TinyLLaMA", "params": 0.5, "type": "SLM"},
    "qwen2.5_1.5b": {"name": "Qwen2.5", "params": 1.5, "type": "SLM"},
    "phi3_mini": {"name": "Phi-3", "params": 3.8, "type": "SLM"},
    "groq_mixtral-8x7b-32768": {"name": "Mixtral-8x7B", "params": 45, "type": "Medium"},
    "llama_llama-3.3-70b-versatile": {"name": "Llama-3.3-70B", "params": 70, "type": "LLM"},
}

BINS = [0, 1, 2, 3, 4]
BIN_NAMES = ["Easy", "Medium", "Hard", "Very Hard", "Hardest"]

# Routing thresholds: minimum acceptable accuracy by tier
ACCURACY_THRESHOLDS = {
    "fast_tier": 0.75,    # Fast/cheap (local CPU)
    "balanced_tier": 0.85,  # Balanced (medium cloud)
    "premium_tier": 0.95,   # Best quality (large LLM)
}


def load_capability_data() -> pd.DataFrame:
    """Load capability curve data"""
    curves_path = Path("analysis") / "average_capability_curves.csv"
    if curves_path.exists():
        return pd.read_csv(curves_path)
    return None


def load_cost_data() -> pd.DataFrame:
    """Load cost data"""
    cost_path = Path("analysis") / "cost_analysis.csv"
    if cost_path.exists():
        return pd.read_csv(cost_path)
    return None


def select_model_for_bin(bin_id: int, curves_df: pd.DataFrame, cost_df: pd.DataFrame) -> Dict:
    """
    Select best model for a given difficulty bin

    Uses multi-criteria decision making:
    1. Accuracy (must meet threshold)
    2. Cost (prefer cheaper)
    3. Latency (prefer faster)
    """
    bin_data = curves_df[curves_df["bin"] == bin_id].sort_values("model_params")

    # Tier 1: Can we use fast/cheap tier?
    fast_models = bin_data[bin_data["avg_accuracy"] >= ACCURACY_THRESHOLDS["fast_tier"]]
    if not fast_models.empty:
        # Prefer fastest within accuracy threshold
        return {
            "tier": "fast",
            "model": fast_models.iloc[0]["model_display"],
            "params": float(fast_models.iloc[0]["model_params"]),
            "accuracy": float(fast_models.iloc[0]["avg_accuracy"]),
            "rationale": "Accuracy meets fast-tier threshold; using cheapest/fastest option",
        }

    # Tier 2: Use balanced tier
    balanced_models = bin_data[bin_data["avg_accuracy"] >= ACCURACY_THRESHOLDS["balanced_tier"]]
    if not balanced_models.empty:
        return {
            "tier": "balanced",
            "model": balanced_models.iloc[0]["model_display"],
            "params": float(balanced_models.iloc[0]["model_params"]),
            "accuracy": float(balanced_models.iloc[0]["avg_accuracy"]),
            "rationale": "Accuracy meets balanced-tier threshold; good cost-benefit",
        }

    # Tier 3: Use premium tier (best available)
    best_model = bin_data.iloc[-1]  # Largest model
    return {
        "tier": "premium",
        "model": best_model["model_display"],
        "params": float(best_model["model_params"]),
        "accuracy": float(best_model["avg_accuracy"]),
        "rationale": "Using largest model for maximum quality",
    }


def compute_routing_policy() -> Dict:
    """
    Compute optimal routing policy for all difficulty bins

    Returns: Dict with routing decisions per bin
    """
    curves_df = load_capability_data()
    cost_df = load_cost_data()

    if curves_df is None or cost_df is None:
        print("[ERROR] Need to run capability and cost analysis first")
        return None

    print("Computing routing policy...")

    routing_policy = {
        "policy_name": "Difficulty-Based Dynamic Routing",
        "description": "Routes queries to models based on detected difficulty and accuracy thresholds",
        "tiers": {
            "fast": {
                "name": "Fast/Cheap",
                "min_accuracy": ACCURACY_THRESHOLDS["fast_tier"],
                "examples": ["Local CPU SLMs"],
            },
            "balanced": {
                "name": "Balanced",
                "min_accuracy": ACCURACY_THRESHOLDS["balanced_tier"],
                "examples": ["Medium cloud models"],
            },
            "premium": {
                "name": "Premium",
                "min_accuracy": ACCURACY_THRESHOLDS["premium_tier"],
                "examples": ["Large LLMs"],
            },
        },
        "routing_decisions": {},
    }

    # Compute decisions per bin
    for bin_id in BINS:
        bin_name = BIN_NAMES[bin_id]
        decision = select_model_for_bin(bin_id, curves_df, cost_df)

        routing_policy["routing_decisions"][f"Bin {bin_id} ({bin_name})"] = decision

    return routing_policy


def compute_routing_validation(curves_df: pd.DataFrame, cost_df: pd.DataFrame, routing_policy: Dict) -> pd.DataFrame:
    """
    Validate routing policy: How well would it work?

    Metrics:
    - Accuracy achieved
    - Cost saved
    - Latency impact
    """
    results = []

    print("Validating routing policy...")

    for bin_name, decision in routing_policy["routing_decisions"].items():
        model_name = decision["model"]

        # Find this model's metrics
        model_data = curves_df[curves_df["model_display"] == model_name]
        cost_model_data = cost_df[cost_df["model_display"] == model_name]

        if model_data.empty or cost_model_data.empty:
            continue

        bin_id = int(bin_name.split()[1])

        model_row = model_data[model_data["bin"] == bin_id].iloc[0]
        cost_row = cost_model_data[cost_model_data["bin"] == bin_id].iloc[0]

        # Compare to best available (largest model)
        best_model_data = curves_df[curves_df["bin"] == bin_id].iloc[-1]
        best_cost_data = cost_df[cost_df["bin"] == bin_id].iloc[-1]

        accuracy_gap = best_model_data["avg_accuracy"] - model_row["avg_accuracy"]
        cost_ratio = best_cost_data["cost_per_1k_tokens"] / (cost_row["cost_per_1k_tokens"] + 0.01)
        latency_ratio = model_row["avg_latency_ms"] / (best_model_data["avg_latency_ms"] + 0.01)

        results.append({
            "bin": bin_id,
            "bin_name": BIN_NAMES[bin_id],
            "selected_model": model_name,
            "selected_params": decision["params"],
            "tier": decision["tier"],
            "accuracy_achieved": model_row["avg_accuracy"],
            "accuracy_vs_best": accuracy_gap,
            "cost_per_1k": cost_row["cost_per_1k_tokens"],
            "cost_savings_factor": cost_ratio,
            "latency_ms": model_row["avg_latency_ms"],
            "latency_ratio_to_best": latency_ratio,
            "efficiency_score": (1 - accuracy_gap) * (1 / latency_ratio) * cost_ratio,
        })

    df = pd.DataFrame(results)

    # Save validation
    val_path = Path("analysis") / "routing_validation.csv"
    val_path.parent.mkdir(exist_ok=True)
    df.to_csv(val_path, index=False)
    print(f"[OK] Saved: {val_path}")

    return df


def generate_routing_summary(routing_policy: Dict, validation_df: pd.DataFrame):
    """Generate human-readable routing policy summary"""

    summary_path = Path("analysis") / "ROUTING_POLICY_SUMMARY.md"
    summary_path.parent.mkdir(exist_ok=True)

    with open(summary_path, "w") as f:
        f.write("# Dynamic Routing Policy\n\n")

        f.write("## Policy Overview\n\n")
        f.write(f"**Policy Name**: {routing_policy['policy_name']}\n\n")
        f.write(f"{routing_policy['description']}\n\n")

        f.write("## Tier Definitions\n\n")

        for tier_name, tier_info in routing_policy["tiers"].items():
            f.write(f"### {tier_name.upper()}: {tier_info['name']}\n\n")
            f.write(f"- **Minimum Accuracy**: {tier_info['min_accuracy']:.0%}\n")
            f.write(f"- **Use Cases**: {', '.join(tier_info['examples'])}\n\n")

        f.write("---\n\n")

        f.write("## Routing Decisions\n\n")

        f.write("| Difficulty | Model | Size | Accuracy | Tier | Rationale |\n")
        f.write("|------------|-------|------|----------|------|----------|\n")

        for bin_name, decision in routing_policy["routing_decisions"].items():
            f.write(f"| {bin_name} | {decision['model']} | {decision['params']}B | "
                   f"{decision['accuracy']:.1%} | {decision['tier'].upper()} | "
                   f"{decision['rationale']} |\n")

        f.write("\n## Validation Results\n\n")

        if validation_df is not None and not validation_df.empty:
            f.write("### Accuracy vs Cost Tradeoff\n\n")
            f.write("| Bin | Model | Accuracy | Gap vs Best | Cost Savings |\n")
            f.write("|-----|-------|----------|-------------|---------------|\n")

            for _, row in validation_df.iterrows():
                f.write(f"| {row['bin_name']} | {row['selected_model']} | "
                       f"{row['accuracy_achieved']:.1%} | {row['accuracy_vs_best']:.1%} | "
                       f"{row['cost_savings_factor']:.1f}x |\n")

            f.write("\n")

        f.write("---\n\n")

        f.write("## Pseudocode\n\n")

        f.write("```python\ndef route_query(detected_difficulty_bin):\n")
        f.write("    \"\"\"Route a query to appropriate model based on difficulty\"\"\"\n\n")

        for bin_name_str, decision in routing_policy["routing_decisions"].items():
            # Extract bin number from "Bin N (Name)" format
            bin_id = bin_name_str.split()[1]
            f.write(f"    if detected_difficulty_bin == {bin_id}:\n")
            f.write(f"        return MODEL['{decision['model']}']\n")

        f.write("```\n\n")

    print(f"[OK] Saved: {summary_path}")


def main():
    print("="*70)
    print("ROUTING ALGORITHM COMPUTATION")
    print("="*70)

    # Compute routing policy
    routing_policy = compute_routing_policy()

    if not routing_policy:
        print("[ERROR] Failed to compute routing policy")
        return 1

    # Load data for validation
    curves_df = load_capability_data()
    cost_df = load_cost_data()

    if curves_df is None or cost_df is None:
        print("[ERROR] Missing capability or cost data")
        return 1

    # Validate policy
    validation_df = compute_routing_validation(curves_df, cost_df, routing_policy)

    # Save routing policy
    policy_path = Path("analysis") / "routing_policy.json"
    policy_path.parent.mkdir(exist_ok=True)
    with open(policy_path, "w") as f:
        json.dump(routing_policy, f, indent=2)
    print(f"[OK] Saved: {policy_path}")

    # Generate summary
    generate_routing_summary(routing_policy, validation_df)

    print("\n" + "="*70)
    print("ROUTING ALGORITHM COMPLETE")
    print("="*70)
    print("\nOutputs:")
    print("  - analysis/routing_policy.json")
    print("  - analysis/routing_validation.csv")
    print("  - analysis/ROUTING_POLICY_SUMMARY.md")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
