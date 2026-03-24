from __future__ import annotations

import json
from pathlib import Path


def generate_part_a_report(task: str, results_path: str | Path, output_dir: str | Path | None = None) -> dict[str, str]:
    source = Path(results_path)
    destination = Path(output_dir) if output_dir else source.parent / "reports"
    destination.mkdir(parents=True, exist_ok=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    report_path = destination / "part_a_report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Part A - Benchmark Setup",
                "",
                "## Task Definition",
                f"Task: {task}",
                f"Seed: {payload.get('seed', 'unknown')}",
            ]
        ),
        encoding="utf-8",
    )
    return {"report_path": str(report_path)}
