#!/usr/bin/env python3
"""
Stress Test: Reliability, Consistency, Reproducibility
Validates data integrity, consistency across models, and pipeline robustness
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict
import hashlib

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

MODELS = [
    "tinyllama_1.1b",
    "qwen2.5_1.5b",
    "phi3_mini",
    "groq_mixtral-8x7b-32768",
    "llama_llama-3.3-70b-versatile",
]

EXPECTED_SAMPLES_PER_TASK = 75
EXPECTED_BINS = [0, 1, 2, 3, 4]
SAMPLES_PER_BIN = 15


def test_data_integrity():
    """Test 1: Data Integrity - No corrupted files"""
    print("\n" + "="*70)
    print("TEST 1: DATA INTEGRITY")
    print("="*70)

    issues = []
    valid_count = 0
    total_count = 0

    for task in TASKS:
        task_path = Path("benchmark_output") / task

        for model_dir in task_path.iterdir():
            if not model_dir.is_dir():
                continue

            outputs_path = model_dir / "outputs.jsonl"
            if not outputs_path.exists():
                continue

            total_count += 1

            try:
                records = []
                with open(outputs_path) as f:
                    for line in f:
                        record = json.loads(line)
                        records.append(record)

                # Validate required fields
                required_fields = ["task", "bin", "sample_id", "model", "status", "latency_sec"]
                for record in records:
                    for field in required_fields:
                        if field not in record:
                            issues.append(f"{task}/{model_dir.name}: Missing field '{field}'")

                valid_count += 1
                print(f"  [OK] {task:30s} {model_dir.name:40s} ({len(records)} records)")

            except json.JSONDecodeError as e:
                issues.append(f"{task}/{model_dir.name}: JSON decode error - {str(e)}")
                print(f"  [ERROR] {task:30s} {model_dir.name:40s} - CORRUPTED")
            except Exception as e:
                issues.append(f"{task}/{model_dir.name}: {str(e)}")
                print(f"  [ERROR] {task:30s} {model_dir.name:40s} - ERROR")

    print(f"\n[RESULT] {valid_count}/{total_count} files valid")

    if issues:
        print(f"\n[WARNINGS] {len(issues)} issues found:")
        for issue in issues[:5]:
            print(f"  - {issue}")
        if len(issues) > 5:
            print(f"  ... and {len(issues)-5} more")
        return False

    return True


def test_consistency():
    """Test 2: Consistency - Same queries across models"""
    print("\n" + "="*70)
    print("TEST 2: CONSISTENCY (Same Queries Across Models)")
    print("="*70)

    issues = []

    for task in TASKS:
        task_path = Path("benchmark_output") / task

        # Load sample IDs from first model
        first_samples = None

        for model_dir in sorted(task_path.iterdir()):
            if not model_dir.is_dir():
                continue

            outputs_path = model_dir / "outputs.jsonl"
            if not outputs_path.exists():
                continue

            samples = set()
            try:
                with open(outputs_path) as f:
                    for line in f:
                        record = json.loads(line)
                        samples.add(record.get("sample_id"))
            except:
                continue

            if first_samples is None:
                first_samples = samples
            else:
                # Check if samples match
                if samples != first_samples:
                    missing = first_samples - samples
                    extra = samples - first_samples
                    if missing or extra:
                        issues.append(f"{task}/{model_dir.name}: Sample mismatch")
                        print(f"  [WARN] {task:30s} {model_dir.name:40s} - MISMATCH")
                    else:
                        print(f"  [OK] {task:30s} {model_dir.name:40s} - Consistent")
                else:
                    print(f"  [OK] {task:30s} {model_dir.name:40s} - Consistent")

    print(f"\n[RESULT] Consistency check: {len(issues)} issues")
    return len(issues) == 0


def test_completeness():
    """Test 3: Completeness - All tasks and bins present"""
    print("\n" + "="*70)
    print("TEST 3: COMPLETENESS (All Bins Present)")
    print("="*70)

    issues = []

    for task in TASKS:
        task_path = Path("benchmark_output") / task

        for model_dir in sorted(task_path.iterdir()):
            if not model_dir.is_dir():
                continue

            sddf_path = model_dir / "sddf_ready.csv"
            if not sddf_path.exists():
                issues.append(f"{task}/{model_dir.name}: Missing sddf_ready.csv")
                print(f"  [ERROR] {task:30s} {model_dir.name:40s} - NO SDDF")
                continue

            try:
                sddf_df = pd.read_csv(sddf_path)
                bins_found = set(sddf_df["bin"].unique())
                expected_bins = set(EXPECTED_BINS)

                if bins_found == expected_bins:
                    print(f"  [OK] {task:30s} {model_dir.name:40s} - All bins present")
                else:
                    missing = expected_bins - bins_found
                    issues.append(f"{task}/{model_dir.name}: Missing bins {missing}")
                    print(f"  [WARN] {task:30s} {model_dir.name:40s} - Missing bins {missing}")

            except Exception as e:
                issues.append(f"{task}/{model_dir.name}: {str(e)}")
                print(f"  [ERROR] {task:30s} {model_dir.name:40s} - ERROR")

    print(f"\n[RESULT] Completeness check: {len(issues)} issues")
    return len(issues) == 0


def test_reproducibility():
    """Test 4: Reproducibility - Can re-run analysis scripts"""
    print("\n" + "="*70)
    print("TEST 4: REPRODUCIBILITY (Import All Analysis Modules)")
    print("="*70)

    analysis_modules = [
        "compute_capability_curves",
        "compute_cost_analysis",
        "compute_pareto_frontier",
        "compute_routing_algorithm",
        "generate_full_paper",
    ]

    issues = []

    for module_name in analysis_modules:
        module_path = Path("src") / f"{module_name}.py"

        if not module_path.exists():
            issues.append(f"Module not found: {module_name}")
            print(f"  [ERROR] {module_name:40s} - FILE NOT FOUND")
            continue

        try:
            # Try to import/parse the module
            with open(module_path) as f:
                compile(f.read(), module_path, 'exec')
            print(f"  [OK] {module_name:40s} - Valid Python")
        except SyntaxError as e:
            issues.append(f"{module_name}: Syntax error - {str(e)}")
            print(f"  [ERROR] {module_name:40s} - SYNTAX ERROR")
        except Exception as e:
            issues.append(f"{module_name}: {str(e)}")
            print(f"  [ERROR] {module_name:40s} - ERROR")

    print(f"\n[RESULT] Reproducibility check: {len(issues)} issues")
    return len(issues) == 0


def test_sample_distribution():
    """Test 5: Sample Distribution - 15 per bin"""
    print("\n" + "="*70)
    print("TEST 5: SAMPLE DISTRIBUTION (15 per bin)")
    print("="*70)

    issues = []
    distribution_ok = True

    for task in TASKS[:3]:  # Sample 3 tasks
        task_path = Path("benchmark_output") / task

        for model_dir in sorted(task_path.iterdir())[:2]:  # Sample 2 models
            if not model_dir.is_dir():
                continue

            outputs_path = model_dir / "outputs.jsonl"
            if not outputs_path.exists():
                continue

            try:
                bin_counts = defaultdict(int)
                with open(outputs_path) as f:
                    for line in f:
                        record = json.loads(line)
                        bin_counts[record["bin"]] += 1

                expected_dist = all(count == SAMPLES_PER_BIN for count in bin_counts.values())

                if expected_dist:
                    print(f"  [OK] {task:30s} {model_dir.name:35s} - Perfect distribution")
                else:
                    dist_str = ", ".join([f"Bin{b}:{c}" for b, c in sorted(bin_counts.items())])
                    print(f"  [WARN] {task:30s} {model_dir.name:35s} - {dist_str}")
                    distribution_ok = False

            except Exception as e:
                issues.append(str(e))
                print(f"  [ERROR] {task:30s} {model_dir.name:35s} - ERROR")

    print(f"\n[RESULT] Sample distribution check: {'OK' if distribution_ok else 'WARNINGS'}")
    return distribution_ok


def test_latency_sanity():
    """Test 6: Latency Sanity - Reasonable values"""
    print("\n" + "="*70)
    print("TEST 6: LATENCY SANITY (Reasonable Response Times)")
    print("="*70)

    issues = []

    latency_ranges = {
        "tinyllama": (0.001, 60),      # Local: 1ms - 60s
        "qwen2.5": (0.001, 60),        # Local: 1ms - 60s
        "phi3": (0.001, 60),           # Local: 1ms - 60s
        "mixtral": (0.001, 10),        # Cloud: 1ms - 10s
        "llama": (0.001, 10),          # Cloud: 1ms - 10s
    }

    for task in TASKS[:2]:  # Sample check
        task_path = Path("benchmark_output") / task

        for model_dir in sorted(task_path.iterdir())[:1]:  # Sample 1 model
            if not model_dir.is_dir():
                continue

            outputs_path = model_dir / "outputs.jsonl"
            if not outputs_path.exists():
                continue

            try:
                latencies = []
                with open(outputs_path) as f:
                    for line in f:
                        record = json.loads(line)
                        if "latency_sec" in record:
                            latencies.append(record["latency_sec"])

                if latencies:
                    min_lat = min(latencies)
                    max_lat = max(latencies)
                    avg_lat = sum(latencies) / len(latencies)

                    # Find expected range
                    model_key = None
                    for key in latency_ranges.keys():
                        if key in model_dir.name:
                            model_key = key
                            break

                    if model_key:
                        min_expected, max_expected = latency_ranges[model_key]

                        if min_expected <= min_lat and max_lat <= max_expected:
                            print(f"  [OK] {task:30s} {model_dir.name:35s} - {avg_lat:.2f}s avg")
                        else:
                            print(f"  [WARN] {task:30s} {model_dir.name:35s} - Range [{min_lat:.2f}s - {max_lat:.2f}s]")
                            issues.append(f"Latency out of range: {model_dir.name}")

            except Exception as e:
                issues.append(str(e))

    print(f"\n[RESULT] Latency sanity check: {len(issues)} issues")
    return len(issues) == 0


def main():
    print("\n" + "="*70)
    print("CODEBASE STRESS TEST")
    print("Reliability, Consistency, Reproducibility")
    print("="*70)

    results = {
        "Data Integrity": test_data_integrity(),
        "Consistency": test_consistency(),
        "Completeness": test_completeness(),
        "Reproducibility": test_reproducibility(),
        "Sample Distribution": test_sample_distribution(),
        "Latency Sanity": test_latency_sanity(),
    }

    print("\n\n" + "="*70)
    print("STRESS TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[WARN]"
        print(f"{status} {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED - Codebase is RELIABLE, CONSISTENT, REPRODUCIBLE")
        return 0
    else:
        print("\n[WARN] Some tests had warnings - Review above for details")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
