#!/usr/bin/env python3
"""
End-to-End Test Pipeline with Frozen Thresholds

Demonstrates integration of frozen tau^consensus values through the complete pipeline:
1. Validation phase: Apply frozen thresholds to validation data
2. Test phase: Apply frozen thresholds to test data
3. Generate reports with tier decisions
4. Compare against paper results

This replaces the old learning-based threshold selection with frozen paper values.

Reference: Paper Table 6.3 and Section 7
"""

import json
from pathlib import Path
from typing import Any

from sddf import (
    FROZEN_TAU_CONSENSUS,
    all_frozen_thresholds,
)
from sddf.validation_with_frozen import (
    validate_all_tasks,
    save_validation_report,
    print_validation_summary,
)
from sddf.test_with_frozen import (
    run_test_phase,
    save_test_results,
    print_test_summary,
)


def create_dummy_data() -> tuple[dict, dict, dict]:
    """
    Create dummy test data for demonstration.

    In production, this would load actual validation/test data.

    Returns:
        (query_difficulties_by_task, query_results_by_task, test_samples_by_task)
    """
    task_families = list(FROZEN_TAU_CONSENSUS.keys())
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

    # Dummy validation data
    query_difficulties_by_task = {}
    query_results_by_task = {}

    for task_family in task_families:
        query_difficulties_by_task[task_family] = {}
        query_results_by_task[task_family] = {}

        for model_name in model_names:
            query_difficulties_by_task[task_family][model_name] = {}
            for i in range(20):  # 20 queries per model
                query_id = f"{task_family}_query_{model_name}_{i}"
                # Difficulty between 0 and 1
                difficulty = (i % 10) * 0.1 + 0.05
                query_difficulties_by_task[task_family][model_name][query_id] = difficulty

        for i in range(20):
            query_id = f"{task_family}_query_{i}"
            # Random correctness (70% correct)
            is_correct = (i % 10) < 7
            query_results_by_task[task_family][query_id] = {
                "slm_correct": is_correct,
                "llm_correct": True,  # LLM is always correct in this dummy
            }

    # Dummy test data
    test_samples_by_task = {}
    for task_family in task_families:
        test_samples_by_task[task_family] = {}

        for model_name in model_names:
            test_samples_by_task[task_family][model_name] = {}
            for i in range(30):  # 30 test queries per model
                query_id = f"{task_family}_test_{model_name}_{i}"
                difficulty = (i % 10) * 0.1 + 0.05
                is_correct = (i % 10) < 7
                test_samples_by_task[task_family][model_name][query_id] = {
                    "p_fail": 1.0 - difficulty,  # Failure prob = 1 - difficulty
                    "slm_correct": is_correct,
                    "llm_correct": True,
                }

    return query_difficulties_by_task, query_results_by_task, test_samples_by_task


def main():
    """Run end-to-end pipeline with frozen thresholds."""
    print("\n" + "=" * 80)
    print("END-TO-END PIPELINE WITH FROZEN THRESHOLDS")
    print("Paper: A Unified Framework for Enterprise SLM Deployment")
    print("=" * 80)

    # Setup
    task_families = list(FROZEN_TAU_CONSENSUS.keys())
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]
    output_dir = Path("model_runs/test_with_frozen_thresholds")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nConfiguration:")
    print(f"  Task families: {len(task_families)}")
    for tf in task_families:
        print(f"    - {tf}: tau = {FROZEN_TAU_CONSENSUS[tf]:.4f}")
    print(f"  Models: {model_names}")
    print(f"  Output directory: {output_dir}")

    # Load data
    print("\nLoading data...")
    (
        query_difficulties_by_task,
        query_results_by_task,
        test_samples_by_task,
    ) = create_dummy_data()
    print("  Data created (dummy for demonstration)")

    # Validation phase
    print("\n" + "-" * 80)
    print("VALIDATION PHASE")
    print("-" * 80)
    print("Applying frozen thresholds to validation data...")

    validation_results = validate_all_tasks(
        task_families,
        model_names,
        query_difficulties_by_task,
        query_results_by_task,
    )

    print_validation_summary(validation_results)
    validation_output = output_dir / "validation_with_frozen.json"
    save_validation_report(validation_results, validation_output)

    # Test phase
    print("\n" + "-" * 80)
    print("TEST PHASE")
    print("-" * 80)
    print("Applying frozen thresholds to test data...")

    test_results = run_test_phase(
        task_families,
        model_names,
        test_samples_by_task,
    )

    print_test_summary(test_results)
    test_output = output_dir / "test_with_frozen.json"
    save_test_results(test_results, test_output)

    # Summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED")
    print("=" * 80)

    print(f"\nOutputs saved:")
    print(f"  Validation: {validation_output}")
    print(f"  Test:       {test_output}")

    print("\nKey metrics:")
    val_summary = validation_results.get("summary", {})
    test_summary = test_results.get("summary", {})

    print(f"  Validation tasks: {val_summary.get('tasks_validated', 0)}")
    print(f"    SLM tier:   {val_summary.get('slm_tier_count', 0)}")
    print(f"    HYBRID:     {val_summary.get('hybrid_tier_count', 0)}")
    print(f"    LLM tier:   {val_summary.get('llm_tier_count', 0)}")

    print(f"\n  Test queries:     {test_summary.get('total_queries', 0)}")
    print(f"  Test failures:    {test_summary.get('total_failures', 0)}")
    print(f"  Failure rate:     {test_summary.get('overall_failure_rate', 0):.2%}")

    print("\n  Paper frozen thresholds used:")
    for task, tau in sorted(FROZEN_TAU_CONSENSUS.items()):
        print(f"    {task:25s}: {tau:.4f}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Load real validation/test data instead of dummy data")
    print("2. Integrate with actual benchmarking pipeline")
    print("3. Verify tier agreements match paper Table 8.1")
    print("4. Generate final alignment report")
    print()


if __name__ == "__main__":
    main()
