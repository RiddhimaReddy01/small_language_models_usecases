from __future__ import annotations

import argparse
import time
from pathlib import Path

from .config import DEFAULT_SEED, UserDatasetConfig
from .datasets import load_builtin_datasets, load_uploaded_dataset
from .evaluator import Evaluator, save_results
from .models import GeminiWrapper, HuggingFaceApiWrapper, OllamaWrapper


def parse_args():
    parser = argparse.ArgumentParser(description="Classification evaluation pipeline")
    parser.add_argument("--model", type=str, default="phi3:mini", help="Model name to evaluate")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers")
    parser.add_argument(
        "--profile",
        type=str,
        default="fast15",
        choices=["fast15", "full"],
        help="Built-in dataset sampling profile",
    )
    parser.add_argument("--test-mode", action="store_true", help="Reduce each dataset to 1 sample per class")

    parser.add_argument("--input-file", type=str, help="Path to a user dataset in CSV, JSONL, or JSON format")
    parser.add_argument("--dataset-name", type=str, default="uploaded-dataset", help="Name to display for uploaded data")
    parser.add_argument("--task-type", type=str, default="Custom", help="Task type label for uploaded data")
    parser.add_argument("--text-column", type=str, help="Text column name for uploaded data")
    parser.add_argument("--label-column", type=str, help="Label column name for uploaded data")
    parser.add_argument(
        "--labels",
        type=str,
        help="Comma-separated allowed label names. Optional for uploaded data with string labels.",
    )
    parser.add_argument("--sample-per-class", type=int, help="Samples per class for uploaded data")
    parser.add_argument("--max-samples", type=int, help="Hard cap on total uploaded samples")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for sampling")
    parser.add_argument("--output-dir", type=str, default="results", help="Directory where run artifacts are written")
    return parser.parse_args()


def _build_model(model_name):
    if model_name.lower().startswith("hf_api:"):
        return HuggingFaceApiWrapper(model_name.split(":", 1)[1])
    if "gemini" in model_name.lower():
        return GeminiWrapper(model_name)
    return OllamaWrapper(model_name)


def _load_datasets(args):
    if args.input_file:
        labels = [label.strip() for label in args.labels.split(",")] if args.labels else []
        config = UserDatasetConfig(
            path=Path(args.input_file),
            dataset_name=args.dataset_name,
            task_type=args.task_type,
            text_column=args.text_column,
            label_column=args.label_column,
            labels=labels,
            sample_per_class=args.sample_per_class,
            max_samples=args.max_samples,
            seed=args.seed,
        )
        print(f"Loading uploaded dataset from: {config.path}")
        return load_uploaded_dataset(config)

    print(f"Loading built-in datasets with '{args.profile}' profile...")
    return load_builtin_datasets(sample_profile=args.profile)


def _apply_test_mode(datasets):
    print("Test mode enabled: scaling down datasets to 1 sample per class.")
    for name in datasets:
        datasets[name]["data"] = datasets[name]["data"].groupby("label").head(1)


def run():
    args = parse_args()
    datasets = _load_datasets(args)

    if args.test_mode:
        _apply_test_mode(datasets)

    print(f"Initializing model: {args.model}")
    model = _build_model(args.model)

    timestamp = int(time.time())
    output_dir = args.output_dir
    live_file = f"{output_dir}/live_results_{args.model.replace(':', '_')}_{timestamp}.csv"
    evaluator = Evaluator(model, num_workers=args.workers, output_file=live_file)
    print(f"Live results will be saved to: {live_file}")

    all_ops_metrics = []
    all_capability_metrics = {}

    for name, info in datasets.items():
        ops, dataset_results = evaluator.run_evaluation(name, info["data"], info["labels"], info["type"])
        all_ops_metrics.append(ops)
        cap = evaluator.calculate_capability_metrics(dataset_results)
        all_capability_metrics[name] = cap
        print(f"Capability Highlights for {name}: Accuracy: {cap['accuracy']:.2f}, F1: {cap['macro_f1']:.2f}")

    save_results(
        evaluator.results,
        all_ops_metrics,
        all_capability_metrics,
        output_dir=output_dir,
        run_metadata={
            "model": args.model,
            "workers": args.workers,
            "profile": args.profile if not args.input_file else None,
            "input_file": args.input_file,
            "dataset_name": args.dataset_name if args.input_file else None,
            "test_mode": args.test_mode,
            "seed": args.seed,
        },
    )

    print("\n" + "=" * 30)
    print("EVALUATION COMPLETE")
    print("=" * 30)
