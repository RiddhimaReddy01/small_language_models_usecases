#!/usr/bin/env python3
"""
SDDF Curve Plotter

Generate capability curves and risk sensitivity curves for all models per task
with τ_cau (capability threshold) and τ_risk (risk threshold) markers
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import statistics


class SDDFCurvePlotter:
    """Plot SDDF analysis results with multiple models per task"""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            # Default: relative to project root
            output_dir = "outputs/plots"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Color palette for models
        self.colors = {
            'qwen2.5_1.5b': '#1f77b4',                    # Blue
            'phi3_mini': '#ff7f0e',                        # Orange
            'tinyllama_1.1b': '#2ca02c',                   # Green
            'groq_mixtral-8x7b-32768': '#d62728',          # Red
            'llama_llama-3.3-70b-versatile': '#9467bd',    # Purple
        }

        # Model display labels
        self.model_labels = {
            'qwen2.5_1.5b': 'Qwen 2.5 1.5B',
            'phi3_mini': 'Phi-3 Mini',
            'tinyllama_1.1b': 'TinyLlama 1.1B',
            'groq_mixtral-8x7b-32768': 'Mixtral 8x7B',
            'llama_llama-3.3-70b-versatile': 'Llama 3.3 70B',
        }

    def find_capability_threshold(self, capability_curve: Dict[int, float], task_type: str = None) -> Optional[int]:
        """
        Find tau_cau: bin where capability drops below threshold

        ISSUE 7 FIX: Use learned task-specific threshold instead of hard-coded 0.8

        Args:
            capability_curve: {bin: capability} mapping
            task_type: Task name to load learned threshold (optional)

        Returns: bin_id or None if no threshold
        """
        if not capability_curve:
            return None

        # Load task-specific threshold from config if available
        threshold = 0.8  # Default fallback
        if task_type:
            try:
                from ..core.config import get_capability_threshold
                threshold = get_capability_threshold(task_type, use_learned=True)
            except:
                pass  # Use default if import fails

        valid_bins = sorted([b for b in capability_curve.keys() if capability_curve[b] is not None])

        for bin_id in valid_bins:
            if capability_curve[bin_id] < threshold:
                return bin_id

        return None

    def find_risk_threshold(self, risk_curve: Dict[int, float], task_type: str = None) -> Optional[int]:
        """
        Find tau_risk: bin where risk exceeds threshold

        ISSUE 7 FIX: Use learned task-specific threshold instead of hard-coded 0.3

        Args:
            risk_curve: {bin: risk} mapping
            task_type: Task name to load learned threshold (optional)

        Returns: bin_id or None if no threshold
        """
        if not risk_curve:
            return None

        # Load task-specific threshold from config if available
        threshold = 0.3  # Default fallback
        if task_type:
            try:
                from ..core.config import get_risk_threshold
                threshold = get_risk_threshold(task_type, use_learned=True)
            except:
                pass  # Use default if import fails

        valid_bins = sorted([b for b in risk_curve.keys() if risk_curve[b] is not None])

        for bin_id in valid_bins:
            if risk_curve[bin_id] > threshold:
                return bin_id

        return None

    def plot_capability_curves(self, task_type: str, results: Dict) -> Path:
        """
        Plot capability curves for all models in a task

        Args:
            task_type: Name of task (e.g., 'text_generation')
            results: Analysis results dict {model: {capability_curve: {...}, ...}}

        Returns:
            Path to saved figure
        """
        fig, ax = plt.subplots(figsize=(12, 7))

        # Collect all bin IDs
        all_bins = set()
        thresholds = {}  # {model: tau_cau}

        for model, analysis in results.items():
            if 'error' in analysis:
                continue

            capability_curve = analysis.get('capability_curve', {})
            if not capability_curve:
                continue

            all_bins.update([b for b in capability_curve.keys() if capability_curve[b] is not None])
            thresholds[model] = self.find_capability_threshold(capability_curve, task_type=task_type)

        if not all_bins:
            plt.close(fig)
            return None

        sorted_bins = sorted(list(all_bins))

        # Plot each model
        for model, analysis in sorted(results.items()):
            if 'error' in analysis:
                continue

            capability_curve = analysis.get('capability_curve', {})
            if not capability_curve:
                continue

            # Extract capabilities for sorted bins
            caps = [capability_curve.get(b) for b in sorted_bins]

            # Get color and label
            color = self.colors.get(model, '#000000')
            label = self.model_labels.get(model, model)

            # Plot line
            ax.plot(sorted_bins, caps, marker='o', linewidth=2.5,
                   label=label, color=color, markersize=8, alpha=0.8)

            # Mark τ_cau threshold if exists
            tau_cau = thresholds.get(model)
            if tau_cau is not None and tau_cau in sorted_bins:
                idx = sorted_bins.index(tau_cau)
                ax.scatter([tau_cau], [caps[idx]], marker='X', s=200,
                          color=color, edgecolors='red', linewidths=2, zorder=5)

        # Formatting
        ax.set_xlabel('Difficulty Bin', fontsize=12, fontweight='bold')
        ax.set_ylabel('Capability (1 - Risk)', fontsize=12, fontweight='bold')
        ax.set_title(f'{task_type.replace("_", " ").title()} - Capability Curves',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(sorted_bins)
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=10, framealpha=0.95)

        # Add threshold legend
        ax.scatter([], [], marker='X', s=200, color='red', edgecolors='red',
                  linewidths=2, label='τ_cau (cap < 0.8)')
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc='best', fontsize=10, framealpha=0.95)

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f'{task_type}_capability_curves.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_file

    def plot_risk_curves(self, task_type: str, results: Dict) -> Path:
        """
        Plot risk sensitivity curves for all models in a task

        Args:
            task_type: Name of task (e.g., 'text_generation')
            results: Analysis results dict {model: {risk_curve: {...}, ...}}

        Returns:
            Path to saved figure
        """
        fig, ax = plt.subplots(figsize=(12, 7))

        # Collect all bin IDs
        all_bins = set()
        thresholds = {}  # {model: tau_risk}

        for model, analysis in results.items():
            if 'error' in analysis:
                continue

            risk_curve = analysis.get('risk_curve', {})
            if not risk_curve:
                continue

            all_bins.update([b for b in risk_curve.keys() if risk_curve[b] is not None])
            thresholds[model] = self.find_risk_threshold(risk_curve, task_type=task_type)

        if not all_bins:
            plt.close(fig)
            return None

        sorted_bins = sorted(list(all_bins))

        # Plot each model
        for model, analysis in sorted(results.items()):
            if 'error' in analysis:
                continue

            risk_curve = analysis.get('risk_curve', {})
            if not risk_curve:
                continue

            # Extract risks for sorted bins
            risks = [risk_curve.get(b) for b in sorted_bins]

            # Get color and label
            color = self.colors.get(model, '#000000')
            label = self.model_labels.get(model, model)

            # Plot line
            ax.plot(sorted_bins, risks, marker='o', linewidth=2.5,
                   label=label, color=color, markersize=8, alpha=0.8)

            # Mark τ_risk threshold if exists
            tau_risk = thresholds.get(model)
            if tau_risk is not None and tau_risk in sorted_bins:
                idx = sorted_bins.index(tau_risk)
                ax.scatter([tau_risk], [risks[idx]], marker='*', s=400,
                          color=color, edgecolors='darkred', linewidths=2, zorder=5)

        # Formatting
        ax.set_xlabel('Difficulty Bin', fontsize=12, fontweight='bold')
        ax.set_ylabel('Risk (P(semantic_failure | bin))', fontsize=12, fontweight='bold')
        ax.set_title(f'{task_type.replace("_", " ").title()} - Risk Sensitivity Curves',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(sorted_bins)
        ax.set_ylim([0, 1.05])
        ax.axhline(y=0.3, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Risk threshold (0.3)')
        ax.grid(True, alpha=0.3, linestyle='--')

        # Legend
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc='best', fontsize=10, framealpha=0.95)

        plt.tight_layout()

        # Save
        output_file = self.output_dir / f'{task_type}_risk_curves.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_file

    def save_all_visualizations(self, all_results: Dict) -> Dict[str, List[Path]]:
        """
        Generate all capability and risk curves for all tasks

        Args:
            all_results: Full analysis results {task: {model: analysis}}

        Returns:
            Dict mapping task names to list of generated plot paths
        """
        saved_plots = {}

        for task_type, task_results in all_results.items():
            print(f"\n  Generating graphs for {task_type}...")

            # Generate capability curve
            cap_plot = self.plot_capability_curves(task_type, task_results)
            if cap_plot:
                print(f"    - Saved: {cap_plot.name}")

            # Generate risk curve
            risk_plot = self.plot_risk_curves(task_type, task_results)
            if risk_plot:
                print(f"    - Saved: {risk_plot.name}")

            saved_plots[task_type] = [cap_plot, risk_plot]

        return saved_plots
