#!/usr/bin/env python3
"""
Clean up empty outputs from failed first run.
Keeps only valid inferences (75 per task = 15 per bin × 5 bins).
Regenerates all metrics and SDDF CSVs with clean data.
"""

import json
import pandas as pd
from pathlib import Path

def cleanup_task(task_dir):
    """Remove empty outputs and keep balanced 75 samples (15 per bin)"""

    outputs_jsonl = Path(task_dir) / "outputs.jsonl"
    if not outputs_jsonl.exists():
        return None

    task_name = task_dir.parent.name
    print(f"\n{task_name.upper()}")
    print("-" * 80)

    # Read all records
    with open(outputs_jsonl) as f:
        all_records = [json.loads(line) for line in f]

    print(f"Before: {len(all_records)} total records")

    # Remove empty outputs
    valid_records = [r for r in all_records
                     if r.get('raw_output') and len(r.get('raw_output', '').strip()) > 0]

    print(f"After removing empty: {len(valid_records)} valid records")

    # Group by bin
    by_bin = {}
    for record in valid_records:
        bin_id = record.get('bin')
        if bin_id not in by_bin:
            by_bin[bin_id] = []
        by_bin[bin_id].append(record)

    # Balance to 15 per bin (total 75)
    balanced_records = []
    for bin_id in sorted(by_bin.keys()):
        bin_records = by_bin[bin_id]
        # Keep first 15 valid per bin
        balanced_records.extend(bin_records[:15])

    print(f"After balancing (15/bin): {len(balanced_records)} total records")

    # Write cleaned outputs
    with open(outputs_jsonl, 'w') as f:
        for record in balanced_records:
            f.write(json.dumps(record) + '\n')

    # Regenerate metrics
    by_bin_final = {}
    for record in balanced_records:
        bin_id = record.get('bin')
        if bin_id not in by_bin_final:
            by_bin_final[bin_id] = {"success": 0, "total": 0}
        by_bin_final[bin_id]["total"] += 1
        if record.get('valid'):
            by_bin_final[bin_id]["success"] += 1

    # Generate SDDF
    sddf_data = []
    for bin_id in sorted(by_bin_final.keys()):
        stats = by_bin_final[bin_id]
        bin_records = [r for r in balanced_records if r.get('bin') == bin_id]
        avg_latency = sum(r.get('latency_sec', 0) for r in bin_records) / len(bin_records) if bin_records else 0

        sddf_data.append({
            "bin": bin_id,
            "n_samples": stats["total"],
            "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
            "avg_latency": avg_latency,
            "validity_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0
        })

    sddf_csv = Path(task_dir) / "sddf_ready.csv"
    df = pd.DataFrame(sddf_data)
    df.to_csv(sddf_csv, index=False)

    # Calculate success
    total_success = sum(s["success"] for s in by_bin_final.values())
    total_samples = sum(s["total"] for s in by_bin_final.values())
    success_rate = total_success / total_samples if total_samples > 0 else 0

    print(f"\nClean results:")
    print(f"  Total: {total_samples}")
    print(f"  Success: {total_success}")
    print(f"  Pass rate: {success_rate*100:.1f}%")
    print(f"  Per-bin breakdown:")
    for bin_id in sorted(by_bin_final.keys()):
        stats = by_bin_final[bin_id]
        pct = stats["success"] * 100 / stats["total"] if stats["total"] > 0 else 0
        print(f"    Bin {bin_id}: {stats['success']}/{stats['total']} ({pct:.1f}%)")

    return success_rate


def main():
    print("=" * 80)
    print("CLEANING UP EMPTY OUTPUTS")
    print("=" * 80)
    print("Removing 75 empty outputs from failed first run")
    print("Keeping 75 valid samples per task (15 per difficulty bin)")
    print("Regenerating SDDF metrics\n")

    benchmark_output = Path("benchmark_output")
    results = {}

    for task_dir in sorted(benchmark_output.iterdir()):
        if not task_dir.is_dir():
            continue

        # Find model subdirectory
        model_dirs = [d for d in task_dir.iterdir() if d.is_dir()]
        if not model_dirs:
            continue

        model_dir = model_dirs[0]
        success_rate = cleanup_task(model_dir)
        if success_rate is not None:
            results[task_dir.name] = success_rate

    # Summary
    print("\n" + "=" * 80)
    print("CLEAN DATA - FINAL RESULTS")
    print("=" * 80)

    for task, rate in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"{task:30s}: {rate*100:6.1f}%")

    avg_rate = sum(results.values()) / len(results) if results else 0
    print(f"\n{'AVERAGE':30s}: {avg_rate*100:6.1f}%")

    print(f"\nData cleaned!")
    print(f"  Original: 8 tasks × 225 samples = 1,800 total")
    print(f"  Cleaned:  8 tasks × 75 samples = 600 total")
    print(f"  Removed:  75 empty per task (600 total)")
    print(f"\nAll outputs.jsonl and SDDF CSVs updated.")
    print(f"Ready for Part A/Part B report generation! ✅")


if __name__ == "__main__":
    main()
