from __future__ import annotations

import argparse
import os
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


CANONICAL_STAGES = [
    "dataset_sampling",
    "model_inference",
    "prediction_storage",
    "metric_computation",
    "benchmark_report",
]

TASK_SPECS: dict[str, dict[str, object]] = {
    "classification": {
        "root": "classification",
        "legacy_command": ["classification/main.py"],
        "output_arg": "--output-dir",
    },
    "maths": {
        "root": "maths",
        "legacy_command": ["maths/run_experiment.py"],
    },
    "text_generation": {
        "root": "text_generation",
        "legacy_command": ["text_generation/run_benchmark.py"],
        "output_arg": "--output_dir",
    },
    "summarization": {
        "root": "Summarization",
        "legacy_command": ["Summarization/scripts/run_benchmark.py"],
        "config_arg": "--config",
    },
    "information_extraction": {
        "root": "Information Extraction",
        "legacy_command": ["Information Extraction/run_benchmark.py"],
        "config_arg": "--config",
    },
    "retrieval_grounded": {
        "root": "Retrieval_grounded",
        "legacy_command": ["Retrieval_grounded/cli/run_experiment.py"],
        "config_arg": "--config",
    },
    "instruction_following": {
        "root": "instruction_following",
        "legacy_command": ["instruction_following/pipeline.py"],
    },
    "code_generation": {
        "root": "code_generation",
        "legacy_command": None,
    },
}


def run_stage_cli(task: str, stage: str) -> int:
    parser = argparse.ArgumentParser(description=f"{task}::{stage} stage adapter")
    parser.add_argument("--run-dir", required=False, help="Standardized run directory")
    parser.add_argument("--config", required=False, help="Optional config path")
    parser.add_argument("--execute-legacy", action="store_true", help="Invoke the legacy benchmark entrypoint")
    parser.add_argument("legacy_args", nargs=argparse.REMAINDER, help="Arguments forwarded to the legacy command")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    payload = {
        "task": task,
        "stage": stage,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "config": args.config,
        "execute_legacy": bool(args.execute_legacy),
        "legacy_args": _normalize_legacy_args(args.legacy_args),
    }
    if run_dir is not None:
        _write_stage_marker(run_dir, stage, payload)

    if args.execute_legacy:
        return _execute_legacy(task, run_dir, args.config, payload["legacy_args"])
    return 0


def _normalize_legacy_args(raw: list[str]) -> list[str]:
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def _write_stage_marker(run_dir: Path, stage: str, payload: dict[str, object]) -> None:
    stage_dir = run_dir / "_stage_state"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / f"{stage}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _execute_legacy(task: str, run_dir: Path | None, config_path: str | None, legacy_args: list[str]) -> int:
    spec = TASK_SPECS[task]
    legacy_command = spec.get("legacy_command")
    if not legacy_command:
        return 0

    repo_root = Path(__file__).resolve().parents[1]
    command = [sys.executable, *[str(repo_root / part) for part in legacy_command]]
    config_arg = spec.get("config_arg")
    output_arg = spec.get("output_arg")

    if config_path and config_arg:
        command.extend([str(config_arg), config_path])
    if run_dir and output_arg:
        command.extend([str(output_arg), str(run_dir)])
    command.extend(legacy_args)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing_pythonpath else os.pathsep.join([str(repo_root), existing_pythonpath])

    completed = subprocess.run(command, cwd=repo_root, env=env, check=False)
    return int(completed.returncode)
