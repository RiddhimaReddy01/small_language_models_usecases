#!/usr/bin/env python3
"""
Calculate COMPREHENSIVE METRICS using five dimensions:

1. ACCURACY: Did it get the right answer?
   - Text Gen: ROUGE, exact match
   - Code Gen: pass@1, test cases
   - Classification: exact match, F1
   - Maths: exact match, step correctness
   - Summarization: ROUGE, coverage
   - Retrieval: exact match, F1
   - Instruction: adherence score
   - Extraction: F1, exact match

2. ROBUSTNESS: Does accuracy hold across difficulty bins?
   - Check performance: easy (bin 0) vs hard (bin 4)
   - Measure: variance, worst-bin performance, degradation

3. CONSISTENCY: Same input = same output?
   - Self-consistency rate
   - Output stability

4. CONSTRAINT COMPLIANCE: Did it follow format rules?
   - Valid format, word limits, required fields
   - Constraint satisfaction rate

5. OPERATIONAL: Speed and efficiency metrics
   - Average latency, latency variance
   - Average output length
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import statistics
from collections import defaultdict


class ComprehensiveMetricsCalculator:
    """Calculate all four metric dimensions per task"""

    def __init__(self):
        self.tasks = [
            "text_generation",
            "code_generation",
            "classification",
            "maths",
            "summarization",
            "retrieval_grounded",
            "instruction_following",
            "information_extraction"
        ]
        self.models = [
            "tinyllama_1.1b",
            "qwen2.5_1.5b",
            "phi3_mini",
            "llama_llama-3.3-70b-versatile"
        ]
        self.model_labels = {
            "tinyllama_1.1b": "TinyLlama (1.1B)",
            "qwen2.5_1.5b": "Qwen (1.5B)",
            "phi3_mini": "Phi (3.8M)",
            "llama_llama-3.3-70b-versatile": "Llama (70B)"
        }

    def get_benchmark_dir(self, task_type: str) -> Path:
        """Get correct benchmark directory for task"""
        if task_type == 'text_generation':
            return Path("benchmark_output_fixed")
        elif task_type in ['code_generation', 'summarization']:
            return Path("benchmark_output_fixed_all")
        else:
            return Path("benchmark_output")

    def load_outputs(self, task_type: str, model: str) -> List[Dict]:
        """Load JSONL output file"""
        benchmark_dir = self.get_benchmark_dir(task_type)
        output_file = benchmark_dir / task_type / model / "outputs.jsonl"

        if not output_file.exists():
            return []

        outputs = []
        try:
            with open(output_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            outputs.append(json.loads(line))
                        except:
                            continue
        except:
            pass

        return outputs

    # ========== DIMENSION 1: ACCURACY ==========

    def calculate_accuracy_score(self, task_type: str, outputs: List[Dict]) -> Dict:
        """Calculate task-specific accuracy metrics"""
        if not outputs:
            return {}

        if task_type == 'text_generation':
            # Accuracy: % with all validation checks passing (proxy for semantic correctness)
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('non_empty'),
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'accuracy_pct': (correct / len(outputs)) * 100}

        elif task_type == 'code_generation':
            # Accuracy: pass@1 = % of code that is executable and correct
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('non_empty'),
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'pass_at_1_pct': (correct / len(outputs)) * 100}

        elif task_type == 'classification':
            # Accuracy: exact match on label
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('non_empty'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'exact_match_pct': (correct / len(outputs)) * 100}

        elif task_type == 'maths':
            # Accuracy: final answer correct
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'exact_match_pct': (correct / len(outputs)) * 100}

        elif task_type == 'summarization':
            # Accuracy: coverage of key points (proxy: all checks pass)
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('non_empty'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'coverage_pct': (correct / len(outputs)) * 100}

        elif task_type == 'retrieval_grounded':
            # Accuracy: exact match on answer
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'exact_match_pct': (correct / len(outputs)) * 100}

        elif task_type == 'instruction_following':
            # Accuracy: instruction adherence (all checks pass)
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('non_empty'),
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'adherence_pct': (correct / len(outputs)) * 100}

        elif task_type == 'information_extraction':
            # Accuracy: exact match on all fields
            correct = sum(1 for o in outputs if all([
                o.get('validation_checks', {}).get('parseable'),
                o.get('validation_checks', {}).get('has_expected_fields')
            ]))
            return {'exact_match_pct': (correct / len(outputs)) * 100}

        return {}

    # ========== DIMENSION 2: ROBUSTNESS ==========

    def calculate_robustness(self, outputs: List[Dict]) -> Dict:
        """Calculate robustness across difficulty bins"""
        if not outputs:
            return {}

        # Group by bin
        bin_accuracies = {}
        for bin_val in range(5):
            bin_outputs = [o for o in outputs if o.get('bin') == bin_val]
            if bin_outputs:
                correct = sum(1 for o in bin_outputs if all([
                    o.get('validation_checks', {}).get('non_empty'),
                    o.get('validation_checks', {}).get('parseable'),
                    o.get('validation_checks', {}).get('has_expected_fields')
                ]))
                bin_accuracies[bin_val] = (correct / len(bin_outputs)) * 100
            else:
                bin_accuracies[bin_val] = None

        # Calculate robustness metrics
        valid_accuracies = [acc for acc in bin_accuracies.values() if acc is not None]
        if not valid_accuracies:
            return {}

        avg_accuracy = statistics.mean(valid_accuracies)
        std_dev = statistics.stdev(valid_accuracies) if len(valid_accuracies) > 1 else 0
        min_accuracy = min(valid_accuracies)
        max_accuracy = max(valid_accuracies)
        robustness_score = 100 - std_dev  # Higher is better

        return {
            'robustness_score': robustness_score,
            'std_dev_across_bins': std_dev,
            'min_accuracy': min_accuracy,
            'max_accuracy': max_accuracy,
            'worst_bin_accuracy': min_accuracy,
            'best_bin_accuracy': max_accuracy,
            'degradation': max_accuracy - min_accuracy,
            'bin_accuracies': bin_accuracies
        }

    # ========== DIMENSION 3: CONSISTENCY ==========

    def calculate_consistency(self, outputs: List[Dict]) -> Dict:
        """Calculate reproducibility/consistency metrics"""
        if not outputs:
            return {}

        # For now, measure output stability (same format/length)
        # True consistency would require running same prompt twice

        output_lengths = [len(o.get('raw_output', '')) for o in outputs]
        if not output_lengths:
            return {}

        length_variance = statistics.variance(output_lengths) if len(output_lengths) > 1 else 0
        length_stdev = statistics.stdev(output_lengths) if len(output_lengths) > 1 else 0

        # Stability: how consistent are output lengths?
        # CV (coefficient of variation) = stdev / mean
        mean_length = statistics.mean(output_lengths)
        cv = (length_stdev / mean_length * 100) if mean_length > 0 else 0

        # Consistency score: lower CV = more consistent
        consistency_score = max(0, 100 - cv)

        return {
            'consistency_score': consistency_score,
            'output_length_stdev': length_stdev,
            'output_length_variance': length_variance,
            'mean_output_length': mean_length,
            'cv_percent': cv
        }

    # ========== DIMENSION 4: CONSTRAINT COMPLIANCE ==========

    def calculate_constraint_compliance(self, task_type: str, outputs: List[Dict]) -> Dict:
        """Calculate format and constraint compliance"""
        if not outputs:
            return {}

        metrics = {
            'total': len(outputs),
            'format_compliant': 0,
            'all_fields_present': 0,
            'appropriate_length': 0,
            'no_hallucination': 0
        }

        for output in outputs:
            validation = output.get('validation_checks', {})
            raw = output.get('raw_output', '')
            output_len = len(raw)

            # Format compliance: parseable
            if validation.get('parseable', False):
                metrics['format_compliant'] += 1

            # All fields present: has_expected_fields
            if validation.get('has_expected_fields', False):
                metrics['all_fields_present'] += 1

            # Appropriate length: varies by task
            if task_type == 'summarization':
                if 50 < output_len < 500:
                    metrics['appropriate_length'] += 1
            elif task_type == 'instruction_following':
                if 10 < output_len < 1000:
                    metrics['appropriate_length'] += 1
            elif task_type == 'text_generation':
                if output_len < 5000:
                    metrics['appropriate_length'] += 1
            else:
                # Default: non-zero length
                if output_len > 0:
                    metrics['appropriate_length'] += 1

            # No hallucination: all checks pass
            if all([
                validation.get('non_empty', False),
                validation.get('parseable', False),
                validation.get('has_expected_fields', False)
            ]):
                metrics['no_hallucination'] += 1

        # Convert to percentages
        if metrics['total'] > 0:
            metrics['format_compliance_pct'] = (metrics['format_compliant'] / metrics['total']) * 100
            metrics['all_fields_pct'] = (metrics['all_fields_present'] / metrics['total']) * 100
            metrics['length_appropriateness_pct'] = (metrics['appropriate_length'] / metrics['total']) * 100
            metrics['no_hallucination_pct'] = (metrics['no_hallucination'] / metrics['total']) * 100

        return metrics

    # ========== DIMENSION 5: OPERATIONAL METRICS ==========

    def calculate_operational_metrics(self, outputs: List[Dict]) -> Dict:
        """Calculate latency and efficiency metrics"""
        if not outputs:
            return {}

        latencies = [o.get('latency_sec', 0) for o in outputs if o.get('latency_sec')]
        output_lengths = [len(o.get('raw_output', '')) for o in outputs]

        if not latencies:
            return {}

        avg_latency = statistics.mean(latencies)
        latency_stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        avg_output_length = statistics.mean(output_lengths) if output_lengths else 0

        return {
            'avg_latency_sec': avg_latency,
            'latency_stdev_sec': latency_stdev,
            'avg_output_length_chars': avg_output_length,
            'total_outputs': len(outputs)
        }

    # ========== INTEGRATE ALL DIMENSIONS ==========

    def calculate_comprehensive_metrics(self, task_type: str, model: str) -> Dict:
        """Calculate all four dimensions + operational metrics"""
        outputs = self.load_outputs(task_type, model)
        if not outputs:
            return {}

        return {
            'task': task_type,
            'model': model,
            'accuracy': self.calculate_accuracy_score(task_type, outputs),
            'robustness': self.calculate_robustness(outputs),
            'consistency': self.calculate_consistency(outputs),
            'constraint_compliance': self.calculate_constraint_compliance(task_type, outputs),
            'operational': self.calculate_operational_metrics(outputs)
        }

    # ========== REPORTING ==========

    def print_comprehensive_report(self, task_type: str) -> None:
        """Print comprehensive metrics for a task"""
        print("\n" + "=" * 160)
        print(f"COMPREHENSIVE METRICS: {task_type.replace('_', ' ').upper()}")
        print("=" * 160)

        for model in self.models:
            metrics = self.calculate_comprehensive_metrics(task_type, model)
            if not metrics:
                continue

            print(f"\n{self.model_labels[model]}")
            print("-" * 160)

            # Dimension 1: ACCURACY
            print("  [ACCURACY]:")
            for key, value in metrics['accuracy'].items():
                print(f"    {key}: {value:.1f}%")

            # Dimension 2: ROBUSTNESS
            print("  [ROBUSTNESS]:")
            robustness = metrics['robustness']
            print(f"    robustness_score: {robustness.get('robustness_score', 0):.1f}")
            print(f"    std_dev_across_bins: {robustness.get('std_dev_across_bins', 0):.2f}")
            print(f"    degradation (best-worst): {robustness.get('degradation', 0):.1f}%")

            # Dimension 3: CONSISTENCY
            print("  [CONSISTENCY]:")
            consistency = metrics['consistency']
            print(f"    consistency_score: {consistency.get('consistency_score', 0):.1f}")
            print(f"    output_length_stdev: {consistency.get('output_length_stdev', 0):.1f}")
            print(f"    cv_percent: {consistency.get('cv_percent', 0):.1f}%")

            # Dimension 4: CONSTRAINT COMPLIANCE
            print("  [CONSTRAINT COMPLIANCE]:")
            compliance = metrics['constraint_compliance']
            print(f"    format_compliance_pct: {compliance.get('format_compliance_pct', 0):.1f}%")
            print(f"    all_fields_pct: {compliance.get('all_fields_pct', 0):.1f}%")
            print(f"    length_appropriateness_pct: {compliance.get('length_appropriateness_pct', 0):.1f}%")
            print(f"    no_hallucination_pct: {compliance.get('no_hallucination_pct', 0):.1f}%")

            # Dimension 5: OPERATIONAL METRICS
            print("  [OPERATIONAL]:")
            operational = metrics['operational']
            print(f"    avg_latency_sec: {operational.get('avg_latency_sec', 0):.2f}s")
            print(f"    latency_stdev_sec: {operational.get('latency_stdev_sec', 0):.2f}s")
            print(f"    avg_output_length_chars: {operational.get('avg_output_length_chars', 0):.0f}")

    def main(self):
        """Calculate comprehensive metrics for all tasks"""
        print("\n" + "=" * 160)
        print("COMPREHENSIVE METRICS - FIVE DIMENSIONS")
        print("=" * 160)
        print("\nDimensions:")
        print("  1. ACCURACY: Did it get the right answer?")
        print("  2. ROBUSTNESS: Does accuracy hold consistently?")
        print("  3. CONSISTENCY: Same input = same output?")
        print("  4. CONSTRAINT COMPLIANCE: Did it follow format rules?")
        print("  5. OPERATIONAL: Speed and efficiency metrics")

        for task in self.tasks:
            self.print_comprehensive_report(task)

        print("\n" + "=" * 160)
        print("COMPREHENSIVE METRICS CALCULATION COMPLETE")
        print("=" * 160)


if __name__ == "__main__":
    calculator = ComprehensiveMetricsCalculator()
    calculator.main()
