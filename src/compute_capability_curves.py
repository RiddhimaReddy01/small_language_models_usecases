#!/usr/bin/env python3
"""
Compute Capability Curves - Model Scaling Analysis
Analyzes how accuracy improves with model size across difficulty bins
Generates: capability_curves.csv, tipping_points.json
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# Model metadata (size in billions, type)
MODEL_SIZES = {
    "tinyllama_1.1b": {"params": 0.5, "name": "TinyLLaMA", "type": "SLM"},
    "qwen2.5_1.5b": {"params": 1.5, "name": "Qwen2.5", "type": "SLM"},
    "phi3_mini": {"params": 3.8, "name": "Phi-3", "type": "SLM"},
    "groq_mixtral-8x7b-32768": {"params": 45, "name": "Mixtral-8x7B", "type": "Medium"},
    "llama_llama-3.3-70b-versatile": {"params": 70, "name": "Llama-3.3-70B", "type": "LLM"},
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


def load_sddf_data(task: str, model_dir: str) -> pd.DataFrame:
    """Load SDDF data for a task/model combination"""
    sddf_path = Path("benchmark_output") / task / model_dir / "sddf_ready.csv"
    if sddf_path.exists():
        return pd.read_csv(sddf_path)
    return None


def extract_model_name(model_dir: str) -> str:
    """Extract canonical model name from directory"""
    for key in MODEL_SIZES.keys():
        if key in model_dir:
            return key
    return None


def compute_capability_curves() -> pd.DataFrame:
    """
    Compute capability curves: accuracy by model size per bin

    Returns: DataFrame with columns:
      - task, bin, model_name, model_params, accuracy
    """
    results = []

    print("Computing capability curves...")

    for task in TASKS:
        task_path = Path("benchmark_output") / task
        if not task_path.exists():
            continue

        for model_dir in task_path.iterdir():
            if not model_dir.is_dir():
                continue

            model_name = extract_model_name(model_dir.name)
            if not model_name or model_name not in MODEL_SIZES:
                continue

            sddf_df = load_sddf_data(task, model_dir.name)
            if sddf_df is None:
                continue

            # Extract accuracy per bin
            for _, row in sddf_df.iterrows():
                bin_id = int(row["bin"])
                accuracy = row["success_rate"]

                results.append({
                    "task": task,
                    "bin": bin_id,
                    "bin_name": BIN_NAMES[bin_id],
                    "model_dir": model_dir.name,
                    "model_name": model_name,
                    "model_display": MODEL_SIZES[model_name]["name"],
                    "model_params": MODEL_SIZES[model_name]["params"],
                    "model_type": MODEL_SIZES[model_name]["type"],
                    "accuracy": accuracy,
                    "latency_ms": row["avg_latency"] * 1000 if row["avg_latency"] > 0 else 0,
                })

    df = pd.DataFrame(results)

    # Save detailed curves
    curves_path = Path("analysis") / "capability_curves.csv"
    curves_path.parent.mkdir(exist_ok=True)
    df.to_csv(curves_path, index=False)
    print(f"[OK] Saved: {curves_path}")

    return df


def compute_tipping_points(curves_df: pd.DataFrame, threshold: float = 0.5) -> Dict:
    """
    Find tipping points: where accuracy drops below threshold

    Args:
        curves_df: Capability curves dataframe
        threshold: Accuracy threshold (default 50%)

    Returns: Dict mapping model → {task → tipping_bin}
    """
    tipping_points = {}

    print(f"\nComputing tipping points (threshold: {threshold*100}%)...")

    for model_name in MODEL_SIZES.keys():
        model_data = curves_df[curves_df["model_name"] == model_name]
        if model_data.empty:
            continue

        tipping_points[model_name] = {}

        for task in TASKS:
            task_data = model_data[model_data["task"] == task].sort_values("bin")
            if task_data.empty:
                continue

            # Find first bin where accuracy drops below threshold
            tipping_bin = None
            for _, row in task_data.iterrows():
                if row["accuracy"] < threshold:
                    tipping_bin = int(row["bin"])
                    break

            if tipping_bin is not None:
                tipping_points[model_name][task] = {
                    "tipping_bin": tipping_bin,
                    "bin_name": BIN_NAMES[tipping_bin],
                    "accuracy_at_threshold": float(task_data[task_data["bin"] == tipping_bin]["accuracy"].values[0])
                }
            else:
                tipping_points[model_name][task] = {
                    "tipping_bin": None,
                    "bin_name": "No tipping point",
                    "note": "Model handles all difficulty levels above threshold"
                }

    return tipping_points


def compute_average_curves(curves_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute average accuracy across all tasks per model/bin

    Returns: DataFrame with average accuracy by model and bin
    """
    avg_curves = curves_df.groupby(["model_name", "model_display", "model_params", "bin", "bin_name"]).agg({
        "accuracy": ["mean", "std", "min", "max"],
        "latency_ms": "mean"
    }).reset_index()

    avg_curves.columns = ["model_name", "model_display", "model_params", "bin", "bin_name",
                          "avg_accuracy", "std_accuracy", "min_accuracy", "max_accuracy", "avg_latency_ms"]

    # Sort by params and bin
    avg_curves = avg_curves.sort_values(["model_params", "bin"])

    avg_path = Path("analysis") / "average_capability_curves.csv"
    avg_path.parent.mkdir(exist_ok=True)
    avg_curves.to_csv(avg_path, index=False)
    print(f"[OK] Saved: {avg_path}")

    return avg_curves


