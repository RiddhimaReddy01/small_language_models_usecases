"""Analyze and visualize evaluation results."""
import json
from typing import Dict, List
import sys


def load_results(filepath: str = "results.json") -> List[Dict]:
    """Load results from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Results file not found: {filepath}")
        return []


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
        pass_rate = result.get("pass_rate", 0)
        csr = result.get("constraint_satisfaction_rate", 0)
        num_prompts = result.get("num_prompts", 0)

        print(f"\nModel: {model}")
        print(f"  Prompts: {num_prompts}")
        print(f"  Pass Rate: {pass_rate:.1%}")
        print(f"  Constraint Satisfaction Rate: {csr:.1%}")

    # Rankings
    print("\n" + "-" * 80)
    print("RANKINGS")
    print("-" * 80)

    sorted_by_pass = sorted(results, key=lambda x: x.get("pass_rate", 0), reverse=True)
    print("\nBy Pass Rate:")
    for i, r in enumerate(sorted_by_pass, 1):
        print(f"  {i}. {r['model']}: {r['pass_rate']:.1%}")

    sorted_by_csr = sorted(results, key=lambda x: x.get("constraint_satisfaction_rate", 0), reverse=True)
    print("\nBy Constraint Satisfaction Rate:")
    for i, r in enumerate(sorted_by_csr, 1):
        print(f"  {i}. {r['model']}: {r['constraint_satisfaction_rate']:.1%}")

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
    results = load_results()
    if results:
        print_summary(results)
        if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
            for i in range(len(results)):
                print_detailed_responses(results, i)
    else:
        print("No evaluation results found. Run 'python run_fast.py' first.")


if __name__ == "__main__":
    main()
