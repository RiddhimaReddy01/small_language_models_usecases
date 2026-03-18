#!/usr/bin/env python3
"""
Master Analysis Orchestrator
Runs all 5 analysis scripts in sequence to generate full publication
"""

import subprocess
import sys
from pathlib import Path
import time

ANALYSIS_SCRIPTS = [
    ("compute_capability_curves.py", "Capability Curves Analysis"),
    ("compute_cost_analysis.py", "Cost-Benefit Analysis"),
    ("compute_pareto_frontier.py", "Pareto Frontier Analysis"),
    ("compute_routing_algorithm.py", "Routing Algorithm Computation"),
    ("generate_full_paper.py", "Full Publication Paper"),
]


def run_analysis_script(script_name: str, description: str) -> bool:
    """Run a single analysis script"""
    print("\n" + "="*70)
    print(f"STEP: {description}")
    print("="*70)

    script_path = Path(__file__).parent.parent / "src" / script_name

    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent.parent,
            capture_output=False,
            timeout=300  # 5 minute timeout per script
        )

        if result.returncode == 0:
            print(f"\n[OK] {description} completed successfully")
            return True
        else:
            print(f"\n[ERROR] {description} failed with exit code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print(f"\n[ERROR] {description} timed out (exceeded 5 minutes)")
        return False
    except Exception as e:
        print(f"\n[ERROR] {description} failed: {str(e)}")
        return False


def main():
    print("\n" + "="*70)
    print("FULL ANALYSIS PIPELINE")
    print("SLM vs LLM Benchmark Analysis")
    print("="*70)

    start_time = time.time()

    # Create analysis directory
    analysis_dir = Path(__file__).parent.parent / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    results = {}

    # Run each script
    for script_name, description in ANALYSIS_SCRIPTS:
        success = run_analysis_script(script_name, description)
        results[description] = success

        if not success:
            print(f"\n[WARNING] {description} failed. Continuing...")

    # Summary
    print("\n\n" + "="*70)
    print("ANALYSIS PIPELINE SUMMARY")
    print("="*70)

    for description, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {description}")

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60

    print(f"\nTotal: {success_count}/{total_count} steps successful")
    print(f"Time: {elapsed_min:.1f} minutes")

    if success_count == total_count:
        print("\n[SUCCESS] Full analysis pipeline complete!")
        print("\nGenerated outputs in analysis/:")
        print("  • capability_curves.csv")
        print("  • average_capability_curves.csv")
        print("  • tipping_points.json")
        print("  • cost_analysis.csv")
        print("  • pareto_analysis.json")
        print("  • pareto_efficiency_matrix.csv")
        print("  • routing_policy.json")
        print("  • routing_validation.csv")
        print("  • PAPER.md (publication-ready)")
        print("\nSummary reports:")
        print("  • CAPABILITY_CURVES_SUMMARY.md")
        print("  • COST_BENEFIT_SUMMARY.md")
        print("  • PARETO_FRONTIER_SUMMARY.md")
        print("  • ROUTING_POLICY_SUMMARY.md")
        return 0
    else:
        print(f"\n[WARNING] {total_count - success_count} steps failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
