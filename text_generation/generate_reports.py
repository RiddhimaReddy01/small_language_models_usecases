import argparse

from scripts.reporting import generate_reports


def main():
    parser = argparse.ArgumentParser(description="Generate text-generation benchmark reports")
    parser.add_argument("--results_dir", type=str, default="results", help="Directory containing raw result JSON files")
    parser.add_argument("--input_files", nargs="*", help="Optional list of raw result JSON files to summarize")
    args = parser.parse_args()

    outputs = generate_reports(args.results_dir, input_files=args.input_files)
    print(f"Models: {', '.join(outputs['models'])}")
    print(f"Summary JSON: {outputs['summary_path']}")
    print(f"Metrics tables: {outputs['tables_path']}")
    print(f"Model comparison: {outputs['comparison_path']}")


if __name__ == "__main__":
    main()
