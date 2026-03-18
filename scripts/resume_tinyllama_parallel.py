#!/usr/bin/env python3
"""
Resume TinyLLaMA benchmark - run REMAINING tasks in parallel on multiple cores.

This script:
1. Identifies which TinyLLaMA tasks are incomplete
2. Runs each incomplete task as a separate subprocess
3. Runs them in parallel to utilize multiple cores
4. Resumes from checkpoint (doesn't rerun already-completed samples)

Usage:
    python scripts/resume_tinyllama_parallel.py [--max-workers N]
"""

import subprocess
import json
from pathlib import Path
import sys
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

OUTPUT_ROOT = Path("./benchmark_output")
TASKS = [
    "text_generation",
    "code_generation",
    "classification",
    "maths",
    "summarization",
    "retrieval_grounded",
    "instruction_following",
    "information_extraction"
]

def get_task_status(task):
    """Check how many samples are complete for a task"""
    outputs_file = OUTPUT_ROOT / task / "tinyllama_1.1b" / "outputs.jsonl"

    try:
        with open(outputs_file) as f:
            lines = f.readlines()
        return len(lines), 75
    except FileNotFoundError:
        return 0, 75

def run_task(task):
    """Run a single task (will resume from checkpoint)"""
    completed, total = get_task_status(task)

    if completed >= total:
        print(f"[SKIP] {task}: Already complete ({completed}/{total})")
        return task, "skipped", completed, total

    print(f"\n[START] {task}: Running {total - completed} remaining samples ({completed}/{total} done)")

    cmd = [
        sys.executable,
        "scripts/run_benchmark_all_8_tasks.py",
        "--task", task,
        "tinyllama:1.1b"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per task
        )

        # Check final status
        completed_after, total = get_task_status(task)

        if result.returncode == 0:
            status = "success" if completed_after >= total else "partial"
        else:
            status = "failed"

        return task, status, completed_after, total

    except subprocess.TimeoutExpired:
        completed_after, total = get_task_status(task)
        print(f"[TIMEOUT] {task}: Exceeded 1 hour limit")
        return task, "timeout", completed_after, total
    except Exception as e:
        completed_after, total = get_task_status(task)
        print(f"[ERROR] {task}: {str(e)}")
        return task, "error", completed_after, total

def main():
    parser = argparse.ArgumentParser(
        description="Resume TinyLLaMA benchmark on multiple cores"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)"
    )
    args = parser.parse_args()

    print("\n" + "="*80)
    print("TINYLLAMA PARALLEL RESUME - Multiple Cores")
    print("="*80)

    # Check status
    print("\nTask Status:")
    print("-"*80)

    incomplete_tasks = []
    total_missing = 0

    for task in TASKS:
        completed, total = get_task_status(task)
        remaining = total - completed
        pct = (completed / total * 100) if total else 0

        if completed >= total:
            status = "COMPLETE"
        else:
            status = f"INCOMPLETE ({remaining} remaining)"
            incomplete_tasks.append(task)
            total_missing += remaining

        print(f"{task:<30} {completed:>2}/{total}  {pct:>5.1f}%  {status}")

    print("-"*80)
    print(f"Total incomplete: {len(incomplete_tasks)} tasks, {total_missing} samples")
    print(f"Max parallel workers: {args.max_workers}")
    print("="*80)

    if not incomplete_tasks:
        print("[OK] All tasks complete!")
        return 0

    # Run incomplete tasks in parallel
    print(f"\n[RUNNING] {len(incomplete_tasks)} incomplete tasks on {args.max_workers} cores...")
    print("="*80)

    start_time = time.time()
    results = {}

    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(run_task, task): task for task in incomplete_tasks}

        # Process results as they complete
        completed_count = 0
        for future in as_completed(future_to_task):
            task, status, completed, total = future.result()
            results[task] = (status, completed, total)
            completed_count += 1

            pct = (completed / total * 100) if total else 0
            print(f"[{completed_count}/{len(incomplete_tasks)}] {task}: {status.upper()} ({completed}/{total} = {pct:.1f}%)")

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    success_count = sum(1 for s, _, _ in results.values() if s == "success")
    partial_count = sum(1 for s, _, _ in results.values() if s == "partial")
    failed_count = sum(1 for s, _, _ in results.values() if s in ["failed", "error", "timeout"])

    total_samples = 0
    for task, (status, completed, total) in results.items():
        print(f"{task:<30} {completed:>2}/{total}  ({status.upper()})")
        total_samples += completed

    print("-"*80)
    print(f"Success: {success_count}, Partial: {partial_count}, Failed: {failed_count}")
    print(f"Total samples collected: {total_samples}/600")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")

    if failed_count == 0:
        print("[OK] All tasks completed successfully!")
        return 0
    else:
        print(f"[WARN] {failed_count} tasks did not complete")
        return 1

if __name__ == "__main__":
    sys.exit(main())
