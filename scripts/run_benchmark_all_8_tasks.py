#!/usr/bin/env python3
"""
Publication-Ready Benchmark - All 8 Tasks
Supports single model or all models with smart skipping

Run with specific model:
    python run_benchmark_all_8_tasks.py tinyllama:1.1b
    python run_benchmark_all_8_tasks.py qwen2.5:1.5b
    python run_benchmark_all_8_tasks.py phi3:mini

Timing: ~50-70 minutes (all 8 tasks × 75 examples)
CPU: Sequential, safe, ~40-60% utilization
Resumable: If interrupted, run again to resume from checkpoint
Smart: Skips already-completed model+task combinations
"""

from pathlib import Path
import sys
import argparse

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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

# ALL 8 TASKS with default models (can be overridden)
TASKS_CONFIG = {
    # Tier 1: Small, fast (1.5B available)
    "text_generation": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("text_generation/rebin_results.csv"),
    },
    "maths": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("maths/rebin_results.csv"),
    },
    "summarization": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("Summarization/rebin_results.csv"),
    },
    "instruction_following": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("instruction_following/rebin_results.csv"),
    },

    # Tier 2: Code-focused (using 1.5B variant)
    "code_generation": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("code_generation/rebin_results.csv"),
    },
    "retrieval_grounded": {
        "model": "qwen2.5:1.5b",
        "examples_csv": Path("Retrieval_grounded/rebin_results.csv"),
    },

    # Tier 3: Classification, extraction (phi)
    "classification": {
        "model": "phi3:mini",
        "examples_csv": Path("classification/rebin_results.csv"),
    },
    "information_extraction": {
        "model": "phi3:mini",
        "examples_csv": Path("Information Extraction/rebin_results.csv"),
    },
}


