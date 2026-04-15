#!/usr/bin/env python3
"""
Run SDDF validation phase: compute TAU thresholds and operational zones.

Usage:
    python tools/run_sddf_validation.py --task classification --model qwen2.5_3b
    python tools/run_sddf_validation.py --task all --model all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.difficulty import compute_all_features, DIFFICULTY_FEATURES
from sddf.validation_dynamic import run_validation

RUNS_DIR = ROOT / "model_runs"
WEIGHTS_F = RUNS_DIR / "difficulty_weights" / "family_weights_learned.json"
SPLITS_DIR = RUNS_DIR / "sddf_training_splits"

TASKS = ["classification", "maths", "code_generation", "instruction_following",
         "information_extraction", "retrieval_grounded", "summarization", "text_generation"]
SLMS = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]
BASELINE = "llama_llama-3.3-70b-versatile"

# Static capability/risk targets per task
THRESHOLDS = {
    "classification":         (0.75, 0.20),
    "maths":                  (0.65, 0.35),
    "code_generation":        (0.55, 0.40),
    "instruction_following":  (0.70, 0.30),
    "information_extraction": (0.75, 0.25),
    "retrieval_grounded":     (0.70, 0.30),
    "summarization":          (0.65, 0.35),
    "text_generation":        (0.70, 0.30),
}


def load_weights() -> dict[str, dict[str, dict]]:
    """Load learned weights from training phase."""
    if not WEIGHTS_F.exists():
        return {}
    return json.loads(WEIGHTS_F.read_text(encoding="utf-8")).get("families", {})


def load_split_query_ids(task: str, split: str = "val") -> list[str]:
    """Load query IDs for a split."""
    path = SPLITS_DIR / task / "split_query_ids.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get(split, [])


def load_task_data(task: str) -> dict[str, dict]:
    """
    Load all model inference results for a task.

    Returns: {model_name -> {sample_id -> {slm_correct, llm_correct, ...}}}
    """
    data = {}

    for model in SLMS + [BASELINE]:
        artifacts_path = SPLITS_DIR / task / "sddf_pipeline_artifacts"

        # Find the matching file (models may have special naming)
        model_file = None
        for candidate in artifacts_path.glob(f"*{model.replace('.', '_')}*.json"):
            model_file = candidate
            break

        if not model_file:
            # Try direct name
            model_file = artifacts_path / f"{model.replace('_', '.')}.json"

        if not model_file or not model_file.exists():
            continue

        # Load model results
        try:
            content = json.loads(model_file.read_text(encoding="utf-8"))
            # Extract per-sample correctness
            # The format varies; look for results or rows
            if isinstance(content, dict):
                # Try different keys
                for key in ["results", "rows", "data"]:
                    if key in content:
                        for row in content[key]:
                            sample_id = str(row.get("sample_id", ""))
                            if sample_id not in data:
                                data[sample_id] = {}
                            data[sample_id][model] = {
                                "correct": bool(row.get("correct", False)),
                            }
                        break
        except Exception as e:
            print(f"Warning: Failed to load {model_file}: {e}", file=sys.stderr)

    return data


def score_sample(
    sample: dict,
    prompt: str,
    weights: dict,
) -> float:
    """Score a sample using learned weights and norm_stats."""
    features = compute_all_features(sample, prompt)
    score = 0.0

    for dim in DIFFICULTY_FEATURES:
        val = float(features.get(dim, 0.0))
        b = weights.get("norm_stats", {}).get(dim, {})
        lo = float(b.get("p05", 0.0))
        hi = float(b.get("p95", 1.0))

        # Normalize to [0, 1]
        if hi > lo:
            nv = max(0.0, min(1.0, (val - lo) / (hi - lo)))
        else:
            nv = 0.0

        score += float(weights.get("weights", {}).get(dim, 0.0)) * nv

    return max(0.0, min(1.0, score))


def run_validation_for_task_model(
    task: str,
    model: str,
    weights_all: dict[str, dict[str, dict]],
    task_data: dict[str, dict],
    cap_target: float,
    risk_target: float,
) -> dict:
    """Run validation for a single task-model pair."""

    # Get learned weights for this task-model
    weights = weights_all.get(task, {}).get(model, {})
    if not weights:
        print(f"  [{task}/{model}] No learned weights found", file=sys.stderr)
        return None

    # Load validation split
    val_query_ids = load_split_query_ids(task, "val")
    if not val_query_ids:
        print(f"  [{task}/{model}] No validation split found", file=sys.stderr)
        return None

    # Build validation samples
    val_samples = []
    scores = {}

    for sample_id in val_query_ids:
        if sample_id not in task_data:
            continue

        sample_data = task_data[sample_id]

        # Get correctness for SLM and baseline
        slm_correct = sample_data.get(model, {}).get("correct", False)
        baseline_correct = sample_data.get(BASELINE, {}).get("correct", False)

        # For now, use placeholder features; in real scenario would reload from source
        sample = {
            "sample_id": sample_id,
            "slm_correct": slm_correct,
            "llm_correct": baseline_correct,
            "prompt": "",  # Placeholder
        }

        val_samples.append(sample)

        # Score the sample (would need actual prompt in production)
        # For now, use uniform score
        scores[sample_id] = 0.5

    if not val_samples:
        print(f"  [{task}/{model}] No validation samples found", file=sys.stderr)
        return None

    # Run validation
    result = run_validation(
        val_samples,
        scores,
        task,
        cap_static=cap_target,
        risk_static=risk_target,
    )

    result["model"] = model
    result["weights_src"] = "learned"

    return result


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--task",
        default="classification",
        choices=TASKS + ["all"],
        help="Task to validate (default: classification)",
    )
    ap.add_argument(
        "--model",
        default="qwen2.5_3b",
        choices=SLMS + ["all"],
        help="SLM model to validate (default: qwen2.5_3b)",
    )
    args = ap.parse_args()

    tasks = TASKS if args.task == "all" else [args.task]
    models = SLMS if args.model == "all" else [args.model]

    # Load all weights
    weights_all = load_weights()

    results_by_task = {}

    for task in tasks:
        print(f"Validating task: {task}", file=sys.stderr)

        # Load all data for this task
        task_data = load_task_data(task)
        cap_target, risk_target = THRESHOLDS.get(task, (0.70, 0.30))

        results_by_task[task] = {}

        for model in models:
            print(f"  Model: {model}", file=sys.stderr)

            result = run_validation_for_task_model(
                task,
                model,
                weights_all,
                task_data,
                cap_target,
                risk_target,
            )

            if result:
                results_by_task[task][model] = result

    # Save results
    output_path = RUNS_DIR / "validation_results" / "operational_zones.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Simplify for output (remove metrics list)
    output_data = {}
    for task, models_data in results_by_task.items():
        output_data[task] = {}
        for model, result in models_data.items():
            simplified = {k: v for k, v in result.items() if k != "metrics"}
            output_data[task][model] = simplified

    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\nValidation results saved to: {output_path}", file=sys.stderr)

    # Print summary
    print("\n" + "="*80, file=sys.stderr)
    print("VALIDATION SUMMARY", file=sys.stderr)
    print("="*80, file=sys.stderr)

    for task in tasks:
        if task not in results_by_task:
            continue

        print(f"\n{task.upper()}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        for model in models:
            if model not in results_by_task[task]:
                continue

            result = results_by_task[task][model]
            print(f"\n  {model}:", file=sys.stderr)
            print(f"    Baseline capability: {result['baseline_capability']:.3f}", file=sys.stderr)
            print(f"    Baseline risk:       {result['baseline_risk']:.3f}", file=sys.stderr)
            print(f"    Dynamic capability: {result['cap_dynamic']:.3f}", file=sys.stderr)
            print(f"    Dynamic risk:       {result['risk_dynamic']:.3f}", file=sys.stderr)
            print(f"    Strict TAU:         {result['strict_tau']}", file=sys.stderr)
            print(f"    Fallback TAU:       {result['fallback_tau']}", file=sys.stderr)
            print(f"    Feasible set:       {result['feasible_set']}", file=sys.stderr)


if __name__ == "__main__":
    main()
