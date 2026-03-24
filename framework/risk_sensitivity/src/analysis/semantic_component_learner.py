#!/usr/bin/env python3
"""
Semantic Component Learner

Learn SDDF components using SEMANTIC failures (not syntactic)
Combines semantic verification with component correlation analysis
"""

import json
from pathlib import Path
from typing import Dict, List
import statistics
import numpy as np
from scipy import stats as scipy_stats


class SemanticComponentLearner:
    """Learn SDDF components from semantic ground truth"""

    def __init__(self):
        self.task_types = [
            "code_generation",
            "maths",
        ]

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

    def load_samples_with_semantic_verification(self, task_type: str, model: str, max_samples: int = 100) -> List[Dict]:
        """
        Load samples with SDDF vectors AND semantic verification results
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from core.sddf_complexity_calculator import SDDFComplexityCalculator
        from semantic_verifier import SemanticVerifier

        calculator = SDDFComplexityCalculator()
        verifier = SemanticVerifier()

        outputs = calculator.load_outputs(task_type, model)

        if not outputs:
            return []

        results = []
        for i, sample in enumerate(outputs[:max_samples]):
            try:
                sddf_vector = calculator.calculate_sddf_vector(sample, task_type)
                composite_complexity = calculator.calculate_composite_complexity(sddf_vector)

                # Semantic verification
                verification = verifier.verify_sample(task_type, sample)

                # Semantic failure: True if NOT semantically correct
                semantic_failure = not verification.get('semantic_correct', False) \
                    if verification['semantic_verifiable'] else None

                results.append({
                    'task_type': task_type,
                    'model': model,
                    'sample_id': i,
                    'sddf_vector': sddf_vector,
                    'composite_complexity': composite_complexity,
                    'semantic_failure': semantic_failure,  # Ground truth: semantic
                    'semantic_verifiable': verification['semantic_verifiable'],
                    'verification': verification,
                })
            except:
                continue

        return results

    def compute_semantic_component_correlation(self, component_name: str, samples: List[Dict]) -> Dict:
        """
        Compute correlation between component value and SEMANTIC failure rate

        Only uses samples where semantic_failure is known (not None)
        """
        component_values = []
        failures = []

        for s in samples:
            if s['semantic_failure'] is None:
                continue  # Skip samples where we can't verify

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
            return {'component': component_name, 'error': f'Insufficient verifiable samples: {len(component_values)}'}

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
            'total_verifiable': len(component_values),
        }

    def analyze_task_semantic_component_correlations(self, task_type: str) -> Dict:
        """
        Analyze which components correlate with SEMANTIC failure for a task
        Aggregate across all models
        """
        all_samples = []

        for model in self.models:
            samples = self.load_samples_with_semantic_verification(task_type, model)
            all_samples.extend(samples)

        if not all_samples:
            return {'task': task_type, 'error': 'No samples found'}

        # Filter to only verifiable samples
        verifiable_samples = [s for s in all_samples if s['semantic_failure'] is not None]

        if not verifiable_samples:
            return {'task': task_type, 'error': 'No semantically verifiable samples'}

        correlations = {}
        for component in ['R', 'Gamma', 'alpha']:
            corr_data = self.compute_semantic_component_correlation(component, all_samples)
            correlations[component] = corr_data

        # Aggregate failure rates
        total_failures = sum(1 for s in verifiable_samples if s['semantic_failure'])
        total_verifiable = len(verifiable_samples)

        return {
            'task': task_type,
            'total_samples': len(all_samples),
            'verifiable_samples': total_verifiable,
            'total_failures': total_failures,
            'semantic_failure_rate': total_failures / total_verifiable if total_verifiable > 0 else 0.0,
            'correlations': correlations,
        }

    def learn_all_task_components(self) -> Dict:
        """Learn components for all verifiable tasks"""
        results = {}

        for task in self.task_types:
            print(f"Analyzing semantic component correlations for {task}...")
            results[task] = self.analyze_task_semantic_component_correlations(task)

        return results

    def print_semantic_component_analysis(self, results: Dict) -> str:
        """Generate readable semantic component analysis report"""
        report = []
        report.append("\n" + "=" * 120)
        report.append("SDDF COMPONENT LEARNING FROM SEMANTIC FAILURES")
        report.append("=" * 120)

        for task_type, task_data in results.items():
            if 'error' in task_data:
                report.append(f"\n{task_type.upper()}: {task_data['error']}")
                continue

            report.append(f"\n{task_type.upper()}")
            report.append("-" * 120)
            report.append(f"  Total Samples: {task_data['total_samples']}")
            report.append(f"  Semantically Verifiable: {task_data['verifiable_samples']}")
            report.append(f"  Semantic Failures: {task_data['total_failures']} ({task_data['semantic_failure_rate']*100:.1f}%)")
            report.append(f"\n  Component Correlations with SEMANTIC Failure:")

            for comp_name in ['R', 'Gamma', 'alpha']:
                comp_data = task_data['correlations'].get(comp_name, {})

                if 'error' in comp_data:
                    report.append(f"    {comp_name}: {comp_data['error']}")
                    continue

                corr = comp_data.get('correlation', 0.0)
                p_val = comp_data.get('p_value', 1.0)
                mean_fail = comp_data.get('mean_when_fail', 0.0)
                mean_pass = comp_data.get('mean_when_pass', 0.0)
                n_verifiable = comp_data.get('total_verifiable', 0)

                sig = "***" if p_val < 0.01 else "**" if p_val < 0.05 else "*" if p_val < 0.1 else ""

                report.append(f"    {comp_name}: (based on {n_verifiable} verifiable samples)")
                report.append(f"      Correlation: {corr:+.3f} {sig}")
                report.append(f"      p-value: {p_val:.4f}")
                report.append(f"      Mean when FAILURE: {mean_fail:.3f}")
                report.append(f"      Mean when SUCCESS: {mean_pass:.3f}")
                if corr > 0:
                    report.append(f"      Interpretation: Higher {comp_name} = More failures")
                elif corr < 0:
                    report.append(f"      Interpretation: Higher {comp_name} = Fewer failures")
                else:
                    report.append(f"      Interpretation: No correlation")

        return "\n".join(report)


if __name__ == "__main__":
    learner = SemanticComponentLearner()

    # Analyze all tasks using semantic ground truth
    print("Learning SDDF components from semantic failures...\n")
    results = learner.learn_all_task_components()

    # Print report
    report = learner.print_semantic_component_analysis(results)
    print(report)

    # Save results
    output_file = Path("semantic_component_learning_results.json")
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
