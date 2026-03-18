#!/usr/bin/env python3
"""
Comprehensive results analysis across all models and tasks.
Generates detailed tables showing pass rates, output lengths, and validation details.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import statistics

# Base path
BASE_PATH = Path("benchmark_output")

# Models and tasks
MODELS = [
    "phi3_mini",
    "llama_llama-3.3-70b-versatile",
    "qwen2.5_1.5b",
    "tinyllama_1.1b",
    "groq_mixtral-8x7b-32768"
]

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

def load_outputs(task, model):
    """Load outputs.jsonl for a task/model combination."""
    path = BASE_PATH / task / model / "outputs.jsonl"
    results = []

    if not path.exists():
        return results

    try:
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except Exception as e:
        print(f"Error loading {task}/{model}: {e}")

    return results

def analyze_outputs(outputs):
    """Analyze output characteristics for a task/model."""
    if not outputs:
        return {
            'total': 0,
            'passed': 0,
            'pass_rate': 0.0,
            'avg_length': 0,
            'min_length': 0,
            'max_length': 0,
            'median_length': 0,
            'outputs_with_valid_check': 0
        }

    passed = sum(1 for o in outputs if o.get('valid', False))
    lengths = []

    for output in outputs:
        if 'raw_output' in output:
            length = len(str(output['raw_output']))
        elif 'output' in output:
            length = len(str(output['output']))
        else:
            length = 0
        if length > 0:
            lengths.append(length)

    return {
        'total': len(outputs),
        'passed': passed,
        'pass_rate': (passed / len(outputs) * 100) if outputs else 0,
        'avg_length': round(statistics.mean(lengths)) if lengths else 0,
        'min_length': min(lengths) if lengths else 0,
        'max_length': max(lengths) if lengths else 0,
        'median_length': round(statistics.median(lengths)) if lengths else 0,
        'outputs_with_valid_check': len(lengths)
    }

def generate_summary_tables():
    """Generate comprehensive summary tables."""

    # Overall pass rate table
    print("\n" + "="*120)
    print("OVERALL PASS RATES BY MODEL AND TASK")
    print("="*120)

    header = "Task".ljust(25)
    for model in MODELS:
        header += f" | {model[:20]:<20}"
    print(header)
    print("-" * 120)

    for task in TASKS:
        row = task.ljust(25)
        for model in MODELS:
            outputs = load_outputs(task, model)
            stats = analyze_outputs(outputs)

            if stats['total'] > 0:
                rate_str = f"{stats['pass_rate']:.1f}% ({stats['passed']}/{stats['total']})"
            else:
                rate_str = "NO DATA"

            row += f" | {rate_str:<20}"
        print(row)

    print("\n" + "="*120)
    print("AVERAGE OUTPUT LENGTH BY MODEL AND TASK (characters)")
    print("="*120)

    header = "Task".ljust(25)
    for model in MODELS:
        header += f" | {model[:20]:<20}"
    print(header)
    print("-" * 120)

    for task in TASKS:
        row = task.ljust(25)
        for model in MODELS:
            outputs = load_outputs(task, model)
            stats = analyze_outputs(outputs)

            if stats['total'] > 0:
                length_str = f"{stats['avg_length']:<6} (range: {stats['min_length']}-{stats['max_length']})"
            else:
                length_str = "NO DATA"

            row += f" | {length_str:<20}"
        print(row)

    # Per-task detailed analysis
    print("\n" + "="*120)
    print("DETAILED PER-TASK ANALYSIS")
    print("="*120)

    for task in TASKS:
        print(f"\n### {task.upper()}")
        print("-" * 120)

        task_header = f"{'Model':<35} | {'Pass Rate':<15} | {'Avg Length':<15} | {'Range':<20} | {'Samples':<10}"
        print(task_header)
        print("-" * 120)

        for model in MODELS:
            outputs = load_outputs(task, model)
            stats = analyze_outputs(outputs)

            if stats['total'] > 0:
                model_display = model[:34]
                pass_str = f"{stats['pass_rate']:.1f}% ({stats['passed']}/{stats['total']})"
                length_str = f"{stats['avg_length']}"
                range_str = f"{stats['min_length']}-{stats['max_length']}"
                sample_str = f"{stats['total']}"

                print(f"{model_display:<35} | {pass_str:<15} | {length_str:<15} | {range_str:<20} | {sample_str:<10}")

def generate_summarization_deep_dive():
    """Deep dive into summarization task."""
    print("\n" + "="*120)
    print("SUMMARIZATION DEEP DIVE - Understanding Quality Differences")
    print("="*120)

    print("\nKey Question: Why does Phi-3 (749 chars avg) score 100% while Llama (643 chars avg) scores 54.7%?")
    print("-" * 120)

    task = "summarization"

    print(f"\n{'Model':<35} | {'Pass Rate':<20} | {'Avg Len':<10} | {'Min-Max':<20} | {'Samples':<10}")
    print("-" * 120)

    for model in ["phi3_mini", "llama_llama-3.3-70b-versatile", "qwen2.5_1.5b", "tinyllama_1.1b"]:
        outputs = load_outputs(task, model)
        stats = analyze_outputs(outputs)

        if stats['total'] > 0:
            model_display = model
            pass_str = f"{stats['pass_rate']:.1f}% ({stats['passed']}/{stats['total']})"
            length_str = f"{stats['avg_length']}"
            range_str = f"{stats['min_length']}-{stats['max_length']}"
            sample_str = f"{stats['total']}"

            print(f"{model_display:<35} | {pass_str:<20} | {length_str:<10} | {range_str:<20} | {sample_str:<10}")

    print("\n" + "-"*120)
    print("HYPOTHESIS: Quality is determined by content completeness, not brevity")
    print("-"*120)
    print("• Phi-3 (100%): Longer outputs capture more key points from source material")
    print("• Llama (54.7%): Shorter outputs sometimes miss important information")
    print("• Validation checks: non_empty, parseable, has_expected_fields (after truncation check removed)")
    print("• This suggests the SDDF evaluation likely includes content completeness scoring")

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    generate_summary_tables()
    generate_summarization_deep_dive()
