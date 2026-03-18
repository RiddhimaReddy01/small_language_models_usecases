#!/usr/bin/env python3
"""
Capability Curves, Tipping Points, and Failure Taxonomy
Analyzes SLM vs LLM performance degradation across difficulty levels
"""

import json
import os
from collections import defaultdict
from pathlib import Path
import statistics

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

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
LLM = "llama_llama-3.3-70b-versatile"
SLMS = ["phi3_mini", "qwen2.5_1.5b", "tinyllama_1.1b"]

# Thresholds
UTILITY_THRESHOLD = 0.75
QUALITY_THRESHOLD = 0.80


def load_outputs(task, model):
    """Load outputs.jsonl for a task-model pair"""
    path = BENCHMARK_DIR / task / model / "outputs.jsonl"
    if not path.exists():
        return []

    outputs = []
    try:
        with open(path) as f:
            for line in f:
                if line.strip():
                    outputs.append(json.loads(line))
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}")

    return outputs


def group_by_bin(outputs):
    """Group outputs by difficulty bin"""
    bins = defaultdict(list)
    for output in outputs:
        bin_id = output.get("bin", 0)
        bins[bin_id].append(output)
    return bins


def calculate_accuracy(outputs):
    """Calculate pass rate (valid/total)"""
    if not outputs:
        return None
    valid = sum(1 for o in outputs if o.get("valid", False))
    return valid / len(outputs)


def calculate_latency(outputs):
    """Calculate average latency"""
    latencies = [o.get("latency_sec", 0) for o in outputs if o.get("latency_sec")]
    return statistics.mean(latencies) if latencies else None


def analyze_failures(outputs):
    """Categorize failure modes"""
    failures = defaultdict(int)
    for output in outputs:
        if output.get("valid"):
            continue

        error = output.get("error", "")
        status = output.get("status", "unknown")

        if status == "error":
            if "timeout" in error.lower():
                failures["timeout"] += 1
            elif "parse" in error.lower() or "json" in error.lower():
                failures["format_error"] += 1
            elif "truncat" in error.lower():
                failures["truncation"] += 1
            elif "token" in error.lower():
                failures["token_limit"] += 1
            else:
                failures["other_error"] += 1
        elif status == "success" and not output.get("valid"):
            failures["validation_failure"] += 1
        else:
            failures["unknown"] += 1

    return failures


def build_capability_curve(task):
    """Build capability curve for a task: difficulty bin vs accuracy"""
    print(f"\n{'='*70}")
    print(f"TASK: {task.upper()}")
    print(f"{'='*70}")

    curves = {}

    for model in MODELS.keys():
        outputs = load_outputs(task, model)
        if not outputs:
            print(f"  {MODELS[model]}: NO DATA")
            continue

        bins = group_by_bin(outputs)
        curve = []

        for bin_id in sorted(bins.keys()):
            bin_outputs = bins[bin_id]
            accuracy = calculate_accuracy(bin_outputs)
            latency = calculate_latency(bin_outputs)
            curve.append({
                "bin": bin_id,
                "accuracy": accuracy,
                "count": len(bin_outputs),
                "latency": latency
            })

        curves[model] = curve

        # Print per-bin breakdown
        print(f"\n  {MODELS[model]}:")
        for point in curve:
            acc_str = f"{point['accuracy']*100:5.1f}%" if point['accuracy'] is not None else "N/A"
            lat_str = f"{point['latency']:6.2f}s" if point['latency'] is not None else "N/A"
            print(f"    Bin {point['bin']}: {acc_str} ({point['count']:2d} samples) [{lat_str}]")

    return curves


def detect_tipping_point(task, curves):
    """Find where SLM accuracy drops below LLM"""
    if LLM not in curves:
        print(f"  Warning: {LLM} not in curves, skipping tipping point detection")
        return None

    llm_curve = curves[LLM]
    tipping_points = {}

    print(f"\n  TIPPING POINTS (where SLM < LLM):")

    for slm in SLMS:
        if slm not in curves:
            continue

        slm_curve = curves[slm]
        tipping_bin = None

        # Find first bin where SLM accuracy < LLM accuracy
        for slm_point in slm_curve:
            bin_id = slm_point["bin"]
            slm_acc = slm_point["accuracy"]

            # Find LLM accuracy for same bin
            llm_acc = next((p["accuracy"] for p in llm_curve if p["bin"] == bin_id), None)

            if slm_acc is None or llm_acc is None:
                continue

            if slm_acc < llm_acc:
                tipping_bin = bin_id
                break

        if tipping_bin is not None:
            slm_acc = next(p["accuracy"] for p in slm_curve if p["bin"] == tipping_bin)
            llm_acc = next(p["accuracy"] for p in llm_curve if p["bin"] == tipping_bin)
            print(f"    {MODELS[slm]}: Bin {tipping_bin} ({slm_acc*100:.1f}% vs {llm_acc*100:.1f}%)")
        else:
            print(f"    {MODELS[slm]}: NO DEGRADATION (competitive throughout)")

        tipping_points[slm] = tipping_bin

    return tipping_points


