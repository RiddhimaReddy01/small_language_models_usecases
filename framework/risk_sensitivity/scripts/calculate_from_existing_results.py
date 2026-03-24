#!/usr/bin/env python3
"""
Calculate SDDF Risk Sensitivity from Existing Benchmark Results

Uses already-collected benchmark data (no re-running inference)
Extracts SDDF complexity and risk curves from existing outputs
"""

import json
from pathlib import Path
from typing import Dict, List
import statistics
import sys
from pathlib import Path as PathlibPath

# Add parent directory to path for imports
sys.path.insert(0, str(PathlibPath(__file__).parent.parent))

from src.core import SDDFComplexityCalculator, SDDFRiskAnalyzer, SDDFCapabilityAnalyzer


class ExistingResultsAnalyzer:
    """Analyze risk sensitivity and capability from existing benchmark results"""

    def __init__(self, n_bins: int = 5, spike_threshold: float = 0.1,
                 sddf_components: str = 'all_6', normalization: str = 'zscore'):
        """
        Args:
            n_bins: Number of difficulty bins (hyperparameter)
            spike_threshold: Minimum curvature to detect degradation
            sddf_components: Which SDDF components to use ('all_6', 'top_3', 'weighted')
            normalization: How to normalize complexity ('zscore', 'percentile', 'minmax')
        """
        self.calculator = SDDFComplexityCalculator(
            sddf_components=sddf_components,
            normalization=normalization
        )
        self.analyzer = SDDFRiskAnalyzer(n_bins=n_bins, spike_threshold=spike_threshold)
        self.capability_analyzer = SDDFCapabilityAnalyzer(n_bins=n_bins, spike_threshold=spike_threshold)
        self.visualizer = SDDFVisualizer()
        self.n_bins = n_bins
        self.spike_threshold = spike_threshold
        self.sddf_components = sddf_components
        self.normalization = normalization

    def get_benchmark_dir(self, task_type: str) -> Path:
        """Get correct benchmark directory (relative to project root, not risk_sensitivity/)"""
        # Go up one level from risk_sensitivity/ to project root
        base_dir = Path(__file__).parent.parent

        if task_type == 'text_generation':
            return base_dir / "benchmark_output_fixed"
        elif task_type in ['code_generation', 'summarization']:
            return base_dir / "benchmark_output_fixed_all"
        else:
            return base_dir / "benchmark_output"

    def load_all_outputs(self, task_type: str, model: str) -> List[Dict]:
        """Load ALL outputs for task/model (not limited by max_samples)"""
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

    def analyze_from_existing(self, task_type: str, model: str) -> Dict:
        """
        Analyze single task/model using existing benchmark results
        (ALL samples, not limited)
        """
        # Load all existing outputs
        outputs = self.load_all_outputs(task_type, model)

        if not outputs:
            return {
                'task': task_type,
                'model': model,
                'error': f'No outputs found for {task_type}/{model}'
            }

        print(f"  Loaded {len(outputs)} samples from {task_type}/{model}")

        # Create samples with SDDF vectors
        samples_with_complexity = []

        for i, output in enumerate(outputs):
            try:
                sddf_vector = self.calculator.calculate_sddf_vector(output, task_type)
                composite_complexity = self.calculator.calculate_composite_complexity(sddf_vector)

                samples_with_complexity.append({
                    'task_type': task_type,
                    'model': model,
                    'sample_id': i,
                    'sddf_vector': sddf_vector,
                    'composite_complexity': composite_complexity,
                    'raw_input': output.get('raw_input', ''),
                    'raw_output': output.get('raw_output', ''),
                    'bin': output.get('bin'),
                    'validation_checks': output.get('validation_checks', {}),
                })
            except:
                continue

        if not samples_with_complexity:
            return {
                'task': task_type,
                'model': model,
                'error': 'Could not process any samples'
            }

        print(f"    Processed {len(samples_with_complexity)} samples with SDDF vectors")

        # ===== RISK ANALYSIS (P(semantic_failure | bin)) =====
        risk_curve = self.analyzer.compute_risk_curve(samples_with_complexity)

        # Find spike point with fallbacks for robust models
        valid_bins = [b for b in risk_curve.keys() if risk_curve[b] is not None]
        valid_risks = [risk_curve[b] for b in valid_bins]

        spike_bin = None
        spike_type = None

        if valid_risks:
            # Try primary: curvature-based spike detection
            spike_bin = self.analyzer.find_spike_point(valid_bins, valid_risks)
            spike_type = 'curvature'

            # Fallback 1: If no spike, find threshold-based boundary (risk > 30%)
            if spike_bin is None:
                spike_bin = self.analyzer.find_risk_threshold_bin(valid_bins, valid_risks, threshold=0.3)
                spike_type = 'threshold_30%'

            # Fallback 2: If still no spike, find max risk bin
            if spike_bin is None:
                spike_bin = self.analyzer.find_max_risk_bin(valid_bins, valid_risks)
                spike_type = 'max_risk'
                # Only mark if risk is non-trivial (> 5%)
                if spike_bin is not None:
                    max_risk_val = risk_curve[spike_bin]
                    if max_risk_val < 0.05:
                        spike_bin = None  # Too robust, no warning needed
                        spike_type = None

        # Compute statistics
        total_failures = sum(1 for s in samples_with_complexity
                            if self.analyzer.check_semantic_failure({
                                'validation_checks': s['validation_checks']
                            }))

        avg_risk = statistics.mean(valid_risks) if valid_risks else 0.0

        # ===== CAPABILITY ANALYSIS (P(accuracy | bin), task-specific) =====
        capability_analysis = self.capability_analyzer.analyze_task_model(
            task_type, model, samples_with_complexity
        )

        # Extract task-specific accuracy metrics
        tau_capability = capability_analysis.get('tau_capability')
        avg_accuracy = capability_analysis.get('avg_accuracy', 0.0)
        min_accuracy = capability_analysis.get('min_accuracy', 0.0)
        max_accuracy = capability_analysis.get('max_accuracy', 0.0)
        accuracy_range = capability_analysis.get('accuracy_range', 0.0)
        task_capability_curve = capability_analysis.get('capability_curve', {})

        # Compute capability as 1 - risk (inverse of semantic failure)
        capability_curve = self.analyzer.compute_capability_curve(risk_curve)

        return {
            'task': task_type,
            'model': model,
            'label': self.analyzer.model_labels.get(model, model),
            'total_samples': len(samples_with_complexity),
            'total_failures': total_failures,
            'failure_rate': total_failures / len(samples_with_complexity) if samples_with_complexity else 0.0,
            'risk_curve': risk_curve,
            'capability_curve': capability_curve,
            'spike_bin': spike_bin,
            'spike_type': spike_type,  # How the risk boundary was detected
            'avg_risk': avg_risk,
            'avg_capability': 1.0 - avg_risk,
            'task_capability_curve': task_capability_curve,  # Task-specific accuracy per bin
            'tau_capability': tau_capability,  # Where accuracy degrades
            'avg_accuracy': avg_accuracy,  # Task-specific accuracy
            'min_accuracy': min_accuracy,
            'max_accuracy': max_accuracy,
            'accuracy_range': accuracy_range,
            'samples': samples_with_complexity,
        }

    def analyze_all_tasks_existing(self) -> Dict:
        """
        Analyze all 8 tasks × 4 models from existing results
        Uses ALL available samples (no sampling/limiting)
        """
        results = {}

        task_types = self.calculator.task_types
        models = self.analyzer.models

        for task_type in task_types:
            print(f"\n{task_type.upper()}")
            results[task_type] = {}

            for model in models:
                analysis = self.analyze_from_existing(task_type, model)
                results[task_type][model] = analysis

        return results

    def save_results(self, results: Dict, output_dir: str = None):
        """Save results to JSON"""
        if output_dir is None:
            # Save to same directory as this script
            output_dir = Path(__file__).parent
        else:
            output_dir = Path(output_dir)

        output_file = output_dir / 'results_from_existing.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        json_results = {}
        for task, models_data in results.items():
            json_results[task] = {}
            for model, analysis in models_data.items():
                if 'error' not in analysis:
                    json_results[task][model] = {
                        'total_samples': analysis['total_samples'],
                        'total_failures': analysis['total_failures'],
                        'failure_rate': analysis['failure_rate'],
                        'avg_risk': analysis['avg_risk'],
                        'avg_capability': analysis['avg_capability'],
                        'spike_bin': analysis['spike_bin'],
                        'spike_type': analysis.get('spike_type'),
                        'risk_curve': {int(k): v for k, v in analysis['risk_curve'].items()},
                        'capability_curve': {int(k): v for k, v in analysis['capability_curve'].items()},
                        'avg_accuracy': analysis['avg_accuracy'],
                        'min_accuracy': analysis['min_accuracy'],
                        'max_accuracy': analysis['max_accuracy'],
                        'accuracy_range': analysis['accuracy_range'],
                        'tau_capability': analysis['tau_capability'],
                        'task_capability_curve': {int(k): v for k, v in analysis['task_capability_curve'].items()},
                    }
                else:
                    json_results[task][model] = {'error': analysis['error']}

        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2)

        print(f"\nSaved: {output_file}")
        return json_results

    def extract_spike_and_cliff(self, analysis: Dict) -> Dict:
        """
        Extract spike and cliff (inflection) point details from analysis

        Returns:
            {
                'spike': {'bin': int, 'risk_before': float, 'risk_after': float, 'delta': float},
                'cliff': {'bin': int, 'acc_before': float, 'acc_after': float, 'delta': float}
            }
        """
        result = {'spike': None, 'cliff': None}

        # Extract spike (risk sensitivity)
        if analysis['spike_bin'] is not None:
            spike_bin = analysis['spike_bin']
            risk_curve = analysis['risk_curve']

            # Get risk before and after spike
            risk_before = risk_curve.get(spike_bin - 1) if spike_bin > 0 else None
            risk_after = risk_curve.get(spike_bin)

            if risk_before is not None and risk_after is not None:
                result['spike'] = {
                    'bin': spike_bin,
                    'risk_before': risk_before,
                    'risk_after': risk_after,
                    'delta': risk_after - risk_before,
                    'spike_type': analysis.get('spike_type')
                }

        # Extract cliff (capability degradation)
        if analysis['tau_capability'] is not None:
            cliff_bin = analysis['tau_capability']
            cap_curve = analysis['task_capability_curve']

            # Get accuracy before and after cliff
            acc_before = cap_curve.get(cliff_bin - 1) if cliff_bin > 0 else None
            acc_after = cap_curve.get(cliff_bin)

            if acc_before is not None and acc_after is not None:
                result['cliff'] = {
                    'bin': cliff_bin,
                    'accuracy_before': acc_before,
                    'accuracy_after': acc_after,
                    'delta': acc_before - acc_after,  # Should be positive (degradation)
                }

        return result

    def create_capability_metrics_table(self, results: Dict) -> str:
        """Create formatted table of capability metrics by task and model"""
        lines = []
        lines.append("\n" + "=" * 160)
        lines.append("CAPABILITY ANALYSIS - TASK-SPECIFIC ACCURACY METRICS")
        lines.append("=" * 160)

        for task_type in self.calculator.task_types:
            lines.append(f"\n{task_type.upper()}")
            lines.append("-" * 160)

            # Header
            lines.append(f"{'Model':<25} {'Avg Accuracy':<15} {'Min':<10} {'Max':<10} {'Range':<10} {'tau_capability':<18} {'Status':<15}")
            lines.append("-" * 160)

            task_results = results.get(task_type, {})

            for model in self.analyzer.models:
                analysis = task_results.get(model, {})

                if 'error' in analysis:
                    lines.append(f"{model:<25} ERROR: {analysis['error']}")
                    continue

                label = analysis.get('label', model)
                avg_acc = analysis.get('avg_accuracy', 0)
                min_acc = analysis.get('min_accuracy', 0)
                max_acc = analysis.get('max_accuracy', 0)
                acc_range = analysis.get('accuracy_range', 0)
                tau_cap = analysis.get('tau_capability')

                # Status
                if tau_cap is None:
                    if avg_acc > 0.9:
                        status = "EXCELLENT"
                    elif avg_acc > 0.7:
                        status = "GOOD"
                    else:
                        status = "FAIR"
                else:
                    status = f"DEGRADES @ Bin {tau_cap}"

                tau_cap_str = str(tau_cap) if tau_cap is not None else "None"
                lines.append(f"{label:<25} {avg_acc:>13.1%} {min_acc:>8.1%} {max_acc:>8.1%} {acc_range:>8.1%} {tau_cap_str:<18} {status:<15}")

        return "\n".join(lines)

    def create_risk_metrics_table(self, results: Dict) -> str:
        """Create formatted table of risk metrics by task and model"""
        lines = []
        lines.append("\n" + "=" * 160)
        lines.append("RISK SENSITIVITY - SEMANTIC FAILURE ANALYSIS")
        lines.append("=" * 160)

        for task_type in self.calculator.task_types:
            lines.append(f"\n{task_type.upper()}")
            lines.append("-" * 160)

            # Header
            lines.append(f"{'Model':<25} {'Avg Risk':<15} {'Max Risk':<15} {'Failure Rate':<15} {'tau_risk':<18} {'Spike Type':<18} {'Status':<15}")
            lines.append("-" * 160)

            task_results = results.get(task_type, {})

            for model in self.analyzer.models:
                analysis = task_results.get(model, {})

                if 'error' in analysis:
                    lines.append(f"{model:<25} ERROR: {analysis['error']}")
                    continue

                label = analysis.get('label', model)
                avg_risk = analysis.get('avg_risk', 0)
                failure_rate = analysis.get('failure_rate', 0)
                tau_risk = analysis.get('spike_bin')
                spike_type = analysis.get('spike_type', '')

                # Calculate max risk
                risk_curve = analysis.get('risk_curve', {})
                max_risk = max([v for v in risk_curve.values() if v is not None], default=0)

                # Status
                if tau_risk is None:
                    if avg_risk < 0.1:
                        status = "ROBUST"
                    elif avg_risk < 0.2:
                        status = "STABLE"
                    else:
                        status = "RISKY"
                else:
                    status = f"SPIKE @ Bin {tau_risk}"

                tau_risk_str = str(tau_risk) if tau_risk is not None else "None"
                spike_type_str = spike_type if spike_type else "-"
                lines.append(f"{label:<25} {avg_risk:>13.1%} {max_risk:>13.1%} {failure_rate:>13.1%} {tau_risk_str:<18} {spike_type_str:<18} {status:<15}")

        return "\n".join(lines)

    def create_operational_metrics_table(self, results: Dict) -> str:
        """Create operational metrics table (spike/cliff comparison)"""
        lines = []
        lines.append("\n" + "=" * 180)
        lines.append("OPERATIONAL METRICS - SPIKE & CLIFF ANALYSIS")
        lines.append("=" * 180)

        for task_type in self.calculator.task_types:
            lines.append(f"\n{task_type.upper()}")
            lines.append("-" * 180)

            # Header
            header = f"{'Model':<25} {'Spike Bin':<12} {'Risk Before->After':<25} {'Cliff Bin':<12} {'Accuracy Before->After':<30} {'Severity':<15}"
            lines.append(header)
            lines.append("-" * 180)

            task_results = results.get(task_type, {})

            for model in self.analyzer.models:
                analysis = task_results.get(model, {})

                if 'error' in analysis:
                    continue

                label = analysis.get('label', model)

                # Extract spike and cliff
                degradation = self.extract_spike_and_cliff(analysis)

                spike_info = ""
                cliff_info = ""
                severity = "NONE"

                if degradation['spike'] is not None:
                    s = degradation['spike']
                    spike_info = f"Bin {s['bin']}: {s['risk_before']:.1%}->{s['risk_after']:.1%}"

                if degradation['cliff'] is not None:
                    c = degradation['cliff']
                    cliff_info = f"Bin {c['bin']}: {c['accuracy_before']:.1%}->{c['accuracy_after']:.1%}"

                # Severity classification
                if degradation['spike'] and degradation['cliff']:
                    severity = "DUAL"
                elif degradation['spike']:
                    severity = "STRUCTURAL"
                elif degradation['cliff']:
                    severity = "ACCURACY"
                else:
                    severity = "NONE"

                lines.append(f"{label:<25} {spike_info:<25} {cliff_info:<30} {severity:<15}")

        return "\n".join(lines)

    def print_report(self, results: Dict):
        """Print summary report"""
        report = []
        report.append("\n" + "=" * 140)
        report.append("SDDF RISK & CAPABILITY ANALYSIS - FROM EXISTING BENCHMARK RESULTS")
        report.append("=" * 140)

        for task_type, models_data in results.items():
            report.append(f"\n{task_type.upper()}")
            report.append("-" * 140)

            for model, analysis in models_data.items():
                if 'error' in analysis:
                    report.append(f"  {self.analyzer.model_labels.get(model, model)}: {analysis['error']}")
                    continue

                model_label = analysis['label']
                report.append(f"\n  {model_label}")
                report.append(f"    Total Samples: {analysis['total_samples']}")
                report.append(f"    Semantic Failures: {analysis['total_failures']} ({analysis['failure_rate']*100:.1f}%)")
                report.append(f"")

                # Risk metrics
                report.append(f"    RISK SENSITIVITY (Semantic Failure Rate):")
                report.append(f"      Avg Risk: {analysis['avg_risk']:.3f}")
                report.append(f"      Avg Capability (1-Risk): {analysis['avg_capability']:.3f}")

                # Task-specific accuracy metrics
                report.append(f"    TASK-SPECIFIC ACCURACY:")
                report.append(f"      Avg Accuracy: {analysis['avg_accuracy']:.3f}")
                report.append(f"      Min Accuracy: {analysis['min_accuracy']:.3f}")
                report.append(f"      Max Accuracy: {analysis['max_accuracy']:.3f}")
                report.append(f"      Accuracy Range: {analysis['accuracy_range']:.3f}")

                # Degradation points
                report.append(f"    DEGRADATION POINTS:")
                if analysis['spike_bin'] is not None:
                    spike_type = analysis.get('spike_type', 'unknown')
                    report.append(f"      tau_risk: Bin {analysis['spike_bin']} ({spike_type})")
                else:
                    report.append(f"      tau_risk: None (robust)")

                if analysis['tau_capability'] is not None:
                    report.append(f"      tau_capability: Bin {analysis['tau_capability']} (accuracy degradation)")
                else:
                    report.append(f"      tau_capability: None (consistent accuracy)")

        report.append("\n" + "=" * 140)

        return "\n".join(report)


