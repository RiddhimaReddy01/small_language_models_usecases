#!/usr/bin/env python3
"""
Results Reporter: Generate 6 formatted tables showing model performance for each task

Tables:
1. Capability Metrics: Accuracy, robustness, reliability, format validity
2. Operational Metrics: Latency, throughput, cost, memory, tier
3. Degradation Analysis: Capability tipping points (tau_capability)
4. Risk Analysis: Risk sensitivity and failure patterns
5. Task-Specific Metrics: Task-specific performance metrics
6. Cost-Benefit Analysis: Routing recommendations and trade-offs
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import csv


class ResultsReporter:
    """Generate formatted performance reports for model evaluation results"""

    def __init__(self, task_type: str, analysis_results: Dict[str, Dict]):
        """
        Args:
            task_type: Type of task (e.g., 'code_generation', 'classification')
            analysis_results: Results from SDDF analysis, keyed by model name
        """
        self.task_type = task_type
        self.analysis_results = analysis_results
        self.models = list(analysis_results.keys())

    def _format_header(self, title: str, width: int = 100) -> str:
        """Format a centered header with separator line"""
        sep = "=" * width
        title_line = f" {title} "
        centered = title_line.center(width, "=")
        return f"{sep}\n{centered}\n{sep}"

    def _format_metric(self, value: Any, format_type: str = 'percent') -> str:
        """Format a metric value for display"""
        if value is None:
            return "N/A"

        if format_type == 'percent':
            return f"{value:.2%}" if isinstance(value, (int, float)) else str(value)
        elif format_type == 'float':
            return f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
        elif format_type == 'int':
            return f"{int(value)}" if isinstance(value, (int, float)) else str(value)
        else:
            return str(value)

    # ========== TABLE 1: CAPABILITY METRICS ==========

    def print_capability_metrics(self) -> str:
        """
        Table 1: Task Capability Metrics
        Shows: Avg Accuracy, Min Accuracy, Reliability, Robustness, Format Validity
        """
        lines = []
        lines.append(self._format_header(f"TABLE 1: Task Capability Metrics - {self.task_type.upper()}"))
        lines.append("")

        # Header
        header = "Model                    Avg Acc     Min Acc  Reliability  Robustness  Format  Samples"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for model in self.models:
            results = self.analysis_results[model]

            avg_acc = results.get('capability', {}).get('avg_accuracy', 0.0)
            min_acc = results.get('capability', {}).get('min_accuracy', 0.0)
            reliability = results.get('reliability', 0.0)
            robustness = results.get('robustness', 0.0)
            format_valid = results.get('format_valid', 0.0)
            samples = results.get('capability', {}).get('samples', 0)

            model_display = model[:24].ljust(24)
            line = (f"{model_display} {self._format_metric(avg_acc):>10s} "
                   f"{self._format_metric(min_acc):>8s} "
                   f"{self._format_metric(reliability):>12s} "
                   f"{self._format_metric(robustness):>11s} "
                   f"{self._format_metric(format_valid):>7s} "
                   f"{self._format_metric(samples, 'int'):>7s}")
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    # ========== TABLE 2: OPERATIONAL METRICS ==========

    def print_operational_metrics(self) -> str:
        """
        Table 2: Operational Metrics
        Shows: Latency, Throughput, Cost, Memory, Tier
        """
        lines = []
        lines.append(self._format_header(f"TABLE 2: Operational Metrics - {self.task_type.upper()}", 110))
        lines.append("")

        # Header
        header = "Model                   Latency (ms)  Throughput    Cost/1M tok    Cost/hour  Memory (GB)  Tier"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for model in self.models:
            results = self.analysis_results[model]
            operational = results.get('operational', {})

            latency = operational.get('latency_ms', 'N/A')
            throughput = operational.get('throughput', 'N/A')
            cost_per_token = operational.get('cost_per_million_tokens', 'N/A')
            cost_per_hour = operational.get('cost_per_hour', 'N/A')
            memory = operational.get('memory_gb', 'N/A')
            tier = operational.get('tier', 'N/A')

            model_display = model[:24].ljust(24)
            latency_str = f"{latency:>12}" if isinstance(latency, str) else f"{latency:>12.0f}"
            throughput_str = f"{throughput:>13}" if isinstance(throughput, str) else f"{throughput:>13.1f}"
            cost_str = f"${cost_per_token:>10}" if isinstance(cost_per_token, str) else f"${cost_per_token:>10.2f}"
            cost_hour = f"${cost_per_hour:>8}" if isinstance(cost_per_hour, str) else f"${cost_per_hour:>8.2f}"
            memory_str = f"{memory:>10}" if isinstance(memory, str) else f"{memory:>10.1f}"

            line = f"{model_display} {latency_str} {throughput_str} {cost_str} {cost_hour} {memory_str}  {tier}"
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    # ========== TABLE 3: DEGRADATION ANALYSIS ==========

    def print_degradation_analysis(self) -> str:
        """
        Table 3: Degradation Analysis
        Shows: Tipping point (tau), capability at tipping point, risk at tipping point
        """
        lines = []
        lines.append(self._format_header(f"TABLE 3: Degradation Analysis - {self.task_type.upper()}", 100))
        lines.append("")

        # Header
        header = "Model                  tau_cap  Acc@tau  Risk@tau  Safe Bins    Degrades  Confidence"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for model in self.models:
            results = self.analysis_results[model]
            degradation = results.get('degradation', {})

            tau_cap = degradation.get('tau_capability', 'N/A')
            acc_at_tau = degradation.get('capability_at_tau', 0.0)
            risk_at_tau = degradation.get('risk_at_tau', 0.0)
            safe_bins = degradation.get('safe_bins', [])
            safe_bins_str = f"0-{safe_bins[-1]}" if safe_bins else "None"
            num_degrades = degradation.get('num_degradation_points', 0)
            confidence = degradation.get('confidence', 0.0)

            model_display = model[:22].ljust(22)
            tau_str = f"{tau_cap:>7}" if isinstance(tau_cap, str) else f"{tau_cap:>7.0f}"

            line = (f"{model_display} {tau_str}  {self._format_metric(acc_at_tau):>7s} "
                   f"{self._format_metric(risk_at_tau):>8s}  {safe_bins_str:<12s} {num_degrades:>8d}  "
                   f"{self._format_metric(confidence):>10s}")
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    # ========== TABLE 4: RISK ANALYSIS ==========

    def print_risk_analysis(self) -> str:
        """
        Table 4: Risk Sensitivity Analysis
        Shows: Average risk, peak risk, tipping point, trend, failure type
        """
        lines = []
        lines.append(self._format_header(f"TABLE 4: Risk Sensitivity - {self.task_type.upper()}", 120))
        lines.append("")

        # Header
        header = "Model                  Avg Risk  Peak Risk  tau_risk  Trend    Failure Type           Mitigation"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for model in self.models:
            results = self.analysis_results[model]
            risk = results.get('risk', {})

            avg_risk = risk.get('avg_risk', 0.0)
            peak_risk = risk.get('peak_risk', 0.0)
            tau_risk = risk.get('tau_risk', 'N/A')
            trend = risk.get('trend', 'Unknown')
            failure_type = risk.get('failure_type', 'Unknown')
            mitigation = risk.get('mitigation', 'No action')

            model_display = model[:22].ljust(22)
            tau_str = f"{tau_risk:>8}" if isinstance(tau_risk, str) else f"{tau_risk:>8.0f}"
            trend_str = trend[:9].ljust(9)
            failure_str = failure_type[:21].ljust(21)

            line = (f"{model_display} {self._format_metric(avg_risk):>8s}  "
                   f"{self._format_metric(peak_risk):>9s}  {tau_str}  {trend_str} "
                   f"{failure_str} {mitigation[:20]}")
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    # ========== TABLE 5: TASK-SPECIFIC METRICS ==========

    def print_task_specific_metrics(self) -> str:
        """
        Table 5: Task-Specific Performance Metrics
        Format varies by task type
        """
        lines = []
        lines.append(self._format_header(f"TABLE 5: Task-Specific Metrics - {self.task_type.upper()}"))
        lines.append("")

        if self.task_type == 'code_generation':
            header = "Model                 Pass@1     Compiles    Runs        Tests        Comments"
            lines.append(header)
            lines.append("-" * len(header))

            for model in self.models:
                results = self.analysis_results[model]
                task_metrics = results.get('task_specific', {})

                pass_at_1 = task_metrics.get('pass_at_1', 0.0)
                compiles = task_metrics.get('compilable', 0.0)
                runs = task_metrics.get('runnable', 0.0)
                tests = task_metrics.get('test_pass', 0.0)
                comments = task_metrics.get('notes', 'N/A')

                model_display = model[:21].ljust(21)
                line = (f"{model_display} {self._format_metric(pass_at_1):>10s} "
                       f"{self._format_metric(compiles):>11s} "
                       f"{self._format_metric(runs):>11s} "
                       f"{self._format_metric(tests):>12s}  {comments}")
                lines.append(line)

        elif self.task_type == 'classification':
            header = "Model                Accuracy   Precision   Recall       F1       Macro F1"
            lines.append(header)
            lines.append("-" * len(header))

            for model in self.models:
                results = self.analysis_results[model]
                task_metrics = results.get('task_specific', {})

                accuracy = task_metrics.get('accuracy', 0.0)
                precision = task_metrics.get('precision', 0.0)
                recall = task_metrics.get('recall', 0.0)
                f1 = task_metrics.get('f1', 0.0)
                macro_f1 = task_metrics.get('macro_f1', 0.0)

                model_display = model[:21].ljust(21)
                line = (f"{model_display} {self._format_metric(accuracy):>10s} "
                       f"{self._format_metric(precision):>11s} "
                       f"{self._format_metric(recall):>12s} "
                       f"{self._format_metric(f1):>8s}  {self._format_metric(macro_f1):>8s}")
                lines.append(line)

        elif self.task_type == 'text_generation':
            header = "Model                ROUGE-L    BLEU        Readability  Grammar"
            lines.append(header)
            lines.append("-" * len(header))

            for model in self.models:
                results = self.analysis_results[model]
                task_metrics = results.get('task_specific', {})

                rouge_l = task_metrics.get('rouge_l', 0.0)
                bleu = task_metrics.get('bleu', 0.0)
                readability = task_metrics.get('readability', 0.0)
                grammar = task_metrics.get('grammar', 0.0)

                model_display = model[:21].ljust(21)
                line = (f"{model_display} {rouge_l:>8.3f}    {bleu:>8.3f}      "
                       f"{self._format_metric(readability):>11s}  {self._format_metric(grammar):>7s}")
                lines.append(line)

        else:
            lines.append("No task-specific metrics defined for this task type")

        lines.append("")
        return "\n".join(lines)

    # ========== TABLE 6: COST-BENEFIT ANALYSIS ==========

    def print_cost_benefit_analysis(self) -> str:
        """
        Table 6: Cost-Benefit Analysis & Routing Recommendations
        Shows recommended models for different scenarios
        """
        lines = []
        lines.append(self._format_header(f"TABLE 6: Cost-Benefit Analysis & Recommendations - {self.task_type.upper()}", 100))
        lines.append("")

        # Header
        header = "Scenario                Recommended        Rationale            Cost Save  Quality"
        lines.append(header)
        lines.append("-" * len(header))

        # Get recommendations from results if available, otherwise use defaults
        scenarios = [
            ('Simple task (Bin 0)', 'select_cheapest'),
            ('Medium task (Bin 1)', 'select_balanced'),
            ('Hard task (Bin 2+)', 'select_most_capable'),
            ('Critical system', 'select_most_capable'),
            ('Cost-sensitive', 'select_cheapest'),
            ('Mixed workload', 'select_balanced'),
        ]

        for scenario, recommendation_type in scenarios:
            # Find recommended model based on type
            if recommendation_type == 'select_cheapest':
                recommended = min(self.models,
                                key=lambda m: self.analysis_results[m].get('operational', {}).get('cost_per_hour', float('inf')))
            elif recommendation_type == 'select_most_capable':
                recommended = max(self.models,
                                key=lambda m: self.analysis_results[m].get('capability', {}).get('avg_accuracy', 0))
            else:  # balanced
                recommended = self.models[len(self.models) // 2] if self.models else 'N/A'

            # Get metrics for recommended model
            if isinstance(recommended, str) and recommended != 'N/A':
                results = self.analysis_results.get(recommended, {})
                cost_save = results.get('operational', {}).get('cost_per_hour', 0)
                quality = results.get('capability', {}).get('avg_accuracy', 0)
            else:
                cost_save = 0
                quality = 0

            scenario_display = scenario[:24].ljust(24)
            recommended_display = str(recommended)[:20].ljust(20)
            rationale_map = {
                'select_cheapest': 'Lowest cost option',
                'select_most_capable': 'Highest accuracy',
                'select_balanced': 'Best overall balance',
            }
            rationale = rationale_map.get(recommendation_type, 'Unknown')
            rationale_display = rationale[:20].ljust(20)

            line = (f"{scenario_display} {recommended_display} {rationale_display} "
                   f"{self._format_metric(cost_save, 'float'):>10s}  {self._format_metric(quality):>7s}")
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    # ========== AGGREGATE REPORT ==========

    def print_full_report(self) -> str:
        """Generate all 6 tables in a single report"""
        report_parts = [
            self.print_capability_metrics(),
            self.print_operational_metrics(),
            self.print_degradation_analysis(),
            self.print_risk_analysis(),
            self.print_task_specific_metrics(),
            self.print_cost_benefit_analysis(),
        ]
        return "\n".join(report_parts)

    # ========== EXPORT FUNCTIONS ==========

    def save_report(self, output_path: Path) -> Path:
        """Save full report to text file"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(self.print_full_report())

        return output_path

    def save_as_json(self, output_path: Path) -> Path:
        """Export metrics as JSON"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)

        return output_path

    def save_as_csv(self, output_path: Path) -> Path:
        """Export capability metrics as CSV"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for model in self.models:
            results = self.analysis_results[model]
            capability = results.get('capability', {})
            operational = results.get('operational', {})

            row = {
                'Model': model,
                'Avg Accuracy': capability.get('avg_accuracy', 0.0),
                'Min Accuracy': capability.get('min_accuracy', 0.0),
                'Reliability': results.get('reliability', 0.0),
                'Robustness': results.get('robustness', 0.0),
                'Format Valid': results.get('format_valid', 0.0),
                'Latency (ms)': operational.get('latency_ms', 0),
                'Cost/Hour': operational.get('cost_per_hour', 0),
                'Memory (GB)': operational.get('memory_gb', 0),
                'Samples': capability.get('samples', 0),
            }
            rows.append(row)

        if rows:
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        return output_path


# ========== EXAMPLE USAGE ==========

if __name__ == '__main__':
    # Example: Load analysis results and generate reports
    results_file = 'results_from_existing.json'

    if Path(results_file).exists():
        with open(results_file) as f:
            all_results = json.load(f)

        # Generate reports for each task
        for task_type, task_results in all_results.items():
            print(f"\n{'='*100}")
            print(f"Generating report for: {task_type}")
            print(f"{'='*100}\n")

            reporter = ResultsReporter(task_type, task_results)

            # Print to console
            print(reporter.print_full_report())

            # Save to files
            Path('reports').mkdir(exist_ok=True)
            reporter.save_report(Path(f'reports/{task_type}_report.txt'))
            reporter.save_as_json(Path(f'reports/{task_type}_metrics.json'))
            reporter.save_as_csv(Path(f'reports/{task_type}_metrics.csv'))

            print(f"\n✓ Report saved to reports/{task_type}_report.txt")