def generate_capability_summary(curves_df: pd.DataFrame, avg_curves_df: pd.DataFrame, tipping_points: Dict):
    """Generate human-readable summary"""

    summary_path = Path("analysis") / "CAPABILITY_CURVES_SUMMARY.md"
    summary_path.parent.mkdir(exist_ok=True)

    with open(summary_path, "w") as f:
        f.write("# Capability Curves Analysis\n\n")

        f.write("## Model Scaling by Difficulty Bin\n\n")

        for bin_id in BINS:
            bin_name = BIN_NAMES[bin_id]
            f.write(f"### Bin {bin_id}: {bin_name}\n\n")

            bin_data = avg_curves_df[avg_curves_df["bin"] == bin_id].sort_values("model_params")

            f.write("| Model | Size | Accuracy | Variance | Latency (ms) |\n")
            f.write("|-------|------|----------|----------|---------------|\n")

            for _, row in bin_data.iterrows():
                f.write(f"| {row['model_display']} | {row['model_params']}B | "
                       f"{row['avg_accuracy']:.1%} | ±{row['std_accuracy']:.1%} | "
                       f"{row['avg_latency_ms']:.0f} |\n")

            f.write("\n")

        f.write("## Tipping Points by Model\n\n")

        for model_name in sorted(MODEL_SIZES.keys()):
            if model_name not in tipping_points:
                continue

            model_display = MODEL_SIZES[model_name]["name"]
            f.write(f"### {model_display} ({MODEL_SIZES[model_name]['params']}B)\n\n")

            f.write("| Task | Tipping Bin | Accuracy at Threshold |\n")
            f.write("|------|-------------|----------------------|\n")

            for task in TASKS:
                if task not in tipping_points[model_name]:
                    continue

                tp = tipping_points[model_name][task]
                if tp["tipping_bin"] is not None:
                    f.write(f"| {task} | {tp['bin_name']} | {tp['accuracy_at_threshold']:.1%} |\n")
                else:
                    f.write(f"| {task} | No tipping | No tipping point |\n")

            f.write("\n")

    print(f"[OK] Saved: {summary_path}")


def main():
    print("="*70)
    print("CAPABILITY CURVES ANALYSIS")
    print("="*70)

    # Compute curves
    curves_df = compute_capability_curves()

    if curves_df.empty:
        print("[ERROR] No capability curve data found")
        return 1

    # Compute average curves
    avg_curves_df = compute_average_curves(curves_df)

    # Compute tipping points
    tipping_points = compute_tipping_points(curves_df, threshold=0.5)

    # Save tipping points
    tp_path = Path("analysis") / "tipping_points.json"
    tp_path.parent.mkdir(exist_ok=True)
    with open(tp_path, "w") as f:
        json.dump(tipping_points, f, indent=2)
    print(f"[OK] Saved: {tp_path}")

    # Generate summary
    generate_capability_summary(curves_df, avg_curves_df, tipping_points)

    print("\n" + "="*70)
    print("CAPABILITY CURVES COMPLETE")
    print("="*70)
    print("\nOutputs:")
    print("  - analysis/capability_curves.csv")
    print("  - analysis/average_capability_curves.csv")
    print("  - analysis/tipping_points.json")
    print("  - analysis/CAPABILITY_CURVES_SUMMARY.md")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
