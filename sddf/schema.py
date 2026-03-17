from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_RESULT_COLUMNS = [
    "example_id",
    "task",
    "dataset",
    "model_name",
    "model_family",
    "prediction",
    "reference",
    "primary_metric",
    "valid_output",
    "latency_sec",
    "memory_mb",
    "cpu_util",
    "difficulty_dim",
    "difficulty_score",
]


def validate_results_schema(df: pd.DataFrame, required_columns: list[str] | None = None) -> None:
    required = required_columns or REQUIRED_RESULT_COLUMNS
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Results dataframe is missing required columns: {missing}")


def build_results_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    validate_results_schema(df)
    return df
