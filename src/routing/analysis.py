#!/usr/bin/env python3
"""
Complete Risk & Capability Analysis for All Tasks

Generates:
1. Capability curves with tipping points (τ_cap)
2. Risk curves with tipping points (τ_risk)
3. 2x2 Decision Matrix for all 8 tasks
4. Visualizations
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics
import sys

# Configuration
BENCHMARK_DIR = Path("benchmark_output")
TASKS = [
    "text_generation", "code_generation", "classification", "maths",
    "summarization", "retrieval_grounded", "instruction_following", "information_extraction"
]

MODELS = {
    "phi3_mini": "Phi-3 (3.8B)",
    "qwen2.5_1.5b": "Qwen (1.5B)",
    "tinyllama_1.1b": "TinyLlama (1.1B)",
    "llama_llama-3.3-70b-versatile": "Llama (70B)"
}

# Quality thresholds from sddf/ingest.py
QUALITY_THRESHOLDS = {
    "text_generation": 0.80,
    "code_generation": 1.0,
    "classification": 1.0,
    "maths": 1.0,
    "summarization": 0.80,
    "retrieval_grounded": 1.0,
    "instruction_following": 0.80,
    "information_extraction": 0.80,
}

# Decision thresholds
CAPABILITY_THRESHOLD = 0.80  # τ_C
RISK_THRESHOLD = 0.20        # τ_R

# Quality metric extractors (from sddf/ingest.py)
QUALITY_EXTRACTORS = {
    "text_generation": lambda s: s.get('metrics', {}).get('framework', {})
                                   .get('instruction_following', {})
                                   .get('constraint_satisfaction_rate', 0.0),
    "code_generation": lambda s: float(bool(s.get('passed', False))),
    "classification": lambda s: float(s.get('prediction') == s.get('reference')),
    "maths": lambda s: float(bool(s.get('base', {}).get('correct', False))),
    "summarization": lambda s: s.get('rouge_1_f1', 0.0),
    "retrieval_grounded": lambda s: float(str(s.get('prediction', '')).strip()
                                           == str(s.get('reference', '')).strip()),
    "instruction_following": lambda s: (
        s.get('constraints_satisfied', 0) / s.get('total_constraints', 1)
        if s.get('total_constraints', 0) > 0 else 1.0
    ),
    "information_extraction": lambda s: s.get('f1_score', 0.0),
}

# Difficulty extractors
DIFFICULTY_EXTRACTORS = {
    "text_generation": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "code_generation": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "classification": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "maths": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "summarization": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "retrieval_grounded": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "instruction_following": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
    "information_extraction": lambda s: min(len(s.get('raw_input', '')) / 1000, 1.0),
}


class CompleteAnalysis:
    """Generate complete analysis with curves, tipping points, and decision matrix"""

    def __init__(self):
        self.risk_curves = {}        # {(task, model): {bin: risk}}
        self.capability_curves = {}  # {(task, model): {bin: capability}}
        self.tipping_points = {}     # {(task, model): (tau_cap, tau_risk)}
        self.decisions = {}           # {(task, model): zone}

    def load_outputs(self, task, model_key):
        """Load outputs from benchmark directory"""
        # Try multiple possible paths
        possible_paths = [
            BENCHMARK_DIR / task / model_key / "outputs.jsonl",
            BENCHMARK_DIR / task / model_key / "results.jsonl",
            BENCHMARK_DIR / task / "results" / model_key / "outputs.jsonl",
        ]

        for path in possible_paths:
            if path.exists():
                samples = []
                try:
                    with open(path) as f:
                        for line in f:
                            if line.strip():
                                try:
                                    samples.append(json.loads(line))
                                except:
                                    continue
                    if samples:
                        return samples
                except Exception as e:
                    continue

        return None

    def bin_by_difficulty(self, samples, task, num_bins=5):
        """Bin samples by difficulty"""
        binned = defaultdict(list)
        difficulty_fn = DIFFICULTY_EXTRACTORS.get(task, lambda s: 0.5)

        for sample in samples:
            try:
                difficulty_score = difficulty_fn(sample)
                difficulty_score = max(0.0, min(1.0, difficulty_score))
                bin_id = int(difficulty_score * (num_bins - 1))
                bin_id = min(bin_id, num_bins - 1)
                binned[bin_id].append(sample)
            except:
                continue

        return dict(binned)

    def compute_curves(self, samples_by_bin, task):
        """Compute Risk and Capability curves"""
        quality_fn = QUALITY_EXTRACTORS.get(task)
        threshold = QUALITY_THRESHOLDS.get(task, 0.80)

        if not quality_fn:
            return None, None

        risks = {}
        capabilities = {}

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]

            if not samples:
                risks[bin_id] = None
                capabilities[bin_id] = None
                continue

            # Count failures
            failures = 0
            for sample in samples:
                try:
                    quality_score = quality_fn(sample)
                    if quality_score < threshold:
                        failures += 1
                except:
                    failures += 1

            # Compute curves
            risk = failures / len(samples) if samples else 0
            capability = 1 - risk

            risks[bin_id] = risk
            capabilities[bin_id] = capability

        return risks, capabilities

    def detect_tipping_points(self, capability_curve, risk_curve):
        """
        Detect tipping points:
        τ_cap = max{b : C_m(b) >= 0.80}
        τ_risk = min{b : Risk_m(b) > 0.20}
        """
        # Capability tipping point: last bin where capability >= 0.80
        tau_cap = None
        for b in range(5):
            if b in capability_curve and capability_curve[b] is not None:
                if capability_curve[b] >= CAPABILITY_THRESHOLD:
                    tau_cap = b

        # Risk tipping point: first bin where risk > 0.20
        tau_risk = None
        for b in range(5):
            if b in risk_curve and risk_curve[b] is not None:
                if risk_curve[b] > RISK_THRESHOLD:
                    tau_risk = b
                    break

        return tau_cap, tau_risk

    def classify_zone(self, capability_curve, risk_curve):
        """Classify into 2x2 zone"""
        cap_vals = [c for c in capability_curve.values() if c is not None]
        risk_vals = [r for r in risk_curve.values() if r is not None]

        if not cap_vals or not risk_vals:
            return "Unknown"

        avg_cap = statistics.mean(cap_vals)
        avg_risk = statistics.mean(risk_vals)

        if avg_cap >= CAPABILITY_THRESHOLD:
            if avg_risk <= RISK_THRESHOLD:
                return "Zone 1: Pure SLM"
            else:
                return "Zone 2: SLM+Guards"
        else:
            if avg_risk <= RISK_THRESHOLD:
                return "Zone 3: SLM Draft"
            else:
                return "Zone 4: LLM Only"

    def analyze_all_tasks(self):
        """Analyze all tasks and models"""
        print("\n" + "="*120)
        print("COMPLETE ANALYSIS: CAPABILITY CURVES, RISK CURVES, TIPPING POINTS")
        print("="*120)

        for task in TASKS:
            print(f"\n{'='*120}")
            print(f"TASK: {task}")
            print(f"Quality Threshold: {QUALITY_THRESHOLDS[task]:.2f}")
            print(f"{'='*120}\n")
            print(f"{'Model':<30} {'tau_cap':>10} {'tau_risk':>10} {'Avg Cap':>10} {'Avg Risk':>10} {'Zone':<25}")
            print("-"*120)

            for model_key, model_name in MODELS.items():
                # Load outputs
                samples = self.load_outputs(task, model_key)
                if not samples:
                    continue

                # Bin by difficulty
                binned = self.bin_by_difficulty(samples, task)

                # Compute curves
                risk_curve, cap_curve = self.compute_curves(binned, task)
                if risk_curve is None or cap_curve is None:
                    continue

                # Detect tipping points
                tau_cap, tau_risk = self.detect_tipping_points(cap_curve, risk_curve)

                # Classify zone
                zone = self.classify_zone(cap_curve, risk_curve)

                # Store results
                self.risk_curves[(task, model_key)] = risk_curve
                self.capability_curves[(task, model_key)] = cap_curve
                self.tipping_points[(task, model_key)] = (tau_cap, tau_risk)
                self.decisions[(task, model_key)] = zone

                # Compute averages
                cap_vals = [c for c in cap_curve.values() if c is not None]
                risk_vals = [r for r in risk_curve.values() if r is not None]
                avg_cap = statistics.mean(cap_vals) if cap_vals else 0
                avg_risk = statistics.mean(risk_vals) if risk_vals else 0

                # Print results
                tau_cap_str = str(tau_cap) if tau_cap is not None else "None"
                tau_risk_str = str(tau_risk) if tau_risk is not None else "None"

                print(f"{model_name:<30} {tau_cap_str:>10} {tau_risk_str:>10} {avg_cap:>9.1%} {avg_risk:>9.1%} {zone:<25}")

                # Print curve details
                cap_str = " ".join([f"{c:.0%}" if c is not None else "N/A" for c in cap_curve.values()])
                risk_str = " ".join([f"{r:.0%}" if r is not None else "N/A" for r in risk_curve.values()])
                print(f"  Capability: {cap_str}")
                print(f"  Risk:       {risk_str}\n")

    def print_decision_matrix(self):
        """Print 2x2 decision matrix for all tasks"""
        print("\n" + "="*120)
        print("DECISION MATRIX: ALL TASKS")
        print("="*120)

        # Group by task
        for task in TASKS:
            print(f"\n{task.upper()}")
            print("-"*120)

            zones = {
                "Zone 1: Pure SLM": [],
                "Zone 2: SLM+Guards": [],
                "Zone 3: SLM Draft": [],
                "Zone 4: LLM Only": []
            }

            for (t, model_key), zone in self.decisions.items():
                if t == task:
                    model_name = MODELS.get(model_key, model_key)
                    zones[zone].append(model_name)

            # Print zones
            for zone_name in ["Zone 1: Pure SLM", "Zone 2: SLM+Guards", "Zone 3: SLM Draft", "Zone 4: LLM Only"]:
                models = zones[zone_name]
                if models:
                    print(f"\n{zone_name}:")
                    for model_name in models:
                        tau_cap, tau_risk = self.tipping_points.get((task, [k for k, v in MODELS.items() if v == model_name][0]), (None, None))
                        print(f"  - {model_name:30s} (tau_cap={tau_cap}, tau_risk={tau_risk})")
                else:
                    print(f"\n{zone_name}: [None]")

    def print_summary(self):
        """Print overall summary"""
        print("\n" + "="*120)
        print("SUMMARY: ZONE DISTRIBUTION")
        print("="*120)

        for task in TASKS:
            zone_counts = {}
            for (t, model_key), zone in self.decisions.items():
                if t == task:
                    zone_counts[zone] = zone_counts.get(zone, 0) + 1

            total_models = sum(zone_counts.values())
            if total_models > 0:
                print(f"\n{task}:")
                for zone in ["Zone 1: Pure SLM", "Zone 2: SLM+Guards", "Zone 3: SLM Draft", "Zone 4: LLM Only"]:
                    count = zone_counts.get(zone, 0)
                    pct = (count / total_models * 100) if total_models > 0 else 0
                    print(f"  {zone:25s}: {count} model(s) ({pct:.0f}%)")

    def export_csv(self):
        """Export results to CSV"""
        output_path = Path("analysis_results.csv")

        with open(output_path, 'w') as f:
            f.write("Task,Model,τ_cap,τ_risk,Avg_Capability,Avg_Risk,Zone\n")

            for (task, model_key), (tau_cap, tau_risk) in self.tipping_points.items():
                model_name = MODELS.get(model_key, model_key)
                zone = self.decisions.get((task, model_key), "Unknown")

                cap_curve = self.capability_curves.get((task, model_key), {})
                risk_curve = self.risk_curves.get((task, model_key), {})

                cap_vals = [c for c in cap_curve.values() if c is not None]
                risk_vals = [r for r in risk_curve.values() if r is not None]

                avg_cap = statistics.mean(cap_vals) if cap_vals else 0
                avg_risk = statistics.mean(risk_vals) if risk_vals else 0

                f.write(f"{task},{model_name},{tau_cap},{tau_risk},{avg_cap:.3f},{avg_risk:.3f},{zone}\n")

        print(f"\n[OK] Results exported to {output_path}")


def main():
    """Main execution"""
    analysis = CompleteAnalysis()

    # Run complete analysis
    analysis.analyze_all_tasks()

    # Print decision matrix
    analysis.print_decision_matrix()

    # Print summary
    analysis.print_summary()

    # Export to CSV
    analysis.export_csv()

    print("\n" + "="*120)
    print("ANALYSIS COMPLETE")
    print("="*120)
    print("\nFiles generated:")
    print("  - analysis_results.csv (detailed results)")
    print("\nNext: Generate visualizations with capability and risk curves")
    print("="*120 + "\n")


if __name__ == "__main__":
    main()
