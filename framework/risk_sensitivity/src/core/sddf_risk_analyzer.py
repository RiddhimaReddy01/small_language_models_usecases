#!/usr/bin/env python3
"""
SDDF Risk Analyzer

Compute P(bin | complexity) and P(semantic_failure | bin)
Generate risk sensitivity curves with spike detection
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import statistics
import math
from .sddf_complexity_calculator import SDDFComplexityCalculator


class SDDFRiskAnalyzer:
    """Analyze risk using SDDF complexity framework"""

    def __init__(self, n_bins: int = 5, bin_std: float = None, spike_threshold: float = 0.1):
        """
        Args:
            n_bins: Number of difficulty bins (from config)
            bin_std: Standard deviation for Gaussian soft assignment
                     If None, loads from learned_sddf_weights.json (default: 0.500001)
            spike_threshold: Minimum curvature to detect spike (default 0.1 = 10%)
        """
        self.calculator = SDDFComplexityCalculator()
        self.n_bins = n_bins
        self.bin_std = bin_std or self._load_learned_bin_std()
        self.spike_threshold = spike_threshold

        # Model configurations (match actual benchmark data)
        self.models = [
            'qwen2.5_1.5b',
            'phi3_mini',
            'tinyllama_1.1b',
            'groq_mixtral-8x7b-32768',
            'llama_llama-3.3-70b-versatile',
        ]

        self.model_labels = {
            'qwen2.5_1.5b': 'Qwen 2.5 1.5B',
            'phi3_mini': 'Phi-3 Mini',
            'tinyllama_1.1b': 'TinyLlama 1.1B',
            'groq_mixtral-8x7b-32768': 'Mixtral 8x7B',
            'llama_llama-3.3-70b-versatile': 'Llama 3.3 70B',
        }

    def _load_learned_bin_std(self) -> float:
        """
        Load optimized bin_std from learned weights file

        ISSUE 15 FIX: Use centralized config for path
        """
        try:
            from .config import PATHS
            weights_file = PATHS['learned_weights']
        except ImportError:
            # Fallback if config import fails
            base_dir = Path(__file__).parent.parent.parent
            weights_file = base_dir / "data/config/learned_sddf_weights.json"

        if weights_file.exists():
            try:
                with open(weights_file) as f:
                    data = json.load(f)
                    return data.get('bin_std', 1.0)
            except Exception:
                pass

        # Fallback to default if not found
        return 1.0

    # ========== SEMANTIC FAILURE DETECTION ==========

    def check_semantic_failure(self, sample: Dict) -> bool:
        """
        Determine if sample has semantic failure
        Uses validation checks: all must pass for success
        """
        validation = sample.get('validation_checks', {})

        # Sample passes if all validation checks are true
        required_checks = ['non_empty', 'parseable', 'has_expected_fields']

        for check in required_checks:
            if not validation.get(check, False):
                return True  # If any check fails, it's a semantic failure

        return False  # All checks pass, no failure

    # ========== PROBABILITY MAPPINGS ==========

    def complexity_to_bin(self, complexity_score: float) -> int:
        """
        Map continuous complexity score to discrete bin using self.n_bins
        complexity in [0, 1] -> bin in [0, n_bins-1]
        """
        bin_id = int(complexity_score * (self.n_bins - 1))
        return min(max(bin_id, 0), self.n_bins - 1)

    def compute_bin_probabilities(self, complexity_score: float,
                                   num_bins: int = 5) -> Dict[int, float]:
        """
        Compute P(bin | complexity)
        Using gaussian distribution centered at mapped bin

        Returns probability for each bin
        """
        bin_probs = {}
        mapped_bin = complexity_score * (num_bins - 1)

        # Gaussian centered at mapped_bin with learned std dev
        sigma = self.bin_std
        total_prob = 0.0

        for b in range(num_bins):
            distance = abs(b - mapped_bin)
            prob = math.exp(-(distance ** 2) / (2 * sigma ** 2))
            bin_probs[b] = prob
            total_prob += prob

        # Normalize
        if total_prob > 0:
            for b in range(num_bins):
                bin_probs[b] /= total_prob

        return bin_probs

    # ========== RISK CURVE COMPUTATION ==========

    def compute_risk_curve(self, samples_with_complexity: List[Dict]) -> Dict[int, float]:
        """
        Compute P(semantic_failure | bin) using self.n_bins

        For each bin:
        - Find samples in that bin
        - Count semantic failures (model gave wrong answer)
        - Risk[bin] = failure_rate
        """
        bin_failures = {b: {'total': 0, 'failures': 0} for b in range(self.n_bins)}

        # Assign samples to bins based on complexity
        for sample in samples_with_complexity:
            complexity = sample['composite_complexity']
            bin_id = self.complexity_to_bin(complexity)

            has_failure = self.check_semantic_failure({
                'validation_checks': sample['validation_checks']
            })

            bin_failures[bin_id]['total'] += 1
            if has_failure:
                bin_failures[bin_id]['failures'] += 1

        # Compute risk per bin
        risk_curve = {}
        for b in range(self.n_bins):
            total = bin_failures[b]['total']
            failures = bin_failures[b]['failures']

            if total > 0:
                risk_curve[b] = failures / total
            else:
                risk_curve[b] = None

        return risk_curve

    def compute_aggregated_risk(self, complexity: float, risk_curve: Dict[int, float]) -> float:
        """
        Compute aggregated risk across all bins using soft assignment
        Risk(ξ) = Σ_bin P(semantic_failure | bin) × P(bin | ξ)

        Args:
            complexity: ξ(x) ∈ [0,1] (continuous difficulty score)
            risk_curve: {bin: P(failure|bin)}

        Returns: Aggregated risk in [0, 1]
        """
        bin_probs = self.compute_bin_probabilities(complexity, self.n_bins)
        aggregated_risk = 0.0

        for bin_id, bin_prob in bin_probs.items():
            risk = risk_curve.get(bin_id)
            if risk is not None:
                aggregated_risk += risk * bin_prob

        return aggregated_risk

    def compute_capability_curve(self, risk_curve: Dict[int, float]) -> Dict[int, float]:
        """
        Compute per-bin capability = 1 - risk
        Note: This is different from aggregated capability
        """
        capability_curve = {}
        for bin_id, risk in risk_curve.items():
            if risk is not None:
                capability_curve[bin_id] = 1.0 - risk
            else:
                capability_curve[bin_id] = None

        return capability_curve

    # ========== SPIKE DETECTION ==========

    def find_risk_threshold_bin(self, bins: List[int], risks: List[float],
                                 threshold: float = 0.3) -> Optional[int]:
        """
        Find first bin where risk exceeds threshold
        Used when no spike exists (flat curves)
        Returns bin where risk > threshold, or None if always safe
        """
        for bin_id, risk in zip(bins, risks):
            if risk is not None and risk > threshold:
                return bin_id
        return None

    def find_max_risk_bin(self, bins: List[int], risks: List[float]) -> Optional[int]:
        """
        Find bin with maximum risk
        Used as fallback when no spike detected
        """
        max_risk = -1
        max_bin = None
        for bin_id, risk in zip(bins, risks):
            if risk is not None and risk > max_risk:
                max_risk = risk
                max_bin = bin_id
        return max_bin

    def find_spike_point(self, bins: List[int], risks: List[float]) -> Optional[int]:
        """
        Find spike point (inflection point) in risk curve

        For 3+ points: Uses second derivative (curvature)
        For 2 points: Returns the bin with largest increase if delta > 0.3
        """
        if len(risks) < 2:
            return None

        # For 2 points: check if there's a sharp increase
        if len(risks) == 2:
            slope = risks[1] - risks[0]
            if slope > 0.3:  # Significant jump threshold
                return bins[1]
            return None

        # For 3+ points: use second derivative
        # Calculate first derivative (slope)
        slopes = []
        for i in range(1, len(risks)):
            if risks[i] is not None and risks[i-1] is not None:
                slope = risks[i] - risks[i-1]
                slopes.append((bins[i], slope))

        if len(slopes) < 2:
            return None

        # Find maximum slope increase (second derivative)
        max_increase_idx = 0
        max_increase = 0

        for i in range(1, len(slopes)):
            slope_increase = slopes[i][1] - slopes[i-1][1]
            if slope_increase > max_increase:
                max_increase = slope_increase
                max_increase_idx = i

        if max_increase > 0:
            return slopes[max_increase_idx][0]

        return None

    # ========== COMPREHENSIVE ANALYSIS ==========

    def analyze_task_model(self, task_type: str, model: str,
                          max_samples: int = 100) -> Dict:
        """
        Complete analysis for task/model combination

        Returns:
        {
            'task': str,
            'model': str,
            'total_samples': int,
            'total_failures': int,
            'failure_rate': float,
            'risk_curve': {bin: risk},
            'capability_curve': {bin: capability},
            'tau_risk': int or None,
            'spike_bin': int or None,
        }
        """
        # Calculate SDDF vectors
        samples = self.calculator.analyze_task(task_type, model, max_samples)

        if not samples:
            return {
                'task': task_type,
                'model': model,
                'error': 'No samples found'
            }

        # Count semantic failures
        total_failures = sum(1 for s in samples
                            if self.check_semantic_failure({
                                'validation_checks': s['validation_checks']
                            }))

        # Compute risk curves
        risk_curve = self.compute_risk_curve(samples)
        capability_curve = self.compute_capability_curve(risk_curve)

        # Find spike point
        valid_bins = [b for b in risk_curve.keys()
                      if risk_curve[b] is not None]
        valid_risks = [risk_curve[b] for b in valid_bins]

        spike_bin = self.find_spike_point(valid_bins, valid_risks) if valid_risks else None

        # Compute average risk
        avg_risk = statistics.mean([r for r in valid_risks if r is not None]) \
                   if valid_risks else 0.0

        return {
            'task': task_type,
            'model': model,
            'label': self.model_labels.get(model, model),
            'total_samples': len(samples),
            'total_failures': total_failures,
            'failure_rate': total_failures / len(samples) if samples else 0.0,
            'risk_curve': risk_curve,
            'capability_curve': capability_curve,
            'spike_bin': spike_bin,
            'avg_risk': avg_risk,
            'avg_capability': 1.0 - avg_risk,
            'samples': samples,
        }

    def analyze_all_tasks(self, max_samples: int = 100) -> Dict:
        """
        Analyze all 8 tasks across all 4 models
        """
        results = {}

        for task_type in self.calculator.task_types:
            results[task_type] = {}

            for model in self.models:
                analysis = self.analyze_task_model(task_type, model, max_samples)
                results[task_type][model] = analysis

        return results

    # ========== REPORTING ==========

    def print_analysis_report(self, results: Dict) -> str:
        """Generate human-readable risk analysis report"""
        report = []
        report.append("\n" + "=" * 120)
        report.append("SDDF-BASED RISK SENSITIVITY ANALYSIS")
        report.append("=" * 120)

        for task_type, models_data in results.items():
            report.append(f"\n{task_type.upper()}")
            report.append("-" * 120)

            for model, analysis in models_data.items():
                if 'error' in analysis:
                    report.append(f"  {self.model_labels.get(model, model)}: {analysis['error']}")
                    continue

                report.append(f"\n  {self.model_labels.get(model, model)}")
                report.append(f"    Samples: {analysis['total_samples']}")
                report.append(f"    Semantic Failures: {analysis['total_failures']} ({analysis['failure_rate']*100:.1f}%)")
                report.append(f"    Avg Risk: {analysis['avg_risk']:.3f}")
                report.append(f"    Avg Capability: {analysis['avg_capability']:.3f}")

                # Risk by bin
                report.append(f"    Risk Curve:")
                for bin_id in sorted(analysis['risk_curve'].keys()):
                    risk = analysis['risk_curve'][bin_id]
                    if risk is not None:
                        report.append(f"      Bin {bin_id}: {risk:.3f}")

                # Spike point
                if analysis['spike_bin'] is not None:
                    report.append(f"    Risk Spike (tau_risk): Bin {analysis['spike_bin']}")

        return "\n".join(report)


if __name__ == "__main__":
    analyzer = SDDFRiskAnalyzer()

    # Analyze a single task
    result = analyzer.analyze_task_model('text_generation', 'qwen2.5_1.5b', max_samples=50)

    print(f"\nTask: {result['task']}")
    print(f"Model: {result['label']}")
    print(f"Samples: {result['total_samples']}")
    print(f"Semantic Failures: {result['total_failures']} ({result['failure_rate']*100:.1f}%)")
    print(f"Avg Risk: {result['avg_risk']:.3f}")
    print(f"Avg Capability: {result['avg_capability']:.3f}")
    print(f"\nRisk Curve:")
    for bin_id, risk in result['risk_curve'].items():
        if risk is not None:
            print(f"  Bin {bin_id}: {risk:.3f}")
    print(f"\nRisk Spike (tau_risk): Bin {result['spike_bin']}")
