from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from utils.hardware_logger import log_hardware


STANDARD_OUTPUTS = [
    "run_manifest.json",
    "dataset_manifest.json",
    "config_snapshot.json",
    "hardware.json",
    "predictions.jsonl",
    "metrics.json",
    "report.md",
    "logs.txt",
]


def initialize_run_artifacts(
    *,
    task: str,
    task_root: Path,
    run_dir: Path,
    config_path: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "task": task,
        "task_root": str(task_root),
        "run_dir": str(run_dir),
        "started_at_utc": datetime.now(UTC).isoformat(),
        "config_path": config_path,
        "extra": extra or {},
        "artifacts": {},
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    _write_json(
        run_dir / "dataset_manifest.json",
        {
            "task": task,
            "sampling_interface": "scripts/dataset_sampling.py",
            "notes": "Legacy benchmark adapters may still derive exact dataset details internally.",
        },
    )
    _snapshot_config(run_dir / "config_snapshot.json", config_path, extra or {})
    log_hardware(run_dir / "hardware.json")
    (run_dir / "logs.txt").write_text("", encoding="utf-8")
    return manifest


def finalize_run_artifacts(run_dir: Path, manifest: dict[str, Any], exit_code: int) -> None:
    manifest["completed_at_utc"] = datetime.now(UTC).isoformat()
    manifest["exit_code"] = exit_code

    predictions_path = run_dir / "predictions.jsonl"
    metrics_path = run_dir / "metrics.json"
    report_path = run_dir / "report.md"

    if not predictions_path.exists():
        _materialize_predictions(run_dir, predictions_path)
    if not metrics_path.exists():
        _materialize_metrics(run_dir, metrics_path, exit_code)
    if not report_path.exists():
        _materialize_report(run_dir, report_path, exit_code)

    manifest["artifacts"] = {name: str((run_dir / name).resolve()) for name in STANDARD_OUTPUTS if (run_dir / name).exists()}
    _write_json(run_dir / "run_manifest.json", manifest)


def _snapshot_config(target: Path, config_path: str | None, fallback_payload: dict[str, Any]) -> None:
    if config_path:
        source = Path(config_path)
        if source.exists():
            shutil.copyfile(source, target)
            return
    _write_json(target, {"config": fallback_payload})


def _materialize_predictions(run_dir: Path, target: Path) -> None:
    json_candidates = sorted(
        path for path in run_dir.glob("*.json")
        if path.name not in {"benchmark_summary.json", "latest_report_manifest.json", "metrics.json", "run_manifest.json", "dataset_manifest.json", "config_snapshot.json", "hardware.json"}
    )
    for candidate in json_candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows = payload if isinstance(payload, list) else payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue
        with target.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return
    target.write_text("", encoding="utf-8")


def _materialize_metrics(run_dir: Path, target: Path, exit_code: int) -> None:
    summary_path = run_dir / "benchmark_summary.json"
    if summary_path.exists():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            _write_json(
                target,
                {
                    "valid": exit_code == 0,
                    "notes": "Derived from benchmark_summary.json",
                    "summary": payload,
                },
            )
            return
    _write_json(
        target,
        {
            "valid": exit_code == 0,
            "notes": "Legacy adapter did not emit standardized metrics directly.",
        },
    )


def _materialize_report(run_dir: Path, target: Path, exit_code: int) -> None:
    tables_path = run_dir / "metrics_tables.md"
    comparison_path = run_dir / "model_comparison.md"
    lines = [
        "# Benchmark Report",
        "",
        f"- Status: {'success' if exit_code == 0 else 'failed'}",
        f"- Standardized run directory: `{run_dir}`",
    ]
    if tables_path.exists():
        lines.extend(["", "## Metrics Tables", "", tables_path.read_text(encoding="utf-8")])
    elif comparison_path.exists():
        lines.extend(["", "## Comparison", "", comparison_path.read_text(encoding="utf-8")])
    else:
        lines.extend(["", "Legacy runner completed without a standardized markdown report."])
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
