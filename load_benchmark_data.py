#!/usr/bin/env python3
"""
Load benchmark queries from the tracked benchmark suite.

This script shows how to access the complete benchmark data:
- Preferred location: model_runs/
- Backward-compatible location: model_runs/benchmark_75/
- Each task has 75 queries for each SLM (phi3:mini, qwen2.5:1.5b, tinyllama:1.1b)
- Groq Llama baseline is the reference (already completed)
"""

import json
from pathlib import Path


ROOT = Path(__file__).parent
LEGACY_BENCHMARK_PATH = ROOT / "model_runs" / "benchmark_75"
FLAT_BENCHMARK_PATH = ROOT / "model_runs"
EXCLUDED_TASK_DIRS = {"business_analytics"}


def _benchmark_path() -> Path:
    if LEGACY_BENCHMARK_PATH.exists():
        return LEGACY_BENCHMARK_PATH
    return FLAT_BENCHMARK_PATH

def load_benchmark_outputs(task, model):
    """
    Load benchmark outputs for a specific task and model.

    Args:
        task: Task name (e.g., 'maths', 'classification', 'code_generation')
        model: Model name (e.g., 'phi3_mini', 'qwen2.5_1.5b', 'tinyllama_1.1b', 'llama_llama-3.3-70b-versatile')

    Returns:
        List of output dictionaries from outputs.jsonl
    """
    benchmark_path = _benchmark_path()
    outputs_file = benchmark_path / task / model / "outputs.jsonl"

    if not outputs_file.exists():
        raise FileNotFoundError(f"No outputs found at {outputs_file}")

    outputs = []
    with open(outputs_file, 'r', encoding='utf-8') as f:
        for line in f:
            outputs.append(json.loads(line))

    return outputs


def get_available_tasks():
    """List all available tasks in the benchmark."""
    benchmark_path = _benchmark_path()
    return sorted(
        d.name
        for d in benchmark_path.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_TASK_DIRS
    )


def get_available_models():
    """List all available models in the benchmark."""
    return [
        "llama_llama-3.3-70b-versatile",
        "phi3_mini",
        "qwen2.5_1.5b",
        "tinyllama_1.1b",
    ]


if __name__ == "__main__":
    print("\n=== BENCHMARK DATA LOADER ===\n")

    tasks = get_available_tasks()
    models = get_available_models()

    print(f"Available tasks ({len(tasks)}):")
    for task in tasks:
        print(f"  - {task}")

    print(f"\nAvailable models ({len(models)}):")
    for model in models:
        print(f"  - {model}")

    print("\n=== EXAMPLE USAGE ===\n")
    print("# Load all math queries for phi3:mini")
    print("outputs = load_benchmark_outputs('maths', 'phi3_mini')")
    print(f"print(len(outputs))  # {75}")
    print("print(outputs[0])    # First result")
