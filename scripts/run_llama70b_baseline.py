#!/usr/bin/env python3
"""
Large LLM Baseline - Llama 3.3 70B via Groq
Runs Llama 3.3 70B on the same 75 queries per task
Enables SLM vs Large LLM comparison (0.5B, 1.5B, 3.8B vs 70B)

Usage:
    python scripts/run_llama70b_baseline.py
    python scripts/run_llama70b_baseline.py --task text_generation
    python scripts/run_llama70b_baseline.py --verbose

Expected time: ~15-20 minutes (cloud-based, optimized for large models)
"""

from pathlib import Path
import sys
import argparse
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark_inference_pipeline import (
    BenchmarkInferenceEngine,
    DatasetManifest,
    PromptConfig,
    generate_sddf_ready_output,
)
import pandas as pd
import os

# Configuration
OUTPUT_ROOT = Path("./benchmark_output")
BACKEND = "groq"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Large LLM baseline

# Same 8 tasks as SLM benchmark
TASKS_CONFIG = {
    "text_generation": {
        "examples_csv": Path("text_generation/rebin_results.csv"),
    },
    "code_generation": {
        "examples_csv": Path("code_generation/rebin_results.csv"),
    },
    "classification": {
        "examples_csv": Path("classification/rebin_results.csv"),
    },
    "maths": {
        "examples_csv": Path("maths/rebin_results.csv"),
    },
    "summarization": {
        "examples_csv": Path("Summarization/rebin_results.csv"),
    },
    "retrieval_grounded": {
        "examples_csv": Path("Retrieval_grounded/rebin_results.csv"),
    },
    "instruction_following": {
        "examples_csv": Path("instruction_following/rebin_results.csv"),
    },
    "information_extraction": {
        "examples_csv": Path("Information Extraction/rebin_results.csv"),
    },
}


def run_task(task: str, examples_csv: Path, task_num: int, total: int) -> Path:
    """Run single task with Llama 70B model"""

    print(f"\n{'='*70}")
    print(f"[{task_num}/{total}] {task.upper()}")
    print(f"Model: {GROQ_MODEL}")
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
            "model_size": "70B"
        })

    # Create prompt config
    prompt_config = PromptConfig(
        task=task,
        template_version="v1.0",
        system_prompt="You are a helpful assistant.",
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
    task_output = OUTPUT_ROOT / task / f"llama_{GROQ_MODEL.split('/')[-1].replace('/', '_').replace(':', '_')}"
    task_output.mkdir(parents=True, exist_ok=True)

    print(f"[OUTPUT] {task_output}\n")

    # Verify API key is set
    if not os.getenv("GROQ_API_KEY"):
        print("[ERROR] GROQ_API_KEY environment variable not set\n")
        return None

    # Create engine
    engine = BenchmarkInferenceEngine(
        task=task,
        model_name=GROQ_MODEL,
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


def main():
    """Run Llama 70B baseline on all 8 tasks"""

    start_time = time.time()

    # Parse arguments
    parser = argparse.ArgumentParser(description="Run Llama 70B large LLM baseline")
    parser.add_argument("--task", default=None,
                       help="Specific task to run (e.g., text_generation)")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("LLAMA 3.3 70B - LARGE LLM BASELINE")
    print("="*70)
    print(f"\nStarted: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {GROQ_MODEL}")
    print(f"Backend: {BACKEND}")
    print(f"Tier: Large LLM (70B parameters)")
    print(f"Expected duration: 15-20 minutes")
    print(f"Output directory: {OUTPUT_ROOT}\n")

    # Verify API key
    if not os.getenv("GROQ_API_KEY"):
        print("[ERROR] GROQ_API_KEY environment variable not set!")
        print("[ERROR] Set it with: export GROQ_API_KEY='your-key'")
        return 1

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

    # Run all tasks
    results = {}

    for idx, (task, config) in enumerate(task_list, 1):
        try:
            output = run_task(
                task,
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
            results[task] = "[ERROR]"

    # Final summary
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60

    print("\n" + "="*70)
    print("LLAMA 70B BASELINE COMPLETE")
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
    print("[OK] Llama 70B baseline complete! Ready for SLM vs LLM comparison.\n")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
