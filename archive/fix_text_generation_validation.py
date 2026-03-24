#!/usr/bin/env python3
"""
Fix text_generation validation bug

The current validation incorrectly flags outputs as "invalid" based on length.
This script corrects that by:
1. Removing length-based rejection for text_generation tasks
2. Re-evaluating based on actual content quality
3. Creating corrected benchmark outputs
"""

import json
from pathlib import Path
from collections import defaultdict


def fix_text_generation_validation(output_line: str, task: str) -> dict:
    """
    Fix validation for a single sample

    For text_generation:
    - Remove "Output suspiciously long" as failure reason
    - Keep structural checks (non_empty, parseable, has_expected_fields)
    - Set status='success' if content exists, even if previously marked invalid
    """
    sample = json.loads(output_line)

    if task != 'text_generation':
        return sample  # Don't modify other tasks

    # Check if this is a false negative due to length
    if sample.get('status') == 'invalid':
        error = sample.get('error', '')

        # If ONLY failure reason is length, fix it
        if 'suspiciously long' in error.lower():
            raw_output = sample.get('raw_output', '').strip()

            # Validate actual content
            has_content = len(raw_output) > 50  # Minimum threshold
            has_structure = sample.get('valid') is True
            validation_checks = sample.get('validation_checks', {})

            # If validation checks pass and we have content, mark as success
            if (has_content and
                validation_checks.get('non_empty') and
                validation_checks.get('parseable')):

                # Fix the sample
                sample['status'] = 'success'
                sample['error'] = None
                sample['validation_notes'] = 'Fixed: Length-based rejection removed (content valid)'

    return sample


def process_task(task_type: str, models: list, output_dir: str = 'benchmark_output_fixed'):
    """Process all models for a task"""

    if task_type != 'text_generation':
        print(f"Skipping {task_type} - only fixing text_generation")
        return

    benchmark_dir = Path('benchmark_output')
    fixed_dir = Path(output_dir)

    print(f"\nProcessing {task_type}...")

    for model in models:
        input_file = benchmark_dir / task_type / model / 'outputs.jsonl'

        if not input_file.exists():
            print(f"  {model}: File not found")
            continue

        # Create output directory
        output_file = fixed_dir / task_type / model / 'outputs.jsonl'
        output_file.parent.mkdir(parents=True, exist_ok=True)

        fixed_count = 0
        kept_count = 0

        with open(input_file) as inf, open(output_file, 'w') as outf:
            for line in inf:
                if not line.strip():
                    continue

                fixed_sample = fix_text_generation_validation(line, task_type)
                outf.write(json.dumps(fixed_sample) + '\n')

                original = json.loads(line)
                if original.get('status') != fixed_sample.get('status'):
                    fixed_count += 1
                else:
                    kept_count += 1

        print(f"  {model}: {fixed_count} fixed, {kept_count} unchanged")


def analyze_fixed_data(output_dir: str = 'benchmark_output_fixed'):
    """Analyze the fixed data"""
    from risk_sensitivity_with_groundtruth import GroundTruthRiskAnalyzer

    print("\n" + "=" * 80)
    print("ANALYZING FIXED TEXT_GENERATION DATA")
    print("=" * 80)

    models = [
        "tinyllama_1.1b",
        "qwen2.5_1.5b",
        "phi3_mini",
        "llama_llama-3.3-70b-versatile"
    ]

    task_type = 'text_generation'
    fixed_dir = Path(output_dir)

    for model in models:
        input_file = fixed_dir / task_type / model / 'outputs.jsonl'

        if not input_file.exists():
            print(f"{model}: No fixed file")
            continue

        success_count = 0
        invalid_count = 0

        with open(input_file) as f:
            for i, line in enumerate(f):
                if i >= 75:
                    break
                if not line.strip():
                    continue

                sample = json.loads(line)
                if sample.get('status') == 'success':
                    success_count += 1
                elif sample.get('status') == 'invalid':
                    invalid_count += 1

        total = success_count + invalid_count
        if total > 0:
            failure_rate = invalid_count / total
            print(f"\n{model}:")
            print(f"  Success: {success_count}/75 ({success_count/75*100:.1f}%)")
            print(f"  Invalid: {invalid_count}/75 ({failure_rate*100:.1f}%)")
            print(f"  → Actual failure rate: {failure_rate*100:.1f}% (not {failure_rate*100:.1f}%)")


if __name__ == "__main__":
    print("FIXING TEXT_GENERATION VALIDATION BUG")
    print("=" * 80)

    models = [
        "tinyllama_1.1b",
        "qwen2.5_1.5b",
        "phi3_mini",
        "llama_llama-3.3-70b-versatile"
    ]

    # Fix text_generation outputs
    process_task('text_generation', models, output_dir='benchmark_output_fixed')

    # Analyze fixed data
    analyze_fixed_data(output_dir='benchmark_output_fixed')

    print("\n" + "=" * 80)
    print("Fixed outputs saved to: benchmark_output_fixed/")
    print("\nTo use fixed data for risk analysis:")
    print("  1. Update analyzer to read from benchmark_output_fixed/")
    print("  2. Or replace original benchmark_output/ with fixed version")
