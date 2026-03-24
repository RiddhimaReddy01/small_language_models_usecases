#!/usr/bin/env python3
"""
SDDF Component Learner

Learn task-specific values for R (reasoning depth), |Gamma| (constraint count),
and α (parametric dependence) by analyzing correlation between component values
and semantic failure rates.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import statistics
import numpy as np
from scipy import stats as scipy_stats


class ComponentLearner:
    """Learn SDDF components from ground truth semantic failure data"""

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

        # Models to analyze (excluding Mixtral due to 100% failure)
        self.models = [
            'qwen2.5_1.5b',
            'phi3_mini',
            'tinyllama_1.1b',
            'llama_llama-3.3-70b-versatile',
        ]

    def get_benchmark_dir(self, task_type: str) -> Path:
        """Navigate to benchmark directory"""
        base_dir = Path(__file__).parent.parent.parent.parent.parent

        if task_type == 'text_generation':
            return base_dir / "data/benchmark/benchmark_output_fixed"
        elif task_type in ['code_generation', 'summarization']:
            return base_dir / "data/benchmark/benchmark_output_fixed_all"
        else:
            return base_dir / "data/benchmark/benchmark_output"

    def load_samples_with_sddf(self, task_type: str, model: str, max_samples: int = 100) -> List[Dict]:
        """Load samples with SDDF vectors and validation info"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.sddf_complexity_calculator import SDDFComplexityCalculator

        calculator = SDDFComplexityCalculator()
        outputs = calculator.load_outputs(task_type, model)

        if not outputs:
            return []

        results = []
        for i, sample in enumerate(outputs[:max_samples]):
            try:
                sddf_vector = calculator.calculate_sddf_vector(sample, task_type)
                composite_complexity = calculator.calculate_composite_complexity(sddf_vector)

                # Ground truth: semantic validity
                is_valid = sample.get('valid', False)
                semantic_failure = not is_valid

                results.append({
                    'task_type': task_type,
                    'model': model,
                    'sample_id': i,
                    'sddf_vector': sddf_vector,
                    'composite_complexity': composite_complexity,
                    'semantic_failure': semantic_failure,  # Ground truth
                    'validation_checks': sample.get('validation_checks', {}),
                })
            except:
                continue

        return results

    def compute_component_correlation(self, component_name: str, samples: List[Dict]) -> Dict:
        """
        Compute correlation between component value and semantic failure rate

        Returns:
            {
                'component': str,
                'correlation': float,
                'p_value': float,
                'mean_when_fail': float,
                'mean_when_pass': float,
            }
        """
        component_values = []
        failures = []

        for s in samples:
            sddf_vec = s['sddf_vector']

            # Map component name to SDDF vector key
            if component_name == 'R':
                val = sddf_vec['R']
            elif component_name == 'Gamma':
                val = sddf_vec['constraint_count']
            elif component_name == 'alpha':
                val = sddf_vec['alpha']
            else:
                continue

            component_values.append(val)
            failures.append(1 if s['semantic_failure'] else 0)

        if len(component_values) < 10:
            return {'component': component_name, 'error': 'Insufficient samples'}

        # Compute Pearson correlation
        try:
            corr, p_value = scipy_stats.pearsonr(component_values, failures)
        except:
            corr, p_value = 0.0, 1.0

        # Separate by outcome
        fail_vals = [v for v, f in zip(component_values, failures) if f == 1]
        pass_vals = [v for v, f in zip(component_values, failures) if f == 0]

        mean_fail = statistics.mean(fail_vals) if fail_vals else 0.0
        mean_pass = statistics.mean(pass_vals) if pass_vals else 0.0

        return {
            'component': component_name,
            'correlation': corr,
            'p_value': p_value,
            'mean_when_fail': mean_fail,
            'mean_when_pass': mean_pass,
            'n_failures': len(fail_vals),
            'n_successes': len(pass_vals),
        }

    def analyze_task_component_correlations(self, task_type: str) -> Dict:
        """
        Analyze which components correlate with failure for a task
        Aggregate across all models
        """
        all_samples = []

        for model in self.models:
            samples = self.load_samples_with_sddf(task_type, model)
            all_samples.extend(samples)

        if not all_samples:
            return {'task': task_type, 'error': 'No samples found'}

        correlations = {}
        for component in ['R', 'Gamma', 'alpha']:
            corr_data = self.compute_component_correlation(component, all_samples)
            correlations[component] = corr_data

        # Aggregate failure rate
        total_failures = sum(1 for s in all_samples if s['semantic_failure'])
        total_samples = len(all_samples)

        return {
            'task': task_type,
            'total_samples': total_samples,
            'total_failures': total_failures,
            'failure_rate': total_failures / total_samples if total_samples > 0 else 0.0,
            'correlations': correlations,
        }

    def learn_all_task_components(self) -> Dict:
        """Learn components for all tasks"""
        results = {}

        for task in self.task_types:
            print(f"Analyzing component correlations for {task}...")
            results[task] = self.analyze_task_component_correlations(task)

        return results

    def print_component_analysis(self, results: Dict) -> str:
        """Generate readable component analysis report"""
        report = []
        report.append("\n" + "=" * 120)
        report.append("SDDF COMPONENT LEARNING ANALYSIS")
        report.append("=" * 120)

        for task_type, task_data in results.items():
            if 'error' in task_data:
                report.append(f"\n{task_type.upper()}: {task_data['error']}")
                continue

            report.append(f"\n{task_type.upper()}")
            report.append("-" * 120)
            report.append(f"  Samples: {task_data['total_samples']}")
            report.append(f"  Semantic Failures: {task_data['total_failures']} ({task_data['failure_rate']*100:.1f}%)")
            report.append(f"\n  Component Correlations with Semantic Failure:")

            for comp_name in ['R', 'Gamma', 'alpha']:
                comp_data = task_data['correlations'].get(comp_name, {})

                if 'error' in comp_data:
                    report.append(f"    {comp_name}: {comp_data['error']}")
                    continue

                corr = comp_data.get('correlation', 0.0)
                p_val = comp_data.get('p_value', 1.0)
                mean_fail = comp_data.get('mean_when_fail', 0.0)
                mean_pass = comp_data.get('mean_when_pass', 0.0)

                sig = "***" if p_val < 0.01 else "**" if p_val < 0.05 else "*" if p_val < 0.1 else ""

                report.append(f"    {comp_name}:")
                report.append(f"      Correlation: {corr:+.3f} {sig}")
                report.append(f"      p-value: {p_val:.4f}")
                report.append(f"      Mean when failure: {mean_fail:.3f}")
                report.append(f"      Mean when success: {mean_pass:.3f}")

        return "\n".join(report)


if __name__ == "__main__":
    learner = ComponentLearner()

    # Analyze all tasks
    results = learner.learn_all_task_components()

    # Print report
    report = learner.print_component_analysis(results)
    print(report)

    # Save results
    output_file = Path("component_learning_results.json")
    with open(output_file, 'w') as f:
        # Convert to serializable format
        serializable = {}
        for task, data in results.items():
            if 'error' not in data:
                data['correlations'] = {
                    k: {kk: vv for kk, vv in v.items() if kk != 'error'}
                    for k, v in data.get('correlations', {}).items()
                }
            serializable[task] = data

        json.dump(serializable, f, indent=2)

    print(f"\n\nResults saved to {output_file}")
