#!/usr/bin/env python3
"""
End-to-End SDDF Runtime Pipeline with Frozen Thresholds

Executes the complete SDDF runtime implementation:
1. Validation phase: Apply frozen tau thresholds to validation data
2. Test phase: Apply frozen tau thresholds to test data
3. Use case mapping: Route task family results to enterprise UCs
4. Threshold sensitivity analysis: Optimize tier boundaries via risk-coverage tradeoff
5. Generate deployment recommendations

Uses frozen tau values learned from SDDF v3 training (seed42) and routing probabilities
from threshold sensitivity analysis to recommend SLM/HYBRID/LLM deployment tiers.
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
from sddf.usecase_mapping import (
    map_taskfamily_results_to_usecases,
    create_usecase_tier_report,
    print_usecase_tier_summary,
    save_usecase_tier_results,
)
from sddf.threshold_sensitivity_analysis import (
    analyze_threshold_sensitivity,
    print_threshold_sensitivity_report,
    save_sensitivity_analysis,
    plot_threshold_sensitivity,
)


def load_sddf_v3_data(
    splits_root: Path = Path("model_runs/clean_deterministic_splits"),
) -> tuple[dict, dict, dict]:
    """
    Load real SDDF v3 validation/test data from official splits.

    Returns:
        (query_difficulties_by_task, query_results_by_task, test_samples_by_task)
    """
    task_families = list(FROZEN_TAU_CONSENSUS.keys())
    model_names = ["qwen2.5_0.5b", "qwen2.5_3b"]  # Use available models

    query_difficulties_by_task = {}
    query_results_by_task = {}
    test_samples_by_task = {}

    for task_family in task_families:
        query_difficulties_by_task[task_family] = {}
        query_results_by_task[task_family] = {}
        test_samples_by_task[task_family] = {}

        for model_name in model_names:
            model_dir = splits_root / task_family / model_name
            if not model_dir.exists():
                print(f"  Warning: {model_dir} not found, skipping")
                continue

            query_difficulties_by_task[task_family][model_name] = {}
            test_samples_by_task[task_family][model_name] = {}

            # Load validation data
            val_path = model_dir / "val.jsonl"
            if val_path.exists():
                for line in val_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        query_id = row.get("sample_id") or row.get("query_id")
                        if not query_id:
                            continue
                        # Normalize bin (0-9) to difficulty [0,1]
                        bin_val = float(row.get("bin", 5.0))
                        difficulty = bin_val / 9.0
                        query_difficulties_by_task[task_family][model_name][query_id] = difficulty
                        # Track per-task results (aggregated across models later)
                        if query_id not in query_results_by_task[task_family]:
                            status = str(row.get("status", "")).lower()
                            valid = bool(row.get("valid", False))
                            failure_category = row.get("failure_category")
                            error = row.get("error")
                            slm_fail = (
                                (status != "success")
                                or (not valid)
                                or (failure_category not in (None, "", "none"))
                                or (error not in (None, ""))
                            )
                            query_results_by_task[task_family][query_id] = {
                                "slm_correct": not slm_fail,
                                "llm_correct": bool(row.get("llm_correct", True)),
                            }
                    except json.JSONDecodeError:
                        continue

            # Load test data
            test_path = model_dir / "test.jsonl"
            if test_path.exists():
                for line in test_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        query_id = row.get("sample_id") or row.get("query_id")
                        if not query_id:
                            continue
                        bin_val = float(row.get("bin", 5.0))
                        p_fail = 1.0 - (bin_val / 9.0)  # Failure = 1 - difficulty
                        status = str(row.get("status", "")).lower()
                        valid = bool(row.get("valid", False))
                        failure_category = row.get("failure_category")
                        error = row.get("error")
                        slm_fail = (
                            (status != "success")
                            or (not valid)
                            or (failure_category not in (None, "", "none"))
                            or (error not in (None, ""))
                        )
                        test_samples_by_task[task_family][model_name][query_id] = {
                            "p_fail": p_fail,
                            "slm_correct": not slm_fail,
                            "llm_correct": bool(row.get("llm_correct", True)),
                        }
                    except json.JSONDecodeError:
                        continue

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
    print("\nLoading SDDF v3 validation/test data...")
    (
        query_difficulties_by_task,
        query_results_by_task,
        test_samples_by_task,
    ) = load_sddf_v3_data()
    print("  SDDF v3 data loaded from model_runs/clean_deterministic_splits")

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

    # Use case tier mapping
    print("\n" + "-" * 80)
    print("USE CASE TIER ASSIGNMENT (Paper Table 7.4)")
    print("-" * 80)
    print("Mapping task family consensus ratios to enterprise use cases...")

    usecase_report = create_usecase_tier_report(validation_results, test_results)
    print_usecase_tier_summary(usecase_report["validation"])
    print_usecase_tier_summary(usecase_report["test"])

    usecase_output = output_dir / "usecase_tiers_with_frozen.json"
    save_usecase_tier_results(usecase_report, usecase_output)

    # Threshold Sensitivity Analysis (SelectiveNet inspired)
    print("\n" + "-" * 80)
    print("THRESHOLD SENSITIVITY ANALYSIS (SelectiveNet Risk-Coverage Tradeoff)")
    print("-" * 80)
    print("Analyzing optimal tier thresholds based on accuracy-coverage tradeoff...")

    sensitivity_analysis = analyze_threshold_sensitivity(
        test_results,
        threshold_range=(0.2, 0.9),
        step=0.05,
    )
    print_threshold_sensitivity_report(sensitivity_analysis)

    sensitivity_output = output_dir / "threshold_sensitivity.json"
    save_sensitivity_analysis(sensitivity_analysis, sensitivity_output)

    # Generate visualization
    try:
        plot_output = output_dir / "threshold_sensitivity_analysis.png"
        plot_threshold_sensitivity(sensitivity_analysis, plot_output)
    except ImportError:
        print("Note: matplotlib not installed - skipping visualization")

    # Summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED")
    print("=" * 80)

    print(f"\nOutputs saved:")
    print(f"  Validation:          {validation_output}")
    print(f"  Test:                {test_output}")
    print(f"  Use cases:           {usecase_output}")
    print(f"  Sensitivity analysis: {sensitivity_output}")

    print("\nKey metrics:")
    val_summary = validation_results.get("summary", {})
    test_summary = test_results.get("summary", {})
    uc_summary = usecase_report.get("summary", {})

    print(f"  Validation tasks: {val_summary.get('tasks_validated', 0)}")
    print(f"    SLM tier:   {val_summary.get('slm_tier_count', 0)}")
    print(f"    HYBRID:     {val_summary.get('hybrid_tier_count', 0)}")
    print(f"    LLM tier:   {val_summary.get('llm_tier_count', 0)}")

    print(f"\n  Test queries:     {test_summary.get('total_queries', 0)}")
    print(f"  Test failures:    {test_summary.get('total_failures', 0)}")
    print(f"  Failure rate:     {test_summary.get('overall_failure_rate', 0):.2%}")

    print(f"\n  Use case tier agreement: {uc_summary.get('tier_agreement', '0/8')}")
    print(f"    Val SLM:   {uc_summary.get('validation_tiers', {}).get('SLM', 0)}")
    print(f"    Val HYBRID: {uc_summary.get('validation_tiers', {}).get('HYBRID', 0)}")
    print(f"    Val LLM:   {uc_summary.get('validation_tiers', {}).get('LLM', 0)}")
    print(f"    Test SLM:  {uc_summary.get('test_tiers', {}).get('SLM', 0)}")
    print(f"    Test HYBRID: {uc_summary.get('test_tiers', {}).get('HYBRID', 0)}")
    print(f"    Test LLM:  {uc_summary.get('test_tiers', {}).get('LLM', 0)}")

    print("\n  Frozen thresholds (from SDDF v3 training):")
    for task, tau in sorted(FROZEN_TAU_CONSENSUS.items()):
        print(f"    {task:25s}: {tau:.4f}")

    print("\n" + "=" * 80)
    print("RUNTIME DEPLOYMENT READY")
    print("=" * 80)
    print("✅ Frozen thresholds applied successfully")
    print("✅ Validation/test phases complete")
    print("✅ Use case tiers assigned (SLM/HYBRID/LLM)")
    print("✅ Threshold sensitivity analysis optimized tier boundaries")
    print("✅ Routing probabilities determined from sensitivity sweep")
    print()


if __name__ == "__main__":
    main()
