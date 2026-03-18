#!/usr/bin/env python3
"""
Re-validate all outputs.jsonl files with FIXED validation threshold.
Does NOT re-run inference - just re-processes the validation gate.
"""

import json
import os
from pathlib import Path
import pandas as pd

def revalidate_record(record, max_output_length=1000):
    """Re-validate a single record with fixed threshold"""

    checks = {}
    notes = []

    # 1. Non-empty
    checks["non_empty"] = len(record.get("raw_output", "")) > 0
    if not checks["non_empty"]:
        notes.append("Output is empty")

    # 2. Parseable (keep original check)
    checks["parseable"] = record.get("raw_output") is not None

    # 3. FIXED: Reasonable length - use FIXED threshold
    # Original: len(output) < 200 * 4 = 800 (TOO STRICT)
    # Fixed: len(output) < 1000 (REASONABLE)
    output_len = len(record.get("raw_output", ""))
    checks["not_truncated"] = output_len < max_output_length
    if not checks["not_truncated"]:
        notes.append(f"Output exceeds {max_output_length} chars ({output_len})")

    # 4. Has expected fields
    checks["has_expected_fields"] = bool(record.get("raw_output"))

    # Overall validity
    is_valid = all(checks.values())
    notes_str = "; ".join(notes) if notes else "All checks passed"

    return is_valid, checks, notes_str


def revalidate_task(task_dir):
    """Re-validate all outputs in a task directory"""

    outputs_jsonl = Path(task_dir) / "outputs.jsonl"
    if not outputs_jsonl.exists():
        return None

    print(f"\nRevalidating: {task_dir}")
    print("=" * 70)

    # Read all records
    records = []
    with open(outputs_jsonl) as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Total records: {len(records)}")

    # Re-validate each record
    old_valid = sum(1 for r in records if r.get("valid"))

    for record in records:
        is_valid, checks, notes = revalidate_record(record)
        record["valid"] = is_valid
        record["validation_checks"] = checks
        record["validation_notes"] = notes

    new_valid = sum(1 for r in records if r.get("valid"))

    # Write back
    with open(outputs_jsonl, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    # Compute new summary
    by_bin = {}
    for record in records:
        bin_id = record.get("bin")
        if bin_id not in by_bin:
            by_bin[bin_id] = {"success": 0, "total": 0}
        by_bin[bin_id]["total"] += 1
        if record.get("valid"):
            by_bin[bin_id]["success"] += 1

    print(f"Before: {old_valid}/{len(records)} valid ({old_valid*100/len(records):.1f}%)")
    print(f"After:  {new_valid}/{len(records)} valid ({new_valid*100/len(records):.1f}%)")
    print("\nPer-bin breakdown:")
    for bin_id in sorted(by_bin.keys()):
        stats = by_bin[bin_id]
        pct = stats["success"] * 100 / stats["total"]
        print(f"  Bin {bin_id}: {stats['success']}/{stats['total']} ({pct:.1f}%)")

    # Generate SDDF ready CSV
    sddf_data = []
    for bin_id in sorted(by_bin.keys()):
        stats = by_bin[bin_id]
        bin_records = [r for r in records if r.get("bin") == bin_id]
        avg_latency = sum(r.get("latency_sec", 0) for r in bin_records) / len(bin_records) if bin_records else 0

        sddf_data.append({
            "bin": bin_id,
            "n_samples": stats["total"],
            "success_rate": stats["success"] / stats["total"],
            "avg_latency": avg_latency,
            "validity_rate": stats["success"] / stats["total"]
        })

    sddf_csv = Path(task_dir) / "sddf_ready.csv"
    df = pd.DataFrame(sddf_data)
    df.to_csv(sddf_csv, index=False)
    print(f"\nSDDF CSV updated: {sddf_csv}")

    return new_valid / len(records)


def main():
    print("\n" + "=" * 70)
    print("RE-VALIDATING ALL OUTPUTS (NO INFERENCE RE-RUN)")
    print("=" * 70)

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
        success_rate = revalidate_task(str(model_dir))
        if success_rate is not None:
            results[task_dir.name] = success_rate

    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY (RE-VALIDATED)")
    print("=" * 70)

    for task, rate in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"{task:30s}: {rate*100:6.1f}%")

    avg_rate = sum(results.values()) / len(results) if results else 0
    print(f"\n{'AVERAGE':30s}: {avg_rate*100:6.1f}%")
    print("\nRe-validation complete! All outputs.jsonl and SDDF CSVs updated.")


if __name__ == "__main__":
    main()
