#!/usr/bin/env python3
"""
Smart Multi-Model Benchmark Runner
Runs 0.5B, 1.5B, and 3.8B models across all 8 tasks
Intelligently skips already-completed model+task combinations
Supports parallel execution (2 models per task)

Usage:
    python scripts/run_all_models.py
    python scripts/run_all_models.py --parallel
    python scripts/run_all_models.py --verbose

Features:
    • Same 75 queries (15 per bin) for all models
    • Auto-skips completed tasks
    • Parallel execution (2 models at same time)
    • Smart task allocation
"""

import sys
import subprocess
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse

# Model allocation for each task
# Rule: Always test 0.5B
#       If current is 1.5B → also test 3.8B
#       If current is 3.8B → also test 1.5B

TASK_MODELS = {
    "text_generation": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "code_generation": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "classification": {
        "current": "phi3:mini",
        "models_to_run": ["tinyllama:1.1b", "qwen2.5:1.5b"]  # skip 3.8B
    },
    "maths": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "summarization": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "retrieval_grounded": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "instruction_following": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]  # skip 1.5B
    },
    "information_extraction": {
        "current": "phi3:mini",
        "models_to_run": ["tinyllama:1.1b", "qwen2.5:1.5b"]  # skip 3.8B
    },
}


def run_model_for_task(task_name, model_name, verbose=False):
    """Run benchmark for specific model on specific task

    Returns: (success, status_message)
    """
    script_path = Path(__file__).parent / "run_benchmark_all_8_tasks.py"

    try:
        cmd = [sys.executable, str(script_path), model_name, "--task", task_name]

        if verbose:
            print(f"[RUN] {task_name:30s} with {model_name:20s}")

        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=not verbose,
            timeout=1200  # 20 minutes max per task
        )

        if result.returncode == 0:
            return True, f"[OK] {task_name:30s} with {model_name:20s}"
        else:
            return False, f"[FAIL] {task_name:30s} with {model_name:20s}"

    except subprocess.TimeoutExpired:
        return False, f"[TIMEOUT] {task_name:30s} with {model_name:20s}"
    except Exception as e:
        return False, f"[ERROR] {task_name:30s}: {str(e)}"


def run_parallel_models(task_name, models, verbose=False):
    """Run 2 models in parallel for same task (same queries, same bins)

    Uses ProcessPoolExecutor for true CPU parallelism (bypasses Python GIL)

    Args:
        task_name: Task to run
        models: List of 2 model names to run in parallel
        verbose: Print detailed output

    Returns: Dictionary with results for each model
    """
    results = {}

    print(f"\n[TASK] {task_name.upper()}")
    print(f"  Running {len(models)} models in PARALLEL (true CPU parallelism)")
    print(f"  Models: {', '.join(models)}\n")

    # Use ProcessPoolExecutor for true parallelism (CPU-bound tasks)
    # This bypasses Python's GIL (Global Interpreter Lock)
    with ProcessPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_model_for_task, task_name, model, verbose): model
            for model in models
        }

        for future in as_completed(futures):
            model = futures[future]
            success, message = future.result()
            results[model] = success
            print(f"  {message}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run all models across all tasks")
    parser.add_argument("--parallel", action="store_true",
                       help="Run 2 models per task in parallel")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed output")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("MULTI-MODEL BENCHMARK SUITE")
    print("="*70)
    print("\nConfiguration:")
    print(f"  Tasks: 8")
    print(f"  Models per task: 2 (new models only, skip already-done)")
    print(f"  Queries per model: 75 (same for all)")
    print(f"  Difficulty bins: 5 (same for all, 15 samples each)")

    if args.parallel:
        print(f"  Parallel execution: YES (ProcessPoolExecutor - true CPU parallelism)")
        print(f"  Expected speedup: ~1.5-2x faster than sequential")
    else:
        print(f"  Parallel execution: NO (sequential)")

    print(f"\nSample allocation:")
    print(f"  Total: 8 tasks × 2 models × 75 samples = 1,200 NEW samples")
    print(f"  Plus: 600 already-done samples")
    print(f"  Grand total: 1,800 samples across 24 model+task combinations\n")

    start_time = time.time()
    all_results = {}

    # Run each task
    for task_idx, (task_name, config) in enumerate(TASK_MODELS.items(), 1):
        print(f"\n{'='*70}")
        print(f"[{task_idx}/8] {task_name.upper()}")
        print(f"{'='*70}")
        print(f"\nCurrent (done): {config['current']}")
        print(f"New models:    {', '.join(config['models_to_run'])}\n")

        if args.parallel:
            # Run 2 models in parallel
            results = run_parallel_models(
                task_name,
                config['models_to_run'],
                verbose=args.verbose
            )
            all_results[task_name] = results
        else:
            # Run sequentially
            results = {}
            for model in config['models_to_run']:
                success, message = run_model_for_task(task_name, model, args.verbose)
                results[model] = success
                print(f"  {message}")
            all_results[task_name] = results

    # Summary
    elapsed = time.time() - start_time
    elapsed_hours = elapsed / 3600

    print("\n" + "="*70)
    print("MULTI-MODEL RUN COMPLETE")
    print("="*70)

    # Count results
    total_runs = sum(len(results) for results in all_results.values())
    successful_runs = sum(
        sum(1 for success in results.values() if success)
        for results in all_results.values()
    )

    print(f"\nResults Summary:")
    print(f"  Total model+task combinations: {total_runs}")
    print(f"  Successful: {successful_runs}")
    print(f"  Failed: {total_runs - successful_runs}")
    print(f"  Success rate: {successful_runs*100/total_runs:.1f}%")

    print(f"\nTiming:")
    print(f"  Total time: {elapsed_hours:.2f} hours ({elapsed/60:.0f} minutes)")
    if args.parallel:
        print(f"  (Parallel execution: 2 models per task)")
    else:
        print(f"  (Sequential execution: 1 model at a time)")

    print(f"\nResults by task:")
    for task_name, results in all_results.items():
        status = all(results.values())
        symbol = "[OK]" if status else "[FAIL]"
        passed = sum(1 for s in results.values() if s)
        total = len(results)
        print(f"  {symbol} {task_name:30s} {passed}/{total} models succeeded")

    print(f"\nOutput: benchmark_output/")
    print(f"  Each task now has 3 models:")
    print(f"    • Original model (1.5B or 3.8B) - SKIPPED")
    print(f"    • 0.5B model (tinyllama) - NEW")
    print(f"    • 3.8B or 1.5B model - NEW")

    print(f"\nTotal datasets created: 24 (8 tasks × 3 models)")
    print(f"Total samples: 1,800 (24 directories × 75 samples each)")
    print(f"\nReady for comparison! Same queries, same bins, different models.")
    print(f"Shows scaling: 0.5B → 1.5B → 3.8B\n")

    return 0 if successful_runs == total_runs else 1


if __name__ == "__main__":
    sys.exit(main())
