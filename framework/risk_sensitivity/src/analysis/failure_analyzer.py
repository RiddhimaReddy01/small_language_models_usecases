#!/usr/bin/env python3
"""
Semantic Failure Analyzer

Categorize and analyze failure types:
- Syntactic failures: Format/parsing errors
- Semantic failures: Incorrect answers (inaccuracy, hallucination, incomplete)
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import re


class FailureAnalyzer:
    """Categorize semantic vs syntactic failures from benchmark data"""

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

    def classify_failure_type(self, sample: Dict) -> Dict:
        """
        Classify failure into semantic vs syntactic categories

        Returns:
            {
                'is_failure': bool,
                'failure_type': str,  # NONE, SYNTACTIC, SEMANTIC
                'category': str,      # Specific category
                'evidence': str,      # Why we think this
            }
        """
        if sample.get('valid'):
            return {
                'is_failure': False,
                'failure_type': 'NONE',
                'category': 'PASS',
                'evidence': 'All validation checks passed'
            }

        # Sample failed validation
        checks = sample.get('validation_checks', {})
        error_msg = sample.get('error', '')

        # SYNTACTIC failures: Format/parsing issues
        if not checks.get('parseable'):
            return {
                'is_failure': True,
                'failure_type': 'SYNTACTIC',
                'category': 'PARSE_ERROR',
                'evidence': f"Output not parseable: {error_msg}"
            }

        if not checks.get('non_empty'):
            return {
                'is_failure': True,
                'failure_type': 'SYNTACTIC',
                'category': 'EMPTY_OUTPUT',
                'evidence': 'Output is empty or whitespace-only'
            }

        if not checks.get('has_expected_fields'):
            return {
                'is_failure': True,
                'failure_type': 'SYNTACTIC',
                'category': 'MISSING_FIELDS',
                'evidence': 'Required output fields are missing'
            }

        # If we reach here with valid=False but checks pass, it's ambiguous
        # Treat as SEMANTIC (likely incorrect answer that passed format check)
        return {
            'is_failure': True,
            'failure_type': 'SEMANTIC',
            'category': 'INACCURACY',
            'evidence': f'Semantic validation failed: {error_msg}'
        }

    def analyze_task_failures(self, task_type: str, model: str, max_samples: int = 100) -> Dict:
        """Analyze all failure types for a task/model combination"""
        benchmark_dir = self.get_benchmark_dir(task_type)
        output_file = benchmark_dir / task_type / model / "outputs.jsonl"

        if not output_file.exists():
            return {'error': f'No outputs found: {output_file}'}

        failures_by_type = defaultdict(lambda: defaultdict(int))
        samples_analyzed = 0

        try:
            with open(output_file) as f:
                for i, line in enumerate(f):
                    if i >= max_samples:
                        break

                    try:
                        sample = json.loads(line)
                        classification = self.classify_failure_type(sample)

                        failure_type = classification['failure_type']
                        category = classification['category']

                        failures_by_type[failure_type][category] += 1
                        samples_analyzed += 1
                    except:
                        continue
        except Exception as e:
            return {'error': str(e)}

        # Compute statistics
        total = samples_analyzed
        syntactic = sum(failures_by_type['SYNTACTIC'].values())
        semantic = sum(failures_by_type['SEMANTIC'].values())
        passed = failures_by_type['NONE']['PASS']

        return {
            'task': task_type,
            'model': model,
            'total_samples': total,
            'passed': passed,
            'syntactic_failures': syntactic,
            'semantic_failures': semantic,
            'syntactic_rate': syntactic / total if total > 0 else 0.0,
            'semantic_rate': semantic / total if total > 0 else 0.0,
            'pass_rate': passed / total if total > 0 else 0.0,
            'failure_categories': dict(failures_by_type),
        }

    def analyze_all_tasks(self, max_samples: int = 100) -> Dict:
        """Analyze failure types across all tasks and models"""
        results = {}

        for task in self.task_types:
            results[task] = {}

            for model in self.models:
                print(f"  Analyzing {task}/{model}...")
                results[task][model] = self.analyze_task_failures(task, model, max_samples)

        return results

    def print_failure_analysis(self, results: Dict) -> str:
        """Generate readable failure analysis report"""
        report = []
        report.append("\n" + "=" * 120)
        report.append("SEMANTIC vs SYNTACTIC FAILURE ANALYSIS")
        report.append("=" * 120)

        for task_type, task_results in results.items():
            report.append(f"\n{task_type.upper()}")
            report.append("-" * 120)

            for model, analysis in task_results.items():
                if 'error' in analysis:
                    report.append(f"  {model}: {analysis['error']}")
                    continue

                report.append(f"\n  {model}:")
                report.append(f"    Samples: {analysis['total_samples']}")
                report.append(f"    Passed: {analysis['passed']} ({analysis['pass_rate']*100:.1f}%)")
                report.append(f"    Syntactic Failures: {analysis['syntactic_failures']} ({analysis['syntactic_rate']*100:.1f}%)")
                report.append(f"    Semantic Failures: {analysis['semantic_failures']} ({analysis['semantic_rate']*100:.1f}%)")

                # Breakdown
                categories = analysis['failure_categories']
                if categories.get('SYNTACTIC'):
                    report.append(f"      Syntactic breakdown:")
                    for cat, count in categories['SYNTACTIC'].items():
                        report.append(f"        - {cat}: {count}")

                if categories.get('SEMANTIC'):
                    report.append(f"      Semantic breakdown:")
                    for cat, count in categories['SEMANTIC'].items():
                        report.append(f"        - {cat}: {count}")

        return "\n".join(report)

    def get_summary_table(self, results: Dict) -> str:
        """Generate summary table: Pass Rate vs Failure Types"""
        lines = []
        lines.append("\n" + "=" * 140)
        lines.append("SUMMARY TABLE: Semantic vs Syntactic Failures")
        lines.append("=" * 140)
        lines.append(f"{'Task':<25} {'Model':<30} {'Samples':<10} {'Pass %':<10} {'Syntactic %':<15} {'Semantic %':<15}")
        lines.append("-" * 140)

        for task_type, task_results in results.items():
            for model, analysis in sorted(task_results.items()):
                if 'error' in analysis:
                    continue

                task_col = task_type[:24]
                model_col = model[:29]
                samples = analysis['total_samples']
                pass_pct = analysis['pass_rate'] * 100
                syn_pct = analysis['syntactic_rate'] * 100
                sem_pct = analysis['semantic_rate'] * 100

                lines.append(f"{task_col:<25} {model_col:<30} {samples:<10} {pass_pct:>7.1f}%  {syn_pct:>10.1f}%      {sem_pct:>10.1f}%")

        return "\n".join(lines)


if __name__ == "__main__":
    analyzer = FailureAnalyzer()

    print("Analyzing failure types across all tasks...")
    results = analyzer.analyze_all_tasks(max_samples=100)

    # Print detailed report
    report = analyzer.print_failure_analysis(results)
    print(report)

    # Print summary table
    summary = analyzer.get_summary_table(results)
    print(summary)

    # Save results
    output_file = Path("failure_analysis_results.json")
    with open(output_file, 'w') as f:
        # Convert defaultdicts to regular dicts for JSON serialization
        serializable = {}
        for task, task_data in results.items():
            serializable[task] = {}
            for model, analysis in task_data.items():
                if 'error' not in analysis:
                    analysis['failure_categories'] = dict(analysis['failure_categories'])
                serializable[task][model] = analysis

        json.dump(serializable, f, indent=2)

    print(f"\n\nResults saved to {output_file}")
