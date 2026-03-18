from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from benchmarking import CANONICAL_STAGES, TASK_SPECS, finalize_run_artifacts, initialize_run_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified benchmark runner")
    parser.add_argument("--task", required=True, choices=sorted(TASK_SPECS))
    parser.add_argument("--config", help="Optional config file for task benchmarks")
    parser.add_argument("--output-root", help="Optional override for standardized outputs root")
    parser.add_argument("--run-id", help="Optional run identifier")
    parser.add_argument("legacy_args", nargs=argparse.REMAINDER, help="Arguments forwarded to the task benchmark")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    task_spec = TASK_SPECS[args.task]
    task_root = repo_root / str(task_spec["root"])
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_root) if args.output_root else task_root / "outputs" / "runs"
    run_dir = output_root / run_id

    manifest = initialize_run_artifacts(
        task=args.task,
        task_root=task_root,
        run_dir=run_dir,
        config_path=args.config,
        extra={"legacy_args": _normalize_legacy_args(args.legacy_args)},
    )

    exit_code = 0
    for stage in CANONICAL_STAGES:
        script_path = task_root / "scripts" / f"{stage}.py"
        command = [sys.executable, str(script_path), "--run-dir", str(run_dir)]
        if args.config:
            command.extend(["--config", args.config])
        if stage == "benchmark_report":
            command.append("--execute-legacy")
        legacy_args = _normalize_legacy_args(args.legacy_args)
        if legacy_args:
            command.append("--")
            command.extend(legacy_args)
        completed = subprocess.run(command, cwd=repo_root, check=False)
        exit_code = completed.returncode
        if exit_code != 0:
            break

    finalize_run_artifacts(run_dir, manifest, exit_code)
    return exit_code


def _normalize_legacy_args(raw: list[str]) -> list[str]:
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


if __name__ == "__main__":
    raise SystemExit(main())
