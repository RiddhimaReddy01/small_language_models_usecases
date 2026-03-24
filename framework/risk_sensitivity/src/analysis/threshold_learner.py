#!/usr/bin/env python3
"""
Threshold Learner - Compute Data-Driven Thresholds

Learns task-specific capability and risk thresholds from analysis results
"""

import json
from pathlib import Path
from typing import Dict, List
import statistics


class ThresholdLearner:
    """Learn task-specific decision thresholds from data"""

    def __init__(self):
        self.task_types = [
            "text_generation",
            "code_generation",
            "classification",
            "maths",
            "summarization",
            "retrieval_grounded",
            "instruction_following",
            "information_extraction"
        ]

    def compute_capability_threshold(self, capability_curves: List[Dict]) -> float:
        """
        Compute task-specific capability threshold

        Method: Find mean bin where models' capabilities drop below 0.8
        Returns: Data-driven capability threshold (0-1)

        Logic:
        - For each model, find bin where capability < 0.8
        - Average these "failure bins" across models
        - Smooth with slight adjustment
        """
        failure_bins = []

        for curve in capability_curves:
            # Normalize curve keys to integers (handles JSON string keys)
            normalized_curve = {int(k) if isinstance(k, str) else k: v
                               for k, v in curve.items()}
            valid_bins = sorted([b for b in normalized_curve.keys()
                                if normalized_curve[b] is not None])

            for bin_id in valid_bins:
                if normalized_curve[bin_id] < 0.8:
                    failure_bins.append(bin_id)
                    break

        if not failure_bins:
            # All models pass all bins - use 0.8 as default
            return 0.8

        # Mean failure bin - convert back to capability
        mean_fail_bin = statistics.mean(failure_bins)

        # Use mean failure bin to infer threshold
        # If models typically fail at bin 2, set threshold slightly higher
        # to catch that behavior
        if mean_fail_bin <= 1:
            return 0.85  # Higher threshold for early failures
        elif mean_fail_bin <= 2:
            return 0.80  # Standard threshold
        else:
            return 0.75  # Lower threshold for late failures (robust models)

    def compute_risk_threshold(self, risk_curves: List[Dict]) -> float:
        """
        Compute task-specific risk threshold

        Method: Find mean bin where models' risks exceed 0.3
        Returns: Data-driven risk threshold (0-1)

        Logic:
        - For each model, find bin where risk > 0.3
        - Average these "risk bins" across models
        - Adjust threshold accordingly
        """
        risk_bins = []

        for curve in risk_curves:
            # Normalize curve keys to integers (handles JSON string keys)
            normalized_curve = {int(k) if isinstance(k, str) else k: v
                               for k, v in curve.items()}
            valid_bins = sorted([b for b in normalized_curve.keys()
                                if normalized_curve[b] is not None])

            for bin_id in valid_bins:
                if normalized_curve[bin_id] > 0.3:
                    risk_bins.append(bin_id)
                    break

        if not risk_bins:
            # No models exceed 0.3 risk - use 0.3 as default
            return 0.3

        # Mean risk bin
        mean_risk_bin = statistics.mean(risk_bins)

        # Use mean risk bin to infer threshold
        if mean_risk_bin <= 1:
            return 0.25  # Lower threshold for early risk
        elif mean_risk_bin <= 2:
            return 0.30  # Standard threshold
        else:
            return 0.35  # Higher threshold for late risk (some robustness)

    def learn_task_thresholds(self, all_results: Dict) -> Dict[str, Dict[str, float]]:
        """
        Learn thresholds for all tasks from analysis results

        Args:
            all_results: {task: {model: {capability_curve: ..., risk_curve: ...}}}

        Returns:
            {task: {capability_threshold: float, risk_threshold: float}}
        """
        learned_thresholds = {}

        for task_type, task_results in all_results.items():
            print(f"Learning thresholds for {task_type}...")

            # Extract capability and risk curves from all models
            capability_curves = []
            risk_curves = []

            for model, analysis in task_results.items():
                if 'error' not in analysis:
                    cap_curve = analysis.get('capability_curve', {})
                    risk_curve = analysis.get('risk_curve', {})

                    if cap_curve:
                        capability_curves.append(cap_curve)
                    if risk_curve:
                        risk_curves.append(risk_curve)

            # Compute thresholds
            cap_thresh = self.compute_capability_threshold(capability_curves) if capability_curves else 0.8
            risk_thresh = self.compute_risk_threshold(risk_curves) if risk_curves else 0.3

            learned_thresholds[task_type] = {
                'capability_threshold': round(cap_thresh, 2),
                'risk_threshold': round(risk_thresh, 2),
            }

            print(f"  Capability threshold: {cap_thresh:.2f}")
            print(f"  Risk threshold: {risk_thresh:.2f}")

        return learned_thresholds

    def save_thresholds(self, thresholds: Dict, output_file: Path = None) -> Path:
        """
        Save learned thresholds to JSON file

        Args:
            thresholds: {task: {threshold_type: value}}
            output_file: Path to save JSON (default: data/config/learned_thresholds.json)

        Returns:
            Path where thresholds were saved
        """
        if output_file is None:
            # Default location
            base_dir = Path(__file__).parent.parent.parent
            output_file = base_dir / "data/config/learned_thresholds.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(thresholds, f, indent=2)

        print(f"\nSaved learned thresholds to {output_file}")
        return output_file

    def print_thresholds(self, thresholds: Dict) -> str:
        """Generate human-readable threshold report"""
        report = []
        report.append("\n" + "=" * 100)
        report.append("LEARNED THRESHOLDS (Data-Driven, Per-Task)")
        report.append("=" * 100)

        for task, values in thresholds.items():
            report.append(f"\n{task.upper()}")
            report.append(f"  Capability Threshold (tau_cau): {values['capability_threshold']}")
            report.append(f"  Risk Threshold (tau_risk): {values['risk_threshold']}")

        return "\n".join(report)


if __name__ == "__main__":
    # Example usage: Learn thresholds from previous analysis results
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Load previous analysis results
    results_file = Path("semantic_component_learning_results.json")

    if results_file.exists():
        print(f"Loading analysis results from {results_file}...")

        with open(results_file) as f:
            analysis_results = json.load(f)

        # Learn thresholds
        learner = ThresholdLearner()

        # Note: analysis_results structure different from what learner expects
        # This is a demonstration - would need full analysis results with
        # capability_curve and risk_curve for each task/model

        print("\nNote: Run this after full SDDF analysis to learn thresholds")
        print("Placeholder implementation shown above")
    else:
        print(f"Results file not found: {results_file}")
        print("\nTo learn thresholds:")
        print("1. Run full SDDF analysis: python3 scripts/run_sddf_analysis.py")
        print("2. Then run threshold learner with analysis results")
