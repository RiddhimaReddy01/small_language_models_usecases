from __future__ import annotations

import argparse
import json
from pathlib import Path

from sddf.reporting import generate_part_b_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Part B SDDF report for a run directory.")
    parser.add_argument("--benchmark", required=True, help="Benchmark name.")
    parser.add_argument("--run-path", required=True, help="Path to the run/output directory that contains sddf/.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory for the generated report.")
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
    readiness = _lookup_readiness(args.readiness_json, args.benchmark, args.run_path)
    outputs = generate_part_b_report(args.run_path, args.benchmark, output_dir=args.output_dir, readiness=readiness)
    print(f"Part B report written to {outputs['report_path']}")
    print(f"Part B summary written to {outputs['summary_path']}")


if __name__ == "__main__":
    main()
