#!/usr/bin/env python3
"""
Run complete SDDF-based risk sensitivity analysis
"""

import json
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import SDDFComplexityCalculator, SDDFRiskAnalyzer
from src.reporting import ResultsReporter
from src.visualization import SDDFCurvePlotter


def main():
    print("\n" + "=" * 120)
    print("SDDF-BASED RISK SENSITIVITY ANALYSIS")
    print("=" * 120)

    # Initialize components
    calculator = SDDFComplexityCalculator()
    analyzer = SDDFRiskAnalyzer()
    visualizer = SDDFCurvePlotter()

    # Run analysis
    print("\nStep 1: Calculating SDDF complexity vectors...")
    print("-" * 120)

    print("\nStep 2: Computing risk curves for all tasks and models...")
    print("-" * 120)
    results = analyzer.analyze_all_tasks(max_samples=100)

    # Print report
    print(analyzer.print_analysis_report(results))

    # Save results to JSON
    print("\n\nStep 3: Saving results...")
    print("-" * 120)

    output_file = Path('risk_sensitivity/results.json')
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
                    'risk_curve': {int(k): v for k, v in analysis['risk_curve'].items()},
                    'capability_curve': {int(k): v for k, v in analysis['capability_curve'].items()},
                }

    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)

    print(f"Saved: {output_file}")

    # Generate visualizations
    print("\n\nStep 4: Generating visualizations...")
    print("-" * 120)
    saved_plots = visualizer.save_all_visualizations(results)

    # Print summary
    print("\n\n" + "=" * 120)
    print("ANALYSIS COMPLETE")
    print("=" * 120)

    print("\nKey Findings:")
    print("-" * 120)

    for task_type in analyzer.calculator.task_types:
        task_results = results.get(task_type, {})

        print(f"\n{task_type.upper()}")

        # Find best model (lowest failure rate)
        best_model = None
        best_failure_rate = float('inf')

        for model, analysis in task_results.items():
            if 'error' not in analysis:
                if analysis['failure_rate'] < best_failure_rate:
                    best_failure_rate = analysis['failure_rate']
                    best_model = model

        if best_model:
            best_label = analyzer.model_labels.get(best_model, best_model)
            print(f"  Best Model: {best_label} ({best_failure_rate*100:.1f}% failure rate)")

        # Show spike points
        spikes = []
        for model, analysis in task_results.items():
            if 'error' not in analysis and analysis['spike_bin'] is not None:
                model_label = analyzer.model_labels.get(model, model)
                spikes.append(f"{model_label} (Bin {analysis['spike_bin']})")

        if spikes:
            print(f"  Risk Spikes: {', '.join(spikes)}")

    print("\n" + "=" * 120)
    print(f"Results saved to: risk_sensitivity/")
    print(f"  - results.json (numerical data)")
    print(f"  - plots/ (visualizations)")
    print("=" * 120)


if __name__ == "__main__":
    main()
