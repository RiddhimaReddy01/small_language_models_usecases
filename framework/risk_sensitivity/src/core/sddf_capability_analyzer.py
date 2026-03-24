#!/usr/bin/env python3
"""
SDDF Capability Analyzer

Mirror of risk analyzer but for accuracy/capability curves.
Computes task-specific accuracy vs difficulty and detects capability degradation points.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import statistics
import math
from .sddf_complexity_calculator import SDDFComplexityCalculator
from ..metrics.metric_calculators import calculate_metric


class SDDFCapabilityAnalyzer:
    """Analyze task-specific accuracy using SDDF complexity framework"""

    def __init__(self, n_bins: int = 5, bin_std: float = None, spike_threshold: float = 0.1):
        """
        Args:
            n_bins: Number of difficulty bins
            bin_std: Standard deviation for Gaussian soft assignment
                     If None, loads from learned_sddf_weights.json (default: 0.500001)
            spike_threshold: Minimum curvature to detect inflection (default 0.1 = 10%)
        """
        self.calculator = SDDFComplexityCalculator()
        self.n_bins = n_bins
        self.bin_std = bin_std or self._load_learned_bin_std()
        self.spike_threshold = spike_threshold

        # Model configuration
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

        # Task-specific accuracy metrics
        self.task_accuracy_metrics = {
            'text_generation': 'rouge_l',          # ROUGE-L score
            'code_generation': 'pass_at_1',        # Pass@1 (binary)
            'classification': 'f1_score',          # F1 score
            'maths': 'exact_match',                # Exact match (binary)
            'summarization': 'rouge_l',            # ROUGE-L
            'retrieval_grounded': 'exact_match',   # Exact match
            'instruction_following': 'constraint_satisfaction_rate',  # % constraints satisfied
            'information_extraction': 'field_accuracy',  # % fields correct
        }

    def _load_learned_bin_std(self) -> float:
        """Load optimized bin_std from learned weights file"""
        # Navigate to risk_sensitivity/data/config/
        base_dir = Path(__file__).parent.parent.parent
        weights_file = base_dir / "data/config/learned_sddf_weights.json"

        if weights_file.exists():
            try:
                with open(weights_file) as f:
                    data = json.load(f)
                    return data.get('bin_std', 1.0)
            except:
                pass

        return 1.0

    # ========== ACCURACY EXTRACTION ==========

    def extract_task_accuracy(self, sample: Dict, task_type: str) -> Optional[float]:
        """
        Extract task-specific accuracy metric from sample
        Returns: float in [0, 1] or None if not available

        Uses actual task metrics calculated from output:
        - code_generation: Pass@1 (does code execute?)
        - text_generation: ROUGE-L (longest common subsequence overlap)
        - classification: F1 (precision-recall harmonic mean)
        - maths: exact_match (answer exactly correct?)
        - summarization: ROUGE-L (overlap with reference)
        - retrieval_grounded: F1 (token-level overlap)
        - instruction_following: constraint_satisfaction (% instructions followed)
        - information_extraction: field_accuracy (% fields extracted correctly)
        """
        try:
            # Step 1: Try to calculate actual task metric
            metric_value = calculate_metric(sample, task_type)
            if metric_value is not None:
                return float(metric_value)

            # Step 2: If metric calculation failed, try to extract from pre-calculated 'metrics' field
            if 'metrics' in sample:
                metrics = sample['metrics']
                metric_name = self.task_accuracy_metrics.get(task_type)
                if metric_name and metric_name in metrics:
                    return float(metrics[metric_name])

            # Step 3: Fallback to validation-based accuracy
            # This is NOT task accuracy, just output validity
            validation = sample.get('validation_checks', {})
            required_checks = ['non_empty', 'parseable', 'has_expected_fields']
            all_pass = all(validation.get(check, False) for check in required_checks)

            # Return as validation success rate (not actual task accuracy)
            return 1.0 if all_pass else 0.0

        except Exception:
            return None

    # ========== PROBABILITY MAPPINGS ==========

    def complexity_to_bin(self, complexity_score: float) -> int:
        """
        Map continuous complexity score to discrete bin using self.n_bins
        complexity in [0, 1] -> bin in [0, n_bins-1]
        """
        bin_id = int(complexity_score * (self.n_bins - 1))
        return min(max(bin_id, 0), self.n_bins - 1)

    # ========== CAPABILITY CURVE COMPUTATION ==========

    def compute_capability_curve(self, samples_with_complexity: List[Dict],
                                 task_type: str) -> Dict[int, Optional[float]]:
        """
        Compute P(correct_answer | bin) using self.n_bins
        For each bin:
        - Find samples in that bin
        - Calculate mean task-specific accuracy
        - Capability[bin] = mean_accuracy_in_bin
        """
        bin_accuracies = {b: {'total': 0, 'accuracy_sum': 0.0} for b in range(self.n_bins)}

        # Assign samples to bins and accumulate accuracy
        for sample in samples_with_complexity:
            complexity = sample['composite_complexity']
            bin_id = self.complexity_to_bin(complexity)

            accuracy = self.extract_task_accuracy(sample, task_type)

            if accuracy is not None:
                bin_accuracies[bin_id]['total'] += 1
                bin_accuracies[bin_id]['accuracy_sum'] += accuracy

        # Compute mean accuracy per bin
        capability_curve = {}
        for b in range(self.n_bins):
            total = bin_accuracies[b]['total']
            accuracy_sum = bin_accuracies[b]['accuracy_sum']

            if total > 0:
                capability_curve[b] = accuracy_sum / total
            else:
                capability_curve[b] = None

        return capability_curve

    # ========== DEGRADATION DETECTION ==========

    def find_degradation_point(self, bins: List[int], accuracies: List[float]) -> Optional[int]:
        """
        Find degradation point (inflection point) in capability curve

        For 2+ points: Uses second derivative (curvature) to find where accuracy drops sharply
        Returns bin where accuracy degrades significantly
        """
        if len(accuracies) < 2:
            return None

        # For 2 points: check if there's a sharp drop
        if len(accuracies) == 2:
            drop = accuracies[0] - accuracies[1]
            if drop > 0.15:  # Significant drop threshold
                return bins[1]
            return None

        # For 3+ points: use second derivative
        # Calculate first derivative (slope)
        slopes = []
        for i in range(1, len(accuracies)):
            if accuracies[i] is not None and accuracies[i-1] is not None:
                slope = accuracies[i] - accuracies[i-1]
                slopes.append((bins[i], slope))

        if len(slopes) < 2:
            return None

        # Find maximum negative acceleration (steepest drop)
        max_drop_idx = 0
        max_drop = 0

        for i in range(1, len(slopes)):
            slope_drop = slopes[i-1][1] - slopes[i][1]  # How much more negative
            if slope_drop > max_drop:
                max_drop = slope_drop
                max_drop_idx = i

        # Only mark degradation if there's significant drop (>10%)
        if max_drop > 0.1:
            return slopes[max_drop_idx][0]

        return None

    # ========== COMPREHENSIVE ANALYSIS ==========

    def analyze_task_model(self, task_type: str, model: str,
                          samples_with_complexity: List[Dict]) -> Dict:
        """
        Complete capability analysis for task/model combination
        """
        if not samples_with_complexity:
            return {
                'task': task_type,
                'model': model,
                'error': 'No samples'
            }

        # Compute capability curve
        capability_curve = self.compute_capability_curve(samples_with_complexity, task_type)

        # Get valid bins and accuracies
        valid_bins = [b for b in capability_curve.keys() if capability_curve[b] is not None]
        valid_accuracies = [capability_curve[b] for b in valid_bins]

        # Find degradation point
        tau_capability = self.find_degradation_point(valid_bins, valid_accuracies) if valid_accuracies else None

        # Compute statistics
        avg_accuracy = statistics.mean(valid_accuracies) if valid_accuracies else 0.0
        min_accuracy = min(valid_accuracies) if valid_accuracies else 0.0
        max_accuracy = max(valid_accuracies) if valid_accuracies else 0.0

        return {
            'task': task_type,
            'model': model,
            'label': self.model_labels.get(model, model),
            'total_samples': len(samples_with_complexity),
            'capability_curve': capability_curve,
            'tau_capability': tau_capability,  # Degradation point
            'avg_accuracy': avg_accuracy,
            'min_accuracy': min_accuracy,
            'max_accuracy': max_accuracy,
            'accuracy_range': max_accuracy - min_accuracy,
        }

    def analyze_all_tasks_existing(self, results_with_complexity: Dict) -> Dict:
        """
        Analyze capability for all 8 tasks × 4 models
        Input: results from calculate_from_existing_results.py (with complexity vectors)
        """
        results = {}

        for task_type in self.calculator.task_types:
            print(f"\n{task_type.upper()}")
            results[task_type] = {}

            for model in self.models:
                # Get samples with complexity for this task/model
                # (In practice, this comes from previous SDDF analysis)
                print(f"  Analyzing {model}...")

                # Placeholder: would be filled from SDDF results
                results[task_type][model] = {
                    'task': task_type,
                    'model': model,
                    'pending': 'Waiting for SDDF results'
                }

        return results

    def print_capability_report(self, results: Dict) -> str:
        """Print summary report"""
        report = []
        report.append("\n" + "=" * 140)
        report.append("SDDF CAPABILITY ANALYSIS - FROM EXISTING BENCHMARK RESULTS")
        report.append("=" * 140)

        for task_type, models_data in results.items():
            report.append(f"\n{task_type.upper()}")
            report.append("-" * 140)

            for model, analysis in models_data.items():
                if 'error' in analysis:
                    report.append(f"  {self.model_labels.get(model, model)}: {analysis['error']}")
                    continue

                model_label = analysis.get('label', model)
                report.append(f"\n  {model_label}")
                report.append(f"    Total Samples: {analysis.get('total_samples', 0)}")
                report.append(f"    Avg Accuracy: {analysis.get('avg_accuracy', 0):.3f}")
                report.append(f"    Min Accuracy: {analysis.get('min_accuracy', 0):.3f}")
                report.append(f"    Max Accuracy: {analysis.get('max_accuracy', 0):.3f}")
                report.append(f"    Accuracy Range: {analysis.get('accuracy_range', 0):.3f}")

                # Accuracy by bin
                report.append(f"    Capability Curve by Bin:")
                cap_curve = analysis.get('capability_curve', {})
                for bin_id in sorted(cap_curve.keys()):
                    accuracy = cap_curve[bin_id]
                    if accuracy is not None:
                        report.append(f"      Bin {bin_id}: Accuracy={accuracy:.3f}")

                # Degradation point
                tau_cap = analysis.get('tau_capability')
                if tau_cap is not None:
                    report.append(f"    **DEGRADATION POINT (tau_capability): Bin {tau_cap}**")
                else:
                    report.append(f"    No significant degradation detected (stable performance)")

        report.append("\n" + "=" * 140)

        return "\n".join(report)


if __name__ == "__main__":
    analyzer = SDDFCapabilityAnalyzer()
    print("SDDF Capability Analyzer - Ready to analyze task-specific accuracy curves")