def analyze_failures_at_tipping(task, curves, tipping_points):
    """Analyze failure modes at tipping points"""
    print(f"\n  FAILURE ANALYSIS AT TIPPING POINTS:")

    for slm in SLMS:
        if slm not in tipping_points or tipping_points[slm] is None:
            continue

        tipping_bin = tipping_points[slm]
        outputs = load_outputs(task, slm)
        bins = group_by_bin(outputs)

        if tipping_bin in bins:
            failures = analyze_failures(bins[tipping_bin])
            if failures:
                print(f"\n    {MODELS[slm]} @ Bin {tipping_bin}:")
                total_failures = sum(failures.values())
                for failure_type, count in sorted(failures.items(), key=lambda x: -x[1]):
                    pct = (count / total_failures) * 100
                    print(f"      {failure_type:20s}: {count:3d} ({pct:5.1f}%)")


def plot_capability_curves(task, curves, tipping_points):
    """Plot capability curve with tipping points marked"""
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = {
        "phi3_mini": "#639922",
        "qwen2.5_1.5b": "#BA7517",
        "tinyllama_1.1b": "#534AB7",
        "llama_llama-3.3-70b-versatile": "#1B2A3E"
    }

    styles = {
        "phi3_mini": "-o",
        "qwen2.5_1.5b": "-s",
        "tinyllama_1.1b": "-^",
        "llama_llama-3.3-70b-versatile": "-D"
    }

    for model, curve in curves.items():
        if not curve:
            continue

        bins = [p["bin"] for p in curve]
        accuracies = [p["accuracy"] for p in curve if p["accuracy"] is not None]
        valid_bins = [p["bin"] for p in curve if p["accuracy"] is not None]

        ax.plot(valid_bins, accuracies, styles[model],
               color=colors[model], label=MODELS[model], linewidth=2.5, markersize=8)

        # Mark tipping point
        if model in tipping_points and tipping_points[model] is not None:
            tipping_bin = tipping_points[model]
            tipping_acc = next((p["accuracy"] for p in curve if p["bin"] == tipping_bin), None)
            if tipping_acc is not None:
                ax.scatter([tipping_bin], [tipping_acc], s=200, marker='X',
                          color=colors[model], edgecolors='red', linewidths=2, zorder=5)

    ax.axhline(y=QUALITY_THRESHOLD, color="red", linestyle="--", linewidth=1.5,
              label="Quality Threshold (80%)", alpha=0.7)
    ax.set_xlabel("Difficulty Bin (0=easy → 4=hard)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Accuracy (Pass Rate)", fontsize=12, fontweight='bold')
    ax.set_title(f"Capability Curves: {task.upper()}", fontsize=14, fontweight='bold')
    ax.set_xticks(range(5))
    ax.set_ylim([0, 1.05])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=10)

    # Save
    output_path = Path("paper") / f"capability_curve_{task}.png"
    output_path.parent.mkdir(exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  📊 Saved: {output_path}")
    plt.close()


def generate_routing_policy(task, tipping_points, curves):
    """Generate routing decisions based on tipping points"""
    print(f"\n  ROUTING POLICY:")

    routing = {}

    for slm in SLMS:
        if slm not in tipping_points:
            routing[slm] = "UNKNOWN"
            continue

        tipping_bin = tipping_points[slm]

        if tipping_bin is None:
            routing[slm] = "[OK] SAFE (all bins)"
        elif tipping_bin == 0:
            routing[slm] = "[NO] NEVER (fails immediately)"
        elif tipping_bin <= 2:
            routing[slm] = f"[!!] CONDITIONAL (safe until bin {tipping_bin-1})"
        else:
            routing[slm] = f"[OK] MOSTLY SAFE (risky from bin {tipping_bin})"

    for slm, policy in routing.items():
        print(f"    {MODELS[slm]:20s}: {policy}")

    return routing


def main():
    print("\n" + "="*70)
    print("CAPABILITY CURVES & TIPPING POINT ANALYSIS")
    print("="*70)

    routing_summary = {}

    for task in TASKS:
        curves = build_capability_curve(task)
        if not curves:
            continue

        tipping_points = detect_tipping_point(task, curves)
        analyze_failures_at_tipping(task, curves, tipping_points)
        routing = generate_routing_policy(task, tipping_points, curves)

        try:
            plot_capability_curves(task, curves, tipping_points)
        except Exception as e:
            print(f"  Warning: Failed to plot {task}: {e}")

        routing_summary[task] = routing

    # Summary table
    print("\n" + "="*70)
    print("ROUTING POLICY SUMMARY")
    print("="*70 + "\n")

    for task, routing in routing_summary.items():
        print(f"\n{task.upper()}:")
        for slm, policy in routing.items():
            print(f"  {MODELS[slm]:20s}: {policy}")


if __name__ == "__main__":
    main()
