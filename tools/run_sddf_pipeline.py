#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_step(step_name: str, args: list[str]) -> None:
    print(f"[SDDF] {step_name}: {' '.join(args)}")
    subprocess.run(args, cwd=str(ROOT), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run streamlined SDDF pipeline end-to-end.")
    parser.add_argument("--cap-threshold", type=float, default=0.80)
    parser.add_argument("--risk-threshold", type=float, default=0.20)
    parser.add_argument("--ci-level", type=float, default=0.90)
    parser.add_argument("--min-samples", type=int, default=5)
    parser.add_argument("--min-ground-truth-coverage", type=float, default=0.95)
    parser.add_argument("--utility-alpha", type=float, default=1.0)
    parser.add_argument("--utility-beta", type=float, default=0.25)
    parser.add_argument("--utility-gamma", type=float, default=1.0)
    parser.add_argument("--report-split", type=str, default="test")
    parser.add_argument("--weights-source-split", type=str, default=None)
    parser.add_argument("--difficulty-weights", type=Path, default=None)
    parser.add_argument("--learn-family-weights", action="store_true")
    parser.add_argument("--abstain-max-delta", type=float, default=0.35)
    parser.add_argument("--abstain-grid-step", type=float, default=0.01)
    parser.add_argument("--tau-bootstrap-draws", type=int, default=200)
    parser.add_argument("--tau-conservative-percentile", type=float, default=10.0)
    parser.add_argument("--skip-benchmarking", action="store_true")
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--skip-summary", action="store_true")
    args = parser.parse_args()

    py = sys.executable
    sddf_cmd = [
        py,
        str(ROOT / "tools" / "generate_benchmark75_sddf.py"),
        "--cap-threshold",
        str(args.cap_threshold),
        "--risk-threshold",
        str(args.risk_threshold),
        "--ci-level",
        str(args.ci_level),
        "--min-samples",
        str(args.min_samples),
        "--min-ground-truth-coverage",
        str(args.min_ground_truth_coverage),
        "--utility-alpha",
        str(args.utility_alpha),
        "--utility-beta",
        str(args.utility_beta),
        "--utility-gamma",
        str(args.utility_gamma),
        "--report-split",
        str(args.report_split),
        "--abstain-max-delta",
        str(args.abstain_max_delta),
        "--abstain-grid-step",
        str(args.abstain_grid_step),
        "--tau-bootstrap-draws",
        str(args.tau_bootstrap_draws),
        "--tau-conservative-percentile",
        str(args.tau_conservative_percentile),
    ]
    if args.learn_family_weights:
        sddf_cmd.append("--learn-family-weights")
    if args.difficulty_weights:
        sddf_cmd.extend(["--difficulty-weights", str(args.difficulty_weights)])
        if args.weights_source_split:
            sddf_cmd.extend(["--weights-source-split", str(args.weights_source_split)])

    if not args.skip_benchmarking:
        _run_step(
            "Generate comprehensive benchmarking metrics",
            [py, str(ROOT / "tools" / "generate_comprehensive_benchmark_metrics.py")],
        )

    _run_step("Generate SDDF artifacts", sddf_cmd)

    if not args.skip_dashboard:
        _run_step("Generate business dashboard", [py, str(ROOT / "tools" / "generate_business_dashboard.py")])

    if not args.skip_summary:
        _run_step("Generate task summary", [py, str(ROOT / "tools" / "summarize_task_reports.py")])

    print("[SDDF] Pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
