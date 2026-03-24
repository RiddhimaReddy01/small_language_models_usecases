from __future__ import annotations

import pandas as pd


def _rename_columns(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
    col_map: dict[str, str] = {}
    for key in ["primary_metric", "valid_output", "latency_sec"]:
        if key in df.columns:
            col_map[key] = f"{key}_{suffix}"
    return df.rename(columns=col_map)


def match_model_outputs(
    results: pd.DataFrame, slm_name: str, llm_name: str, join_cols: list[str] | None = None
) -> pd.DataFrame:
    """Join SLM and LLM model outputs on shared identifiers."""
    slm = results[results["model_name"] == slm_name].copy()
    llm = results[results["model_name"] == llm_name].copy()

    slm = _rename_columns(slm, "slm")
    llm = _rename_columns(llm, "llm")

    if join_cols is None:
        join_cols = [col for col in ["example_id", "difficulty_score", "difficulty_bin"] if col in slm.columns and col in llm.columns]
    matched = pd.merge(slm, llm, on=join_cols, how="inner", suffixes=("", ""))
    matched = matched.drop_duplicates(subset=join_cols)
    return matched
