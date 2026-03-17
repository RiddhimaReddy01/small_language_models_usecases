from __future__ import annotations

import pandas as pd


def match_model_outputs(results_df: pd.DataFrame, slm_name: str, llm_name: str) -> pd.DataFrame:
    slm = results_df[results_df["model_name"] == slm_name].copy()
    llm = results_df[results_df["model_name"] == llm_name].copy()

    cols = [
        "example_id",
        "difficulty_score",
        "difficulty_bin",
        "primary_metric",
        "valid_output",
        "latency_sec",
    ]
    missing = [column for column in cols if column not in results_df.columns]
    if missing:
        raise ValueError(f"Results dataframe is missing required matching columns: {missing}")

    slm = slm[cols].rename(
        columns={
            "primary_metric": "primary_metric_slm",
            "valid_output": "valid_output_slm",
            "latency_sec": "latency_sec_slm",
        }
    )
    llm = llm[cols].rename(
        columns={
            "primary_metric": "primary_metric_llm",
            "valid_output": "valid_output_llm",
            "latency_sec": "latency_sec_llm",
        }
    )

    return slm.merge(llm, on=["example_id", "difficulty_score", "difficulty_bin"], how="inner")
