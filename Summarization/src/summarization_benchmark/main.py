from __future__ import annotations

import argparse
import json

from summarization_benchmark.config import load_config
from summarization_benchmark.runner import run_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the summarization benchmark.")
    parser.add_argument(
        "--config",
        default="configs/default.json",
        help="Path to the benchmark config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    summary, results_path, summary_path, tables_path = run_benchmark(config)
    print(json.dumps(summary, indent=2))
    print(f"\nPer-sample results saved to: {results_path}")
    print(f"Aggregate summary saved to: {summary_path}")
    print(f"Metrics tables saved to: {tables_path}")


if __name__ == "__main__":
    main()
