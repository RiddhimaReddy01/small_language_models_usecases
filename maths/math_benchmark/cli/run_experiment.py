import argparse

from math_benchmark.modeling.experiment import run_benchmark
from math_benchmark.paths import CONFIGS_DIR, RAW_RESULTS_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="Run the math evaluation benchmark.")
    parser.add_argument("--config", default=str(CONFIGS_DIR / "config.yaml"), help="Path to benchmark config.")
    parser.add_argument(
        "--output",
        default=str(RAW_RESULTS_DIR / "results_benchmark.json"),
        help="Where to write benchmark results.",
    )
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic seed for sampling and ordering.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use simulated model responses while still requiring real datasets on disk.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_benchmark(args.config, args.output, seed=args.seed, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
