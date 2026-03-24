from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .difficulty import annotate_dominant_dimension, make_difficulty_bins


def run_sddf_postprocess(rows: pd.DataFrame, task: str, output_dir: str | Path) -> dict[str, Any]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    annotated = annotate_dominant_dimension(rows, task=task)
    binned = make_difficulty_bins(annotated, n_bins=min(5, max(1, len(annotated))))
    archive_path = destination / f"{task}_canonical_rows.jsonl"
    with archive_path.open("w", encoding="utf-8") as handle:
        for row in binned.to_dict("records"):
            handle.write(json.dumps(row) + "\n")
    return {"archive_path": str(archive_path), "row_count": len(binned)}
