from __future__ import annotations

import argparse

from ie_benchmark.final_results import export_final_results
from ie_benchmark.hf_data import download_sroie_from_hf
from ie_benchmark.ingest import ingest_sroie
from ie_benchmark.pipeline import run_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Information Extraction benchmark CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the IE benchmark.")
    run_parser.add_argument("--config", required=True, help="Path to the benchmark config file.")

    ingest_parser = subparsers.add_parser("ingest-sroie", help="Convert raw SROIE-style files into JSONL.")
    ingest_parser.add_argument("--ocr-dir", required=True, help="Directory containing OCR text files.")
    ingest_parser.add_argument("--labels-dir", required=True, help="Directory containing label files.")
    ingest_parser.add_argument("--output", required=True, help="Output JSONL path.")
    ingest_parser.add_argument("--split", default="clean", help="Split label for produced records.")

    hf_parser = subparsers.add_parser("download-sroie-hf", help="Download the SROIE mirror from Hugging Face.")
    hf_parser.add_argument("--output", required=True, help="Output JSONL path.")
    hf_parser.add_argument("--split", default="train", help="Dataset split to download from Hugging Face.")

    export_parser = subparsers.add_parser("export-results", help="Export stable final tables from run summaries.")
    export_parser.add_argument("--summary", action="append", required=True, help="Path to a run summary.json file.")
    export_parser.add_argument("--model", action="append", default=None, help="Optional model name filter.")
    export_parser.add_argument("--output-dir", default="results", help="Directory for exported final tables.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run_benchmark(args.config)
    if args.command == "ingest-sroie":
        count = ingest_sroie(args.ocr_dir, args.labels_dir, args.output, args.split)
        print(f"Wrote {count} examples to {args.output}")
        return 0
    if args.command == "download-sroie-hf":
        count = download_sroie_from_hf(args.output, args.split)
        print(f"Wrote {count} examples to {args.output}")
        return 0
    if args.command == "export-results":
        output_path = export_final_results(args.summary, args.output_dir, args.model)
        print(f"Wrote final tables to {output_path}")
        return 0
    raise ValueError(f"Unsupported command: {args.command}")
