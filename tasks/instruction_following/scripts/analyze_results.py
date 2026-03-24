"""Analyze and visualize evaluation results."""
import json
import sys
from pathlib import Path
from typing import Dict, List

DEFAULT_RESULTS_PATH = Path("results/results_detailed.json")


def load_results(filepath: str = str(DEFAULT_RESULTS_PATH)) -> List[Dict]:
    """Load results from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Results file not found: {filepath}")
        return []


def get_pass_rate(result: Dict) -> float:
    """Support both legacy and nested metric layouts."""
    if "pass_rate" in result:
        return result["pass_rate"]
    return result.get("capability_metrics", {}).get("pass_rate", 0.0)


def get_constraint_satisfaction_rate(result: Dict) -> float:
    """Support both legacy and nested metric layouts."""
    if "constraint_satisfaction_rate" in result:
        return result["constraint_satisfaction_rate"]
    return result.get("capability_metrics", {}).get("constraint_satisfaction_rate", 0.0)


def print_summary(results: List[Dict]):
    """Print summary statistics."""
    if not results:
        print("No results to analyze")
        return

    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    for result in results:
        model = result.get("model", "Unknown")
        pass_rate = get_pass_rate(result)
        csr = get_constraint_satisfaction_rate(result)
        num_prompts = result.get("num_prompts", 0)

        print(f"\nModel: {model}")
        print(f"  Prompts: {num_prompts}")
        print(f"  Pass Rate: {pass_rate:.1%}")
        print(f"  Constraint Satisfaction Rate: {csr:.1%}")

    # Rankings
    print("\n" + "-" * 80)
    print("RANKINGS")
    print("-" * 80)

    sorted_by_pass = sorted(results, key=get_pass_rate, reverse=True)
    print("\nBy Pass Rate:")
    for i, r in enumerate(sorted_by_pass, 1):
        print(f"  {i}. {r['model']}: {get_pass_rate(r):.1%}")

    sorted_by_csr = sorted(results, key=get_constraint_satisfaction_rate, reverse=True)
    print("\nBy Constraint Satisfaction Rate:")
    for i, r in enumerate(sorted_by_csr, 1):
        print(f"  {i}. {r['model']}: {get_constraint_satisfaction_rate(r):.1%}")

    print("\n" + "=" * 80)


def print_detailed_responses(results: List[Dict], model_idx: int = 0):
    """Print detailed responses for a specific model."""
    if not results or model_idx >= len(results):
        return

    result = results[model_idx]
    model = result.get("model", "Unknown")
    responses = result.get("responses", [])

    if not responses:
        return

    print(f"\nDETAILED RESPONSES - {model}")
    print("=" * 80)

    for i, resp in enumerate(responses[:5], 1):  # First 5
        print(f"\n{i}. Instruction: {resp['instruction'][:60]}...")
        print(f"   Response: {resp['response'][:70]}...")
        print(f"   Constraints: {resp['constraints_satisfied']}/{resp['total_constraints']}")
        print(f"   Pass: {'✓' if resp['pass'] else '✗'}")


def main():
    """Analyze results."""
    results_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--verbose" else str(DEFAULT_RESULTS_PATH)
    results = load_results(results_path)
    if results:
        print_summary(results)
        if "--verbose" in sys.argv[1:]:
            for i in range(len(results)):
                print_detailed_responses(results, i)
    else:
        print("No evaluation results found. Run 'python scripts/run_fast.py' first.")


if __name__ == "__main__":
    main()