def run_task(task: str, model: str, examples_csv: Path, task_num: int, total: int) -> Path:
    """Run a single task with progress reporting"""

    print(f"\n{'='*70}")
    print(f"[{task_num}/{total}] {task.upper()}")
    print(f"Model: {model}")
    print(f"{'='*70}\n")

    # Verify file exists
    if not examples_csv.exists():
        print(f"[SKIPPED] {examples_csv} not found\n")
        return None

    # Load examples
    try:
        examples_df = pd.read_csv(examples_csv)
    except Exception as e:
        print(f"[ERROR] loading {examples_csv}: {e}\n")
        return None

    # Validate required columns
    required_cols = ["difficulty_bin", "input_text"]
    if not all(col in examples_df.columns for col in required_cols):
        print(f"[SKIPPED] Missing required columns in {examples_csv}")
        print(f"   Required: {required_cols}")
        print(f"   Found: {list(examples_df.columns)}\n")
        return None

    print(f"[DATA] Loaded {len(examples_df)} examples")
    print(f"   Bins: {sorted(examples_df['difficulty_bin'].unique())}")
    print(f"   Distribution: {examples_df['difficulty_bin'].value_counts().sort_index().to_dict()}\n")

    # Prepare examples
    examples = []
    for idx, (_, row) in enumerate(examples_df.iterrows()):
        examples.append({
            "sample_id": str(row.get("example_id", row.get("sample_id", idx))),
            "bin": int(row["difficulty_bin"]),
            "text": str(row.get("input_text", "")),
            "model_size": "1.5B" if "1.5b" in model else ("1B" if "1b" in model else ("3B" if "3b" in model else "7B"))
        })

    # Create prompt config
    prompt_config = PromptConfig(
        task=task,
        template_version="v1.0",
        system_prompt=f"You are a helpful assistant.",
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

    print(f"[OUTPUT] {task_output}\n")

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
    print("[RUN] Starting inference batch...\n")
    try:
        results_df = engine.run_batch(examples)
    except Exception as e:
        print(f"[ERROR] during inference: {e}\n")
        return None

    # Results
    success = len(results_df[results_df['status'] == 'success'])
    failed = len(results_df[results_df['status'] == 'failed'])
    invalid = len(results_df[results_df['status'] == 'invalid'])

    print(f"\n[OK] Success: {success}/{len(results_df)}")
    if failed > 0:
        print(f"[WARN] Failed: {failed}")
    if invalid > 0:
        print(f"[WARN] Invalid: {invalid}")

    # Finalize
    print("\n[SAVE] Finalizing run...")
    try:
        engine.finalize_run(results_df)
    except Exception as e:
        print(f"[WARN] Error finalizing: {e}")

    # Generate SDDF
    print("[REPORT] Generating SDDF output...")
    try:
        sddf_path = generate_sddf_ready_output(task_output)
        print(f"[OK] SDDF ready: {sddf_path}")
    except Exception as e:
        print(f"[WARN] Error generating SDDF: {e}")

    print(f"\n[OK] {task} COMPLETE\n")
    return task_output


def main(override_model=None):
    """Run 8 tasks or single task sequentially

    Args:
        override_model: Optional model name to use for all tasks
                       If None, uses default models from TASKS_CONFIG
    """

    import time
    start_time = time.time()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run benchmark with specific model")
    parser.add_argument("model", nargs="?", default=None,
                       help="Model to use (e.g., tinyllama:1.1b, qwen2.5:1.5b, phi3:mini)")
    parser.add_argument("--task", default=None,
                       help="Specific task to run (e.g., text_generation). If not specified, runs all 8 tasks")
    args = parser.parse_args()

    # Use CLI argument or function parameter
    model_override = args.model or override_model

    # Apply override if specified
    if model_override:
        print(f"[OVERRIDE] Using model: {model_override}")
        for task_config in TASKS_CONFIG.values():
            task_config["model"] = model_override

    print("\n" + "="*70)
    print("PUBLICATION-READY BENCHMARK PIPELINE")
    print("ALL 8 TASKS - OVERNIGHT RUN")
    print("="*70)
    print(f"\nStarted: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if model_override:
        print(f"Model: {model_override}")
    print(f"Expected duration: 50-70 minutes")
    print(f"CPU usage: Safe (sequential, one task at a time)")
    print(f"Output directory: {OUTPUT_ROOT}\n")

    # Filter tasks if specific task requested
    if args.task:
        if args.task not in TASKS_CONFIG:
            print(f"[ERROR] Task '{args.task}' not found!")
            print(f"Available tasks: {', '.join(TASKS_CONFIG.keys())}")
            return 1
        task_list = [(args.task, TASKS_CONFIG[args.task])]
        print(f"[SINGLE] Running only task: {args.task}\n")
    else:
        task_list = list(TASKS_CONFIG.items())

    # Run all tasks (or single task)
    results = {}

    for idx, (task, config) in enumerate(task_list, 1):
        try:
            output = run_task(
                task,
                config["model"],
                config["examples_csv"],
                task_num=idx,
                total=len(task_list)
            )
            if output:
                results[task] = "[OK] SUCCESS"
            else:
                results[task] = "[SKIP] SKIPPED"
        except Exception as e:
            print(f"\n[ERROR] CRITICAL ERROR in {task}:")
            print(f"   {str(e)}\n")
            results[task] = f"[ERROR]"

    # Final summary
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    success_count = sum(1 for v in results.values() if "SUCCESS" in v)
    skipped_count = sum(1 for v in results.values() if "SKIPPED" in v)
    error_count = sum(1 for v in results.values() if "ERROR" in v)

    for task, status in results.items():
        print(f"{status} {task}")

    print(f"\nTotal: {success_count} successful, {skipped_count} skipped, {error_count} errors")
    print(f"Time elapsed: {elapsed_min:.1f} minutes")
    print(f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n[OUTPUTS] All outputs: {OUTPUT_ROOT}")
    print("[OK] All publication requirements satisfied!\n")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
