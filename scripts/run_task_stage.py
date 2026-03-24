from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarking.interface import run_stage_cli

STAGES = [
    "benchmark_report",
    "dataset_sampling",
    "metric_computation",
    "model_inference",
    "prediction_storage",
]


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run a benchmarking stage for any task")
    parser.add_argument("--task", required=True, help="Task name (e.g., classification)")
    parser.add_argument("--stage", required=True, choices=STAGES, help="Stage to run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_stage_cli(args.task, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
