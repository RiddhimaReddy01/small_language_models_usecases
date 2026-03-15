import argparse
from pathlib import Path

from math_benchmark.paths import DATA_DIR, RAW_DATA_DIR
from scripts.prepare_datasets import ensure_difficulty_coverage, normalize_records, write_jsonl


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize GSM8K, SVAMP, and MATH data into benchmark JSONL files.")
    parser.add_argument("--gsm8k-source", default=str(RAW_DATA_DIR / "gsm8k"), help="Path to raw GSM8K file or directory.")
    parser.add_argument("--svamp-source", default=str(RAW_DATA_DIR / "svamp"), help="Path to raw SVAMP file or directory.")
    parser.add_argument("--math-source", default=str(RAW_DATA_DIR / "math"), help="Path to raw MATH file or directory.")
    parser.add_argument(
        "--output-dir",
        default=str(DATA_DIR / "processed"),
        help="Directory for normalized benchmark JSONL files.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    datasets = {
        "gsm8k": Path(args.gsm8k_source),
        "svamp": Path(args.svamp_source),
        "math_subset": Path(args.math_source),
    }

    for name, source in datasets.items():
        records = normalize_records(name, source)
        counts = ensure_difficulty_coverage(name, records)
        output_path = output_dir / f"{name}.jsonl"
        write_jsonl(output_path, records)
        print(f"Wrote {len(records)} records to {output_path} with difficulty counts {counts}")


if __name__ == "__main__":
    main()
