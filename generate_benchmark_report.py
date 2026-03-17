from __future__ import annotations

import argparse
import json
from pathlib import Path

from sddf.reporting import generate_part_b_report
from sddf.setup_reporting import generate_part_a_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Part A, Part B, and combined benchmark reports.")
    parser.add_argument("--benchmark", required=True, help="Benchmark name.")
    parser.add_argument("--run-path", required=True, help="Path to benchmark output/run directory.")
    parser.add_argument("--output-dir", default=None, help="Optional report output directory.")
    parser.add_argument("--readiness-json", default=None, help="Optional validator output JSON.")
    return parser.parse_args()


def _lookup_readiness(readiness_json: str | None, benchmark: str, run_path: str) -> dict | None:
    if not readiness_json:
        return None
    payload = json.loads(Path(readiness_json).read_text(encoding="utf-8"))
    target = str(Path(run_path).resolve())
    for run in payload.get("runs", []):
        if run.get("benchmark") == benchmark and run.get("path") == target:
            return run
    return None


def main() -> None:
    args = parse_args()
    run_path = Path(args.run_path)
    default_output = (run_path / "sddf" / "reports") if (run_path / "sddf").exists() else (run_path / "reports")
    output_dir = Path(args.output_dir) if args.output_dir else default_output
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness = _lookup_readiness(args.readiness_json, args.benchmark, args.run_path)
    part_a = generate_part_a_report(args.benchmark, args.run_path, output_dir=output_dir)
    part_b = generate_part_b_report(args.run_path, args.benchmark, output_dir=output_dir, readiness=readiness)

    combined_path = output_dir / "combined_report.md"
    combined_text = (
        Path(part_a["report_path"]).read_text(encoding="utf-8").rstrip()
        + "\n\n"
        + Path(part_b["report_path"]).read_text(encoding="utf-8")
    )
    combined_path.write_text(combined_text, encoding="utf-8")

    print(f"Part A report written to {part_a['report_path']}")
    print(f"Part B report written to {part_b['report_path']}")
    print(f"Combined report written to {combined_path}")


if __name__ == "__main__":
    main()
