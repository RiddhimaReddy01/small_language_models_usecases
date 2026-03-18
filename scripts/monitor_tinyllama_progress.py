#!/usr/bin/env python3
"""
Monitor TinyLLaMA parallel resume progress in real-time.
"""

import json
from pathlib import Path
import time
import sys

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
    """Get current status of a task"""
    outputs_file = OUTPUT_ROOT / task / "tinyllama_1.1b" / "outputs.jsonl"

    try:
        with open(outputs_file) as f:
            lines = f.readlines()

        completed = len(lines)
        # Count successes
        successes = 0
        for line in lines:
            try:
                record = json.loads(line)
                if record.get("status") == "success":
                    successes += 1
            except:
                pass

        return completed, 75, successes
    except FileNotFoundError:
        return 0, 75, 0

def monitor(interval=15):
    """Monitor progress continuously"""
    print("\n" + "="*90)
    print("TINYLLAMA PARALLEL PROGRESS MONITOR")
    print("="*90)

    last_totals = {}

    try:
        while True:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]")
            print("-"*90)

            total_collected = 0
            total_successes = 0

            for task in TASKS:
                completed, target, successes = get_task_status(task)
                total_collected += completed
                total_successes += successes

                pct = (completed / target * 100) if target else 0
                success_pct = (successes / completed * 100) if completed else 0

                # Show change indicator
                prev = last_totals.get(task, 0)
                change = completed - prev
                change_str = f" (+{change})" if change > 0 else ""

                status = "COMPLETE" if completed >= target else "IN PROGRESS"
                print(f"{task:<30} {completed:>2}/{target}  {pct:>5.1f}%  "
                      f"Success: {success_pct:>5.1f}% ({successes}/{completed}){change_str}  {status}")

                last_totals[task] = completed

            print("-"*90)
            overall_pct = (total_collected / 600 * 100) if total_collected else 0
            overall_success = (total_successes / total_collected * 100) if total_collected else 0
            print(f"{'TOTAL':<30} {total_collected:>3}/600  {overall_pct:>5.1f}%  "
                  f"Success: {overall_success:>5.1f}% ({total_successes}/{total_collected})")
            print("="*90)

            # Check if all complete
            all_complete = all(
                get_task_status(task)[0] >= 75 for task in TASKS
            )

            if all_complete:
                print("[OK] All tasks complete!")
                break

            print(f"[Checking again in {interval}s... Press Ctrl+C to exit]")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[STOPPED] Monitoring stopped by user")
        return 0

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    sys.exit(monitor(interval))
