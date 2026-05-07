#!/usr/bin/env python3
"""
Quantify impact of SDDF routing: LLM call reduction, cost savings, coverage analysis.

Outputs:
- Console table with all key metrics
- model_runs/deck_visuals/impact_summary.json for archiving
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_RUNS = PROJECT_ROOT / "model_runs"
OUTPUT_DIR = MODEL_RUNS / "deck_visuals"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Cost model (from generate_business_dashboard.py constants)
LLM_COST_PER_QUERY_USD = 0.0035      # API call cost
SLM_COST_PER_QUERY_USD = 0.0003      # Local inference (10x cheaper)
COST_REDUCTION_RATIO = SLM_COST_PER_QUERY_USD / LLM_COST_PER_QUERY_USD  # ~8.6%

# Data files
TEST_RESULTS_FILE = MODEL_RUNS / "test_results.json"
UC_EMPIRICAL_FILE = MODEL_RUNS / "uc_empirical_routing.json"
UC_TIER_SENSITIVITY_FILE = MODEL_RUNS / "uc_tier_sensitivity.json"


# ============================================================================
# LOADERS
# ============================================================================

def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    if not filepath.exists():
        raise FileNotFoundError(f"Required data file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)


def load_test_results() -> Dict[str, Dict]:
    """Load per-task test results with routing counts."""
    return load_json(TEST_RESULTS_FILE)


def load_uc_data() -> Dict[str, Dict]:
    """Load UC empirical routing data."""
    return load_json(UC_EMPIRICAL_FILE)


def load_uc_sensitivity() -> Dict[str, Any]:
    """Load UC tier sensitivity analysis."""
    return load_json(UC_TIER_SENSITIVITY_FILE)


# ============================================================================
# IMPACT CALCULATIONS
# ============================================================================

def calculate_per_task_metrics() -> Dict[str, Dict]:
    """Calculate LLM call reduction per task family."""
    test_results = load_test_results()

    metrics = {}
    for task, results in test_results.items():
        slm_routed = results.get("slm_routed", 0)
        llm_routed = results.get("llm_routed", 0)
        total = slm_routed + llm_routed

        if total > 0:
            slm_ratio = slm_routed / total
            slm_coverage_pct = 100 * slm_ratio

            # Cost calculation
            blended_cost = slm_ratio * SLM_COST_PER_QUERY_USD + (1 - slm_ratio) * LLM_COST_PER_QUERY_USD
            baseline_cost = LLM_COST_PER_QUERY_USD
            cost_savings_pct = 100 * (1 - blended_cost / baseline_cost)

            metrics[task] = {
                "slm_routed": slm_routed,
                "llm_routed": llm_routed,
                "total_queries": total,
                "slm_coverage_pct": slm_coverage_pct,
                "cost_per_query_usd": blended_cost,
                "cost_savings_vs_baseline_pct": cost_savings_pct,
                "capability_slm": results.get("capability_slm", 0.0),
                "capability_llm": results.get("capability_llm", 0.0),
            }

    return metrics


def calculate_overall_metrics(per_task_metrics: Dict) -> Dict:
    """Calculate overall weighted metrics across all tasks."""
    total_slm = sum(m["slm_routed"] for m in per_task_metrics.values())
    total_llm = sum(m["llm_routed"] for m in per_task_metrics.values())
    total_queries = total_slm + total_llm

    overall_slm_pct = 100 * total_slm / total_queries if total_queries > 0 else 0
    overall_llm_pct = 100 * total_llm / total_queries if total_queries > 0 else 0

    # Blended cost
    blended_cost = (total_slm / total_queries * SLM_COST_PER_QUERY_USD +
                   total_llm / total_queries * LLM_COST_PER_QUERY_USD)
    baseline_cost = LLM_COST_PER_QUERY_USD
    cost_savings_pct = 100 * (1 - blended_cost / baseline_cost)

    total_cost_with_routing = blended_cost * total_queries
    total_cost_all_llm = baseline_cost * total_queries
    absolute_savings = total_cost_all_llm - total_cost_with_routing

    return {
        "total_queries": total_queries,
        "total_slm_routed": total_slm,
        "total_llm_routed": total_llm,
        "slm_routing_pct": overall_slm_pct,
        "llm_routing_pct": overall_llm_pct,
        "blended_cost_per_query_usd": blended_cost,
        "baseline_cost_per_query_usd": baseline_cost,
        "cost_savings_vs_baseline_pct": cost_savings_pct,
        "total_cost_with_routing_usd": total_cost_with_routing,
        "total_cost_all_llm_usd": total_cost_all_llm,
        "absolute_savings_usd": absolute_savings,
    }


def calculate_uc_tier_metrics() -> Dict:
    """Calculate UC-level tier and cost metrics."""
    uc_data = load_uc_data()

    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    total_rows = 0
    slm_rows = 0
    weighted_rho_bar = 0.0

    for uc_id, uc_info in uc_data.items():
        tier = uc_info["tier"]
        tier_counts[tier] += 1
        rows = uc_info.get("total_rows", 0)
        rho_bar = uc_info.get("rho_bar", 0.0)

        total_rows += rows
        weighted_rho_bar += rows * rho_bar

        if tier == "SLM":
            slm_rows += rows

    avg_rho_bar = weighted_rho_bar / total_rows if total_rows > 0 else 0.0

    # UC-level cost calculation
    slm_uc_cost = tier_counts["SLM"] * SLM_COST_PER_QUERY_USD
    hybrid_uc_cost = sum(
        uc_data[uc]["rho_bar"] * SLM_COST_PER_QUERY_USD +
        (1 - uc_data[uc]["rho_bar"]) * LLM_COST_PER_QUERY_USD
        for uc in uc_data if uc_data[uc]["tier"] == "HYBRID"
    )
    llm_uc_cost = tier_counts["LLM"] * LLM_COST_PER_QUERY_USD

    blended_uc_cost = slm_uc_cost + hybrid_uc_cost + llm_uc_cost
    all_llm_uc_cost = 8 * LLM_COST_PER_QUERY_USD

    return {
        "num_ucs": 8,
        "slm_tier_count": tier_counts["SLM"],
        "hybrid_tier_count": tier_counts["HYBRID"],
        "llm_tier_count": tier_counts["LLM"],
        "slm_tier_coverage_pct": 100 * tier_counts["SLM"] / 8,
        "total_rows_across_ucs": total_rows,
        "weighted_avg_rho_bar": avg_rho_bar,
        "uc_blended_cost_usd": blended_uc_cost,
        "uc_all_llm_cost_usd": all_llm_uc_cost,
        "uc_absolute_savings_usd": all_llm_uc_cost - blended_uc_cost,
        "uc_cost_savings_pct": 100 * (1 - blended_uc_cost / all_llm_uc_cost),
    }


def calculate_sensitivity_insight() -> Dict:
    """Extract key insight from sensitivity analysis."""
    sensitivity = load_uc_sensitivity()

    baseline = sensitivity.get("paper_baseline", {})
    baseline_coverage = baseline.get("slm_coverage", 0.625)

    optimize_slm = sensitivity.get("optimal_configurations", {}).get("maximize_slm", {})
    optimal_coverage = optimize_slm.get("slm_coverage", 0.75)

    return {
        "paper_baseline_slm_coverage_pct": 100 * baseline_coverage,
        "optimal_slm_coverage_pct": 100 * optimal_coverage,
        "coverage_improvement_pct": 100 * (optimal_coverage - baseline_coverage),
        "baseline_thresholds": baseline.get("thresholds", {}),
        "optimal_thresholds": optimize_slm.get("thresholds", {}),
    }


# ============================================================================
# OUTPUT
# ============================================================================

def print_impact_summary(per_task: Dict, overall: Dict, uc_metrics: Dict, sensitivity: Dict):
    """Print formatted impact summary table."""
    print("\n" + "=" * 100)
    print("SDDF IMPACT QUANTIFICATION: Cost Savings & Coverage Analysis")
    print("=" * 100)

    # Section 1: Overall Metrics
    print("\n[1] OVERALL QUERY ROUTING IMPACT")
    print("-" * 100)
    print(f"  Total queries analyzed: {overall['total_queries']:,}")
    print(f"  - Routed to SLM: {overall['total_slm_routed']:,} ({overall['slm_routing_pct']:.1f}%)")
    print(f"  - Routed to LLM: {overall['total_llm_routed']:,} ({overall['llm_routing_pct']:.1f}%)")
    print()
    print(f"  Cost per query:")
    print(f"    - With SDDF routing: ${overall['blended_cost_per_query_usd']:.4f}")
    print(f"    - All-LLM baseline:  ${overall['baseline_cost_per_query_usd']:.4f}")
    print(f"    - Savings per query: ${overall['baseline_cost_per_query_usd'] - overall['blended_cost_per_query_usd']:.4f}")
    print()
    print(f"  Total cost impact (all {overall['total_queries']:,} queries):")
    print(f"    - Cost with SDDF: ${overall['total_cost_with_routing_usd']:,.2f}")
    print(f"    - Cost all-LLM:   ${overall['total_cost_all_llm_usd']:,.2f}")
    print(f"    - ABSOLUTE SAVINGS: ${overall['absolute_savings_usd']:,.2f}")
    print(f"    - SAVINGS RATE: {overall['cost_savings_vs_baseline_pct']:.1f}%")

    # Section 2: Per-Task LLM Reduction
    print("\n[2] LLM CALL REDUCTION BY TASK FAMILY")
    print("-" * 100)
    print(f"{'Task Family':<25} {'SLM':<10} {'LLM':<10} {'SLM %':<10} {'Cost/Query':<15} {'Savings %':<10}")
    print("-" * 100)

    for task in sorted(per_task.keys()):
        metrics = per_task[task]
        print(f"{task:<25} {metrics['slm_routed']:<10} {metrics['llm_routed']:<10} "
              f"{metrics['slm_coverage_pct']:>8.1f}% ${metrics['cost_per_query_usd']:>12.4f} "
              f"{metrics['cost_savings_vs_baseline_pct']:>8.1f}%")

    print("-" * 100)
    print(f"{'TOTAL':<25} {overall['total_slm_routed']:<10} {overall['total_llm_routed']:<10} "
          f"{overall['slm_routing_pct']:>8.1f}% ${overall['blended_cost_per_query_usd']:>12.4f} "
          f"{overall['cost_savings_vs_baseline_pct']:>8.1f}%")

    # Section 3: Use Case Coverage
    print("\n[3] USE CASE TIER ASSIGNMENT & COVERAGE")
    print("-" * 100)
    print(f"  SLM Tier:   {uc_metrics['slm_tier_count']}/8 UCs  ({uc_metrics['slm_tier_coverage_pct']:.1f}%)")
    print(f"    => These {uc_metrics['slm_tier_count']} use cases can run fully on SLMs (no LLM fallback needed)")
    print()
    print(f"  HYBRID:     {uc_metrics['hybrid_tier_count']}/8 UCs")
    print(f"    => These {uc_metrics['hybrid_tier_count']} use cases need smart per-query routing")
    print()
    print(f"  LLM Tier:   {uc_metrics['llm_tier_count']}/8 UCs")
    print(f"    => These {uc_metrics['llm_tier_count']} use cases require LLM for all queries (safety/capability)")
    print()
    print(f"  UC-level cost (average per UC):")
    print(f"    - With tier routing:  ${uc_metrics['uc_blended_cost_usd']:.4f}")
    print(f"    - All-LLM baseline:   ${uc_metrics['uc_all_llm_cost_usd']:.4f}")
    print(f"    - Savings per UC:     ${uc_metrics['uc_all_llm_cost_usd'] - uc_metrics['uc_blended_cost_usd']:.4f}")
    print(f"    - UC-level savings:   {uc_metrics['uc_cost_savings_pct']:.1f}%")

    # Section 4: Sensitivity Insight
    print("\n[4] THRESHOLD SENSITIVITY (Paper Baseline vs. Optimal)")
    print("-" * 100)
    print(f"  Paper baseline (slm_threshold=0.70, llm_threshold=0.30):")
    print(f"    => SLM tier coverage: {sensitivity['paper_baseline_slm_coverage_pct']:.1f}% of UCs")
    print()
    print(f"  Optimal configuration (maximizing SLM coverage):")
    print(f"    => SLM tier coverage: {sensitivity['optimal_slm_coverage_pct']:.1f}% of UCs")
    print(f"    => Improvement: +{sensitivity['coverage_improvement_pct']:.1f}% more UCs in SLM tier")
    print()
    print(f"  Optimal thresholds: {sensitivity['optimal_thresholds']}")

    # Summary conclusions
    print("\n[5] KEY TAKEAWAYS FOR PRESENTATION")
    print("-" * 100)
    print(f"  [+] {overall['slm_routing_pct']:.1f}% of enterprise queries can be handled by SLMs alone")
    print(f"  [+] {uc_metrics['slm_tier_coverage_pct']:.0f}% of use cases never need LLM (fully SLM)")
    print(f"  [+] Cost savings: {overall['cost_savings_vs_baseline_pct']:.1f}% vs. all-LLM baseline")
    print(f"  [+] Potential absolute savings: ${overall['absolute_savings_usd']:,.2f} for {overall['total_queries']:,} queries")
    print(f"  [+] With optimal thresholds, can achieve {sensitivity['optimal_slm_coverage_pct']:.0f}% UC coverage")

    print("=" * 100 + "\n")


def save_impact_json(per_task: Dict, overall: Dict, uc_metrics: Dict, sensitivity: Dict):
    """Save impact summary to JSON."""
    output = {
        "metadata": {
            "description": "SDDF impact quantification: cost savings, LLM reduction, coverage",
            "cost_model": {
                "llm_cost_per_query_usd": LLM_COST_PER_QUERY_USD,
                "slm_cost_per_query_usd": SLM_COST_PER_QUERY_USD,
                "cost_reduction_ratio": COST_REDUCTION_RATIO,
            }
        },
        "overall_metrics": overall,
        "per_task_metrics": per_task,
        "use_case_metrics": uc_metrics,
        "threshold_sensitivity": sensitivity,
    }

    output_file = OUTPUT_DIR / "impact_summary.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[OK] Saved impact summary to {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Calculate and display impact metrics."""
    try:
        print(f"\nCalculating impact metrics...")

        per_task = calculate_per_task_metrics()
        overall = calculate_overall_metrics(per_task)
        uc_metrics = calculate_uc_tier_metrics()
        sensitivity = calculate_sensitivity_insight()

        print_impact_summary(per_task, overall, uc_metrics, sensitivity)
        save_impact_json(per_task, overall, uc_metrics, sensitivity)

        return 0

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