def main():
    print("\n" + "=" * 140)
    print("CALCULATE RISK SENSITIVITY & CAPABILITY FROM EXISTING BENCHMARK RESULTS")
    print("=" * 140)
    print("\nThis will use ALL existing benchmark outputs (no re-running inference)")
    print("Extracting SDDF complexity and computing risk + capability curves...")

    # Initialize with hyperparameters
    analyzer = ExistingResultsAnalyzer(n_bins=5, spike_threshold=0.1)

    # Analyze all tasks using existing results
    print("\nAnalyzing all 8 tasks × 4 models...")
    print("-" * 140)
    results = analyzer.analyze_all_tasks_existing()

    # Print comprehensive report
    report = analyzer.print_report(results)
    print(report)

    # Print metrics tables
    print("\n\n")
    print(analyzer.create_risk_metrics_table(results))

    print("\n\n")
    print(analyzer.create_capability_metrics_table(results))

    print("\n\n")
    print(analyzer.create_operational_metrics_table(results))

    # Save results
    json_results = analyzer.save_results(results)

    # Generate visualizations
    print("\n\nGenerating visualizations from existing results...")
    print("-" * 140)
    analyzer.visualizer.save_visualizations(results)

    # Summary
    print("\n\n" + "=" * 140)
    print("ANALYSIS COMPLETE")
    print("=" * 140)

    print("\nKey Findings by Task:")
    print("-" * 140)

    for task_type in analyzer.calculator.task_types:
        task_results = results.get(task_type, {})

        print(f"\n{task_type.upper()}")

        # Find best model (lowest failure rate)
        best_model = None
        best_failure_rate = float('inf')
        best_samples = 0

        for model, analysis in task_results.items():
            if 'error' not in analysis:
                if analysis['failure_rate'] < best_failure_rate:
                    best_failure_rate = analysis['failure_rate']
                    best_model = model
                    best_samples = analysis['total_samples']

        if best_model:
            best_label = analyzer.analyzer.model_labels.get(best_model, best_model)
            print(f"  Best Model: {best_label}")
            print(f"    Failure Rate: {best_failure_rate*100:.1f}% ({best_samples} samples)")

        # Show spike points (risk and capability)
        print(f"  Risk Spikes (tau_risk) & Accuracy Degradation (tau_capability):")
        for model, analysis in task_results.items():
            if 'error' not in analysis:
                model_label = analyzer.analyzer.model_labels.get(model, model)
                risk_info = "No spike (robust)"
                cap_info = "No degradation (consistent)"

                if analysis['spike_bin'] is not None:
                    risk_at_spike = analysis['risk_curve'].get(analysis['spike_bin'], 0)
                    spike_type = analysis.get('spike_type', 'unknown')
                    risk_info = f"Bin {analysis['spike_bin']} (risk={risk_at_spike:.3f}, {spike_type})"

                if analysis['tau_capability'] is not None:
                    acc_at_spike = analysis['task_capability_curve'].get(analysis['tau_capability'])
                    if acc_at_spike is not None:
                        cap_info = f"Bin {analysis['tau_capability']} (accuracy={acc_at_spike:.3f})"

                print(f"    {model_label}:")
                print(f"      Risk:       {risk_info}")
                print(f"      Accuracy:   {cap_info}")

    print("\n" + "=" * 140)
    print("Results saved to:")
    print("  - risk_sensitivity/results_from_existing.json")
    print("  - risk_sensitivity/plots/")
    print("=" * 140)


if __name__ == "__main__":
    main()
