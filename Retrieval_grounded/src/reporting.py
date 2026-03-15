"""Reporting helpers for benchmark outputs."""

import csv
import json
from io import StringIO
from pathlib import Path


CAPABILITY_COLUMNS = [
    ("Model", None),
    ("Exact Match (%)", "exact_match"),
    ("F1 Score (%)", "f1_score"),
    ("Context Utilization (%)", "context_utilization_rate"),
    ("Answer Length Accuracy (%)", "answer_length_accuracy"),
]

OPERATIONAL_COLUMNS = [
    ("Model", None),
    ("Avg Latency (ms)", "latency_ms"),
    ("P50 (ms)", "latency_p50_ms"),
    ("P95 (ms)", "latency_p95_ms"),
    ("Tokens/sec", "tokens_per_sec"),
    ("Output Tokens", "output_tokens_total"),
    ("Avg Input Tokens", "input_tokens_avg"),
    ("Memory (MB)", "memory_mb"),
    ("Wall Time (s)", "wall_time_sec"),
    ("Questions", "questions"),
]


def save_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return ""
    return str(value)


def _build_table_rows(results: dict, section: str, columns: list[tuple[str, str | None]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for model_name, model_result in results.items():
        section_data = model_result.get(section, {})
        row = [model_name]
        for _, key in columns[1:]:
            row.append(_format_metric(section_data.get(key, "")))
        rows.append(row)
    return rows


def _render_markdown_table(columns: list[tuple[str, str | None]], rows: list[list[str]]) -> str:
    headers = [label for label, _ in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _render_csv(columns: list[tuple[str, str | None]], rows: list[list[str]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([label for label, _ in columns])
    writer.writerows(rows)
    return buffer.getvalue()


def generate_markdown_summary(results: dict) -> str:
    capability_rows = _build_table_rows(results, "capability", CAPABILITY_COLUMNS)
    operational_rows = _build_table_rows(results, "operational", OPERATIONAL_COLUMNS)
    lines = [
        "# Experiment Report",
        "",
        "## Capability Metrics",
        _render_markdown_table(CAPABILITY_COLUMNS, capability_rows),
        "",
        "## Operational Metrics",
        _render_markdown_table(OPERATIONAL_COLUMNS, operational_rows),
        "",
    ]
    return "\n".join(lines)


def generate_reproducibility_notes(config: dict, environment: dict) -> str:
    lines = [
        "# Reproducibility Notes",
        "",
        "## Configuration",
        f"- Dataset: {config.get('dataset_name', 'unknown')}",
        f"- Questions: {config.get('num_questions', 'unknown')}",
        f"- Device: {config.get('device', 'unknown')}",
        f"- Temperature: {config.get('temperature', 'unknown')}",
        f"- `do_sample`: {config.get('do_sample', 'unknown')}",
        "",
        "## Environment",
        f"- Platform: {environment.get('platform', 'unknown')}",
        f"- Python: {environment.get('python_version', 'unknown')}",
        f"- PyTorch: {environment.get('torch_version', 'unknown')}",
        f"- Transformers: {environment.get('transformers_version', 'unknown')}",
        "",
        "## Portability",
        "- CPU runs are the most portable across laptops.",
        "- First-time runs still depend on internet/model cache availability.",
        "- Results should be close across laptops with the same config and package versions, but latency and memory will vary by hardware.",
    ]
    return "\n".join(lines)


def save_metric_tables(output_dir: Path, results: dict, config: dict, environment: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    capability_rows = _build_table_rows(results, "capability", CAPABILITY_COLUMNS)
    operational_rows = _build_table_rows(results, "operational", OPERATIONAL_COLUMNS)

    (output_dir / "capability_metrics.md").write_text(
        _render_markdown_table(CAPABILITY_COLUMNS, capability_rows) + "\n",
        encoding="utf-8",
    )
    (output_dir / "operational_metrics.md").write_text(
        _render_markdown_table(OPERATIONAL_COLUMNS, operational_rows) + "\n",
        encoding="utf-8",
    )
    (output_dir / "capability_metrics.csv").write_text(
        _render_csv(CAPABILITY_COLUMNS, capability_rows),
        encoding="utf-8",
    )
    (output_dir / "operational_metrics.csv").write_text(
        _render_csv(OPERATIONAL_COLUMNS, operational_rows),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        generate_markdown_summary(results),
        encoding="utf-8",
    )
    (output_dir / "reproducibility.md").write_text(
        generate_reproducibility_notes(config, environment) + "\n",
        encoding="utf-8",
    )
