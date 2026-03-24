from __future__ import annotations

import pandas as pd
from typing import Mapping


def label_slm_acceptability(
    matched: pd.DataFrame, quality_threshold: float = 0.85
) -> pd.DataFrame:
    """Mark whether an SLM output meets the quality threshold."""
    df = matched.copy()
    df["slm_accept"] = (
        (df.get("primary_metric_slm", 0.0) >= quality_threshold)
        & (df.get("valid_output_slm", 0) == 1)
    )
    return df


def apply_quality_gate(labeled: pd.DataFrame, thresholds: Mapping[str, float]) -> pd.DataFrame:
    """Apply difficulty/latency gates to decide whether the SLM stays in production."""
    df = labeled.copy()
    diff_thresh = float(thresholds.get("max_difficulty", 1.0))
    latency_thresh = float(thresholds.get("max_latency_sec", float("inf")))
    df["gate_pass"] = (
        (df["difficulty_score"] <= diff_thresh)
        & (df["latency_sec_slm"] <= latency_thresh)
        & df["slm_accept"].fillna(False)
    )
    return df


def evaluate_quality_gate(gated: pd.DataFrame) -> dict[str, float]:
    """Compute precision/recall for the quality gate predictions."""
    predicted_source = gated.get("gate_pass", gated.get("y_pred_accept", pd.Series([False] * len(gated))))
    predicted = predicted_source.fillna(False).astype(bool)
    actual = gated.get("valid_output_slm", pd.Series([False] * len(gated))).fillna(0) == 1
    tp = (predicted & actual).sum()
    predicted_count = predicted.sum()
    actual_count = actual.sum()
    precision = float(tp / predicted_count) if predicted_count > 0 else 0.0
    recall = float(tp / actual_count) if actual_count > 0 else 0.0
    return {"precision": precision, "recall": recall}
