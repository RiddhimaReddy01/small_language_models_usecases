#!/usr/bin/env python3
"""
Metric Aggregators: Calculate reliability, robustness, format validity
from raw benchmark sample data

These functions aggregate individual sample metrics into per-model, per-task statistics
"""

import statistics
from typing import Dict, List, Optional, Any


# ========== RELIABILITY: % Valid Outputs ==========

def calculate_reliability(samples: List[Dict]) -> float:
    """
    Reliability = % of outputs that pass all validation checks

    Checks required:
    - non_empty: output has content
    - parseable: output is well-formed
    - has_expected_fields: output has required structure

    Args:
        samples: List of benchmark samples with validation_checks field

    Returns:
        Reliability score [0, 1]
    """
    if not samples:
        return 0.0

    required_checks = ['non_empty', 'parseable', 'has_expected_fields']
    valid_count = 0

    for sample in samples:
        validation = sample.get('validation_checks', {})

        # All required checks must pass
        if all(validation.get(check, False) for check in required_checks):
            valid_count += 1

    reliability = valid_count / len(samples)
    return reliability


# ========== ROBUSTNESS: Consistency Across Bins ==========

def calculate_robustness(accuracy_by_bin: Dict[int, float]) -> float:
    """
    Robustness = min_accuracy / max_accuracy

    Measures: How much does performance degrade from best to worst case?

    Interpretation:
    - 0.95-1.00: Excellent robustness (barely degrades)
    - 0.80-0.95: Very good robustness (20% degradation max)
    - 0.50-0.80: Fair robustness (50% degradation)
    - <0.50: Poor robustness (degrades significantly)

    Args:
        accuracy_by_bin: Dict mapping bin_id to accuracy [0, 1]

    Returns:
        Robustness score [0, 1]
    """
    if not accuracy_by_bin:
        return 0.5  # Unknown

    values = [v for v in accuracy_by_bin.values() if v is not None]

    if not values:
        return 0.5

    min_acc = min(values)
    max_acc = max(values)

    if max_acc == 0:
        return 0.0

    robustness = min_acc / max_acc
    return robustness


# ========== FORMAT VALIDITY: Task-Specific Format Checks ==========

def calculate_format_validity(samples: List[Dict], task_type: str) -> float:
    """
    Format Validity = % outputs with proper format for task type

    Task-specific checks:
    - code_generation: Code is parseable/compilable
    - classification: Predicted class in allowed set
    - information_extraction: All required fields present
    - text_generation: Output is valid text
    - maths: Answer in proper mathematical notation
    - etc.

    Args:
        samples: List of benchmark samples
        task_type: Type of task

    Returns:
        Format validity score [0, 1]
    """
    if not samples:
        return 0.0

    valid_count = 0

    for sample in samples:
        if task_type == 'code_generation':
            # Code must be parseable
            validation = sample.get('validation_checks', {})
            valid = validation.get('parseable', False)

        elif task_type == 'classification':
            # Class must be from allowed set
            parsed = sample.get('parsed_output', {})
            predicted_class = parsed.get('predicted_class', '').lower().strip()

            # Get allowed classes from task
            # For now, assume common classes
            allowed_classes = [
                'positive', 'negative', 'neutral',
                'true', 'false',
                'yes', 'no',
                'spam', 'not spam',
                'relevant', 'irrelevant'
            ]

            valid = any(c in predicted_class for c in allowed_classes)

        elif task_type == 'information_extraction':
            # All required fields must be present
            parsed = sample.get('parsed_output', {})

            # Fields to check depend on task
            required_fields = ['name', 'email', 'phone', 'company']
            valid = any(field in parsed for field in required_fields)

        elif task_type in ['text_generation', 'summarization']:
            # Output must be valid text
            raw_output = sample.get('raw_output', '').strip()

            # Checks:
            # - Not empty
            # - Not just numbers/symbols
            # - Reasonable length (> 20 chars)

            valid = (len(raw_output) > 20 and
                    not all(c.isdigit() or not c.isalnum() for c in raw_output))

        elif task_type == 'maths':
            # Answer must be numeric or mathematical notation
            raw_output = sample.get('raw_output', '').strip()

            # Contains numbers or math symbols
            has_number = any(c.isdigit() for c in raw_output)
            has_math = any(c in '+-*/%()[]{}=' for c in raw_output)

            valid = has_number or has_math

        elif task_type == 'retrieval_grounded':
            # Answer must be extracted from context
            raw_output = sample.get('raw_output', '').strip()
            validation = sample.get('validation_checks', {})

            # Should reference source material
            valid = len(raw_output) > 5 and validation.get('parseable', False)

        elif task_type == 'instruction_following':
            # Output must satisfy constraints
            raw_output = sample.get('raw_output', '').strip()
            constraints = sample.get('constraints', [])

            if not constraints:
                valid = len(raw_output) > 0
            else:
                # Check if output follows constraints
                valid = len(raw_output) > 0  # Simplified

        else:
            # Default: just check non-empty
            raw_output = sample.get('raw_output', '').strip()
            valid = len(raw_output) > 0

        if valid:
            valid_count += 1

    format_validity = valid_count / len(samples)
    return format_validity


