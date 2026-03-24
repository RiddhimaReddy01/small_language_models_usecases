from __future__ import annotations

import json
from pathlib import Path

from ie_benchmark.reporting import write_csv, write_json, write_markdown_table


def _load_summary(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sort_rows(rows: list[dict[str, object]], key: str) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: float("-inf") if row.get(key) is None else float(row[key]),
        reverse=True,
    )


def export_final_results(
    summary_paths: list[str],
    output_dir: str,
    include_models: list[str] | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    capability_rows: list[dict[str, object]] = []
    operational_rows: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []

    selected_models = set(include_models or [])

    for summary_path in summary_paths:
        summary = _load_summary(summary_path)
        for model_summary in summary.get("models", []):
            model_name = model_summary.get("model")
            if selected_models and model_name not in selected_models:
                continue
            capability_rows.append(model_summary["capability_metrics"])
            operational_rows.append(model_summary["operational_metrics"])
            sources.append(
                {
                    "model": model_name,
                    "summary_path": summary_path,
                    "benchmark_name": summary.get("benchmark_name"),
                    "sample_size": summary.get("sample_size"),
                }
            )

    capability_rows = _sort_rows(capability_rows, "Micro F1")
    operational_rows = _sort_rows(operational_rows, "Throughput (docs/min)")

    write_csv(output_path / "final_capability_metrics.csv", capability_rows)
    write_csv(output_path / "final_operational_metrics.csv", operational_rows)
    write_markdown_table(output_path / "final_capability_metrics.md", capability_rows)
    write_markdown_table(output_path / "final_operational_metrics.md", operational_rows)
    write_json(output_path / "final_sources.json", {"sources": sources})
    return output_path
