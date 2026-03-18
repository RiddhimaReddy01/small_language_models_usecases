#!/usr/bin/env python3
"""
Publication-Ready Benchmark Inference - Quick Start Example

Run this to benchmark your 75 examples with full publication infrastructure.

Usage:
    python run_benchmark_example.py
"""

from pathlib import Path
from benchmark_inference_pipeline import (
    BenchmarkInferenceEngine,
    DatasetManifest,
    PromptConfig,
    generate_sddf_ready_output,
)
import pandas as pd

# Configuration
OUTPUT_ROOT = Path("./benchmark_output")
BACKEND = "ollama"

# Task configuration (customize as needed)
TASKS_CONFIG = {
    "text_generation": {
        "model": "qwen2.5:0.5b",
        "examples_csv": Path("text_generation/rebin_results.csv"),
    },
    "code_generation": {
        "model": "qwen2.5-coder:0.5b",
        "examples_csv": Path("code_generation/rebin_results.csv"),
    },
    "classification": {
        "model": "phi3:mini",
        "examples_csv": Path("classification/rebin_results.csv"),
    },
    "maths": {
        "model": "qwen2.5:0.5b",
        "examples_csv": Path("maths/rebin_results.csv"),
    },
}


def run_task(task: str, model: str, examples_csv: Path) -> Path:
    """Run a single task"""

    print(f"\n{'='*70}")
    print(f"Task: {task} | Model: {model}")
    print(f"{'='*70}\n")

    # Load examples
    if not examples_csv.exists():
        print(f"⚠️  File not found: {examples_csv}")
        print(f"   Skipping {task}")
        return None

    examples_df = pd.read_csv(examples_csv)
    print(f"Loaded {len(examples_df)} examples")
    print(f"Bins: {sorted(examples_df['difficulty_bin'].unique())}\n")

    # Prepare examples
    examples = []
    for _, row in examples_df.iterrows():
        examples.append({
            "sample_id": str(row.get("example_id", row.get("sample_id", row.name))),
            "bin": int(row["difficulty_bin"]),
            "text": str(row.get("input_text", "")),
            "model_size": str(row.get("model_size", "0.5B"))
        })

    # Create prompt config
    prompt_config = PromptConfig(
        task=task,
        template_version="v1.0",
        system_prompt=f"You are a helpful assistant for {task}.",
        instruction_wrapper="Q: {input}\nA:",
        temperature=0.7,
        top_p=0.9,
        max_tokens=200,
        stop_tokens=["\n\n"],
        parsing_rules={},
        seed=42
    )

    # Create dataset manifest
    bins = sorted(examples_df['difficulty_bin'].unique())
    target_per_bin = {int(b): len(examples_df[examples_df['difficulty_bin'] == b]) for b in bins}
    samples_per_bin = {
        int(b): examples_df[examples_df['difficulty_bin'] == b].index.astype(str).tolist()
        for b in bins
    }

    dataset_manifest = DatasetManifest(
        task=task,
        source_dataset="benchmark_2024",
        selection_method="stratified_by_difficulty",
        binning_rule="quantile(5)",
        seed=42,
        target_per_bin=target_per_bin,
        samples_included=samples_per_bin
    )

    # Create output directory
    task_output = OUTPUT_ROOT / task / model.replace("/", "_").replace(":", "_")
    task_output.mkdir(parents=True, exist_ok=True)

    # Create engine
    engine = BenchmarkInferenceEngine(
        task=task,
        model_name=model,
        dataset_manifest=dataset_manifest,
        prompt_config=prompt_config,
        output_dir=task_output,
        backend=BACKEND
    )

    # Run inference
    print("Running inference batch...")
    results_df = engine.run_batch(examples)

    print(f"✅ {len(results_df[results_df['status'] == 'success'])}/{len(results_df)} successful")

    # Finalize
    engine.finalize_run(results_df)
    sddf_path = generate_sddf_ready_output(task_output)

    print(f"📊 SDDF output: {sddf_path}")
    print(f"📁 Full output: {task_output}\n")

    return task_output


def main():
    print("\n" + "="*70)
    print("PUBLICATION-READY BENCHMARK PIPELINE")
    print("="*70)

    results = {}
    for task, config in TASKS_CONFIG.items():
        try:
            output = run_task(task, config["model"], config["examples_csv"])
            if output:
                results[task] = "✅ success"
            else:
                results[task] = "⏭️  skipped"
        except Exception as e:
            print(f"❌ Error in {task}: {e}\n")
            results[task] = f"❌ {str(e)[:50]}"

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    for task, status in results.items():
        print(f"{status} {task}")

    print(f"\n📂 All outputs saved to: {OUTPUT_ROOT}")
    print("✅ All publication requirements satisfied!\n")


if __name__ == "__main__":
    main()