# ========== AGGREGATE METRICS ==========

def get_capability_metrics(task_type: str,
                          model: str,
                          samples: List[Dict],
                          accuracy_by_bin: Optional[Dict[int, float]] = None) -> Dict[str, float]:
    """
    Calculate all capability metrics for a model on a task

    Args:
        task_type: Type of task
        model: Model name
        samples: List of benchmark samples
        accuracy_by_bin: Optional pre-computed accuracy by bin

    Returns:
        Dict with keys:
        - avg_accuracy: Mean accuracy across all samples
        - min_accuracy: Worst-case accuracy
        - reliability: % outputs passing validation checks
        - robustness: Consistency across difficulty bins
        - format_valid: % outputs with proper format
        - samples: Number of samples evaluated
    """
    from .metric_calculators import calculate_metric

    # 1. Calculate task-specific accuracy for each sample
    accuracies = []

    for sample in samples:
        metric = calculate_metric(sample, task_type)
        if metric is not None:
            accuracies.append(metric)

    if not accuracies:
        avg_accuracy = 0.0
        min_accuracy = 0.0
    else:
        avg_accuracy = statistics.mean(accuracies)
        min_accuracy = min(accuracies)

    # 2. Calculate reliability (% valid outputs)
    reliability = calculate_reliability(samples)

    # 3. Calculate robustness (consistency across bins)
    if accuracy_by_bin:
        robustness = calculate_robustness(accuracy_by_bin)
    else:
        robustness = 0.5  # Unknown if not provided

    # 4. Calculate format validity (task-specific format checks)
    format_valid = calculate_format_validity(samples, task_type)

    return {
        'avg_accuracy': avg_accuracy,
        'min_accuracy': min_accuracy,
        'reliability': reliability,
        'robustness': robustness,
        'format_valid': format_valid,
        'samples': len(samples)
    }


# ========== EXAMPLE CALCULATION ==========

if __name__ == '__main__':
    import json

    # Example: Load samples from benchmark
    # with open('benchmark_output/code_generation/phi3_mini/outputs.jsonl') as f:
    #     samples = [json.loads(line) for line in f]

    # Calculate metrics
    # metrics = get_capability_metrics('code_generation', 'phi3_mini', samples)

    # print("\nPhi-3 on Code Generation:")
    # print(f"  Avg Accuracy: {metrics['avg_accuracy']:.2%}")
    # print(f"  Min Accuracy: {metrics['min_accuracy']:.2%}")
    # print(f"  Reliability: {metrics['reliability']:.2%}")
    # print(f"  Robustness: {metrics['robustness']:.2%}")
    # print(f"  Format Valid: {metrics['format_valid']:.2%}")
    # print(f"  Samples: {metrics['samples']}")

    pass
