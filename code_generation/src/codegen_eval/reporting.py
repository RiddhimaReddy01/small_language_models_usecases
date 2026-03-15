from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .types import BenchmarkTableManifest, TaskRunResult


def _fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def create_run_directory(output_root: str | Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_root) / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_results_jsonl(results: list[TaskRunResult], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def append_result_jsonl(result: TaskRunResult, path: Path) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def write_summary_json(summaries: list[dict[str, object]], path: Path) -> None:
    path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def render_capability_table(summaries: list[dict[str, object]]) -> str:
    capability_header = (
        "| Model | MBPP Attempted | Total Attempted | pass@1 | "
        "Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | "
        "Format Compliance | Signature Compliance | Instruction Adherence | Unsafe Code Rate |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    capability_rows = []
    for item in summaries:
        capability_rows.append(
            "| {model} | {mbpp} | {total} | {pass1} | {syntax} | {runtime} | {logical} | "
            "{reliability} | {format_ok} | {signature} | {adherence} | {unsafe} |".format(
                model=item["model"],
                mbpp=item["mbpp_attempted"],
                total=item["total_attempted"],
                pass1=_fmt(item["pass@1"]),
                syntax=_fmt(item["syntax_error_rate"]),
                runtime=_fmt(item["runtime_failure_rate"]),
                logical=_fmt(item["logical_failure_rate"]),
                reliability=_fmt(item["reliability_score"]),
                format_ok=_fmt(item["format_compliance"]),
                signature=_fmt(item["signature_compliance"]),
                adherence=_fmt(item["instruction_adherence"]),
                unsafe=_fmt(item["unsafe_code_rate"]),
            )
        )
    return "\n".join([capability_header, *capability_rows, ""])


def render_operational_table(summaries: list[dict[str, object]]) -> str:
    operational_header = (
        "| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | "
        "P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    )
    operational_rows = []
    for item in summaries:
        operational_rows.append(
            "| {model} | {budget} | {completed} | {avg_latency} | {p95} | {tps} | {ram} | {avg_tokens} |".format(
                model=item["model"],
                budget=item["time_budget_minutes"],
                completed=item["tasks_completed_in_budget"],
                avg_latency=_fmt(item["avg_latency_seconds"]),
                p95=_fmt(item["p95_latency_seconds"]),
                tps=_fmt(item["tokens_per_second"]),
                ram=_fmt(item["peak_ram_gb"]),
                avg_tokens=_fmt(item["avg_output_tokens"]),
            )
        )
    return "\n".join([operational_header, *operational_rows, ""])


def render_markdown_report(summaries: list[dict[str, object]]) -> str:
    sections = [
        "# Code Generation Evaluation Report",
        "",
        "## Table A: Capability Metrics",
        render_capability_table(summaries).rstrip(),
        "",
        "## Table B: Operational Metrics",
        render_operational_table(summaries).rstrip(),
        "",
    ]
    return "\n".join(sections)


def write_markdown_report(summaries: list[dict[str, object]], path: Path) -> None:
    path.write_text(render_markdown_report(summaries), encoding="utf-8")


def _write_curated_bundle(
    summaries: list[dict[str, object]],
    output_root: str | Path,
    manifest: BenchmarkTableManifest,
    report_text: str | None = None,
) -> dict[str, str]:
    output_path = Path(output_root)
    tables_dir = output_path / "tables"
    manifests_dir = output_path / "manifests"
    tables_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    capability_path = tables_dir / "capability_metrics.md"
    operational_path = tables_dir / "operational_metrics.md"
    summary_export_path = tables_dir / "latest_summary.json"
    report_export_path = tables_dir / "latest_report.md"
    manifest_path = manifests_dir / "latest_benchmark.json"

    capability_path.write_text(
        "# Capability Metrics\n\n" + render_capability_table(summaries),
        encoding="utf-8",
    )
    operational_path.write_text(
        "# Operational Metrics\n\n" + render_operational_table(summaries),
        encoding="utf-8",
    )
    summary_export_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    report_export_path.write_text(
        report_text if report_text is not None else render_markdown_report(summaries),
        encoding="utf-8",
    )
    manifest.artifacts = {
        "capability_metrics": str(capability_path.resolve()),
        "operational_metrics": str(operational_path.resolve()),
        "latest_summary": str(summary_export_path.resolve()),
        "latest_report": str(report_export_path.resolve()),
    }
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")

    return {
        "tables_dir": str(tables_dir),
        "manifests_dir": str(manifests_dir),
        "manifest_path": str(manifest_path),
        "capability_path": str(capability_path),
        "operational_path": str(operational_path),
        "summary_path": str(summary_export_path),
        "report_path": str(report_export_path),
    }


def export_benchmark_tables(
    run_dir: str | Path,
    output_root: str | Path,
    source_config_path: str | Path | None = None,
) -> dict[str, str]:
    run_path = Path(run_dir)
    summary_path = run_path / "summary.json"
    report_path = run_path / "report.md"
    config_snapshot_path = run_path / "config_snapshot.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary not found: {summary_path}")
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    summaries = _read_json(summary_path)
    config_snapshot = _read_json(config_snapshot_path) if config_snapshot_path.exists() else {}

    manifest = BenchmarkTableManifest(
        exported_at=datetime.now(timezone.utc).isoformat(),
        source_run_dir=str(run_path.resolve()),
        source_summary_path=str(summary_path.resolve()),
        source_report_path=str(report_path.resolve()),
        source_config_snapshot_path=str(config_snapshot_path.resolve()) if config_snapshot_path.exists() else None,
        source_config_path=str(Path(source_config_path).resolve()) if source_config_path else None,
        source_runs=[
            {
                "run_dir": str(run_path.resolve()),
                "summary_path": str(summary_path.resolve()),
                "report_path": str(report_path.resolve()),
                "config_snapshot_path": str(config_snapshot_path.resolve()) if config_snapshot_path.exists() else None,
                "config_path": str(Path(source_config_path).resolve()) if source_config_path else None,
            }
        ],
        evaluation=dict(config_snapshot.get("evaluation", {})),
        generation=dict(config_snapshot.get("generation", {})),
        models=list(config_snapshot.get("models", [])),
    )
    return _write_curated_bundle(
        summaries=summaries,
        output_root=output_root,
        manifest=manifest,
        report_text=report_path.read_text(encoding="utf-8"),
    )


def export_combined_benchmark_tables(
    run_dirs: list[str | Path],
    output_root: str | Path,
    source_config_paths: list[str | Path | None] | None = None,
    deprecate_on_rate_limit: bool = False,
) -> dict[str, str]:
    if not run_dirs:
        raise ValueError("At least one run directory is required.")

    combined_summaries: list[dict[str, object]] = []
    source_runs: list[dict[str, Any]] = []
    deprecated_runs: list[dict[str, Any]] = []
    first_config_snapshot: dict[str, Any] = {}

    if source_config_paths is None:
        source_config_paths = [None] * len(run_dirs)
    elif len(source_config_paths) != len(run_dirs):
        raise ValueError("source_config_paths must match run_dirs length.")

    for run_dir, source_config_path in zip(run_dirs, source_config_paths):
        run_path = Path(run_dir)
        summary_path = run_path / "summary.json"
        report_path = run_path / "report.md"
        config_snapshot_path = run_path / "config_snapshot.json"
        task_results_path = run_path / "task_results.jsonl"
        if not summary_path.exists():
            raise FileNotFoundError(f"Summary not found: {summary_path}")
        if not report_path.exists():
            raise FileNotFoundError(f"Report not found: {report_path}")

        task_results = _read_jsonl(task_results_path)
        rate_limited = any(
            any(
                marker in str(item.get("error_message", "")).lower()
                for marker in ("rate limit", "resource exhausted", "quota exceeded", "429 ")
            )
            for item in task_results
        )
        run_record = {
            "run_dir": str(run_path.resolve()),
            "summary_path": str(summary_path.resolve()),
            "report_path": str(report_path.resolve()),
            "config_snapshot_path": str(config_snapshot_path.resolve()) if config_snapshot_path.exists() else None,
            "config_path": str(Path(source_config_path).resolve()) if source_config_path else None,
            "rate_limited": rate_limited,
        }
        if rate_limited and deprecate_on_rate_limit:
            deprecated_runs.append({**run_record, "status": "deprecated_rate_limit"})
            continue

        combined_summaries.extend(_read_json(summary_path))
        source_runs.append(run_record)
        if not first_config_snapshot and config_snapshot_path.exists():
            first_config_snapshot = _read_json(config_snapshot_path)

    if not combined_summaries:
        raise RuntimeError("No summaries available to export after filtering deprecated runs.")

    manifest = BenchmarkTableManifest(
        exported_at=datetime.now(timezone.utc).isoformat(),
        source_run_dir=source_runs[0]["run_dir"],
        source_summary_path=source_runs[0]["summary_path"],
        source_report_path=source_runs[0]["report_path"],
        source_config_snapshot_path=source_runs[0].get("config_snapshot_path"),
        source_config_path=source_runs[0].get("config_path"),
        source_runs=source_runs,
        deprecated_runs=deprecated_runs,
        evaluation=dict(first_config_snapshot.get("evaluation", {})),
        generation=dict(first_config_snapshot.get("generation", {})),
        models=[
            model
            for source_run in source_runs
            for model in (
                _read_json(Path(source_run["config_snapshot_path"])).get("models", [])
                if source_run.get("config_snapshot_path")
                else []
            )
        ],
    )
    return _write_curated_bundle(summaries=combined_summaries, output_root=output_root, manifest=manifest)
