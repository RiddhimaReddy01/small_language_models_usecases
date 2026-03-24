from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_historical_runs(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    runs = []
    for results_path in root.glob("*/*/raw/*.json"):
        benchmark = results_path.parts[-4]
        payload = json.loads(results_path.read_text(encoding="utf-8"))
        notes = []
        overall_status = "complete"
        if payload.get("mode") == "dry_run":
            overall_status = "partial"
            notes.append("dry_run detected")
        runs.append(
            {
                "benchmark": benchmark,
                "path": str(results_path),
                "overall_status": overall_status,
                "notes": notes,
            }
        )
    return {"runs": runs}


def save_historical_run_validation(repo_root: str | Path, output_path: str | Path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = validate_historical_runs(repo_root)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination
