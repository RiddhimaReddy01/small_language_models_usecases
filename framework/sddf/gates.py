from __future__ import annotations

import pandas as pd


def label_slm_acceptability(
    matched_df: pd.DataFrame,
    quality_threshold: float,
    valid_required: bool = True,
) -> pd.DataFrame:
    out = matched_df.copy()
    validity_mask = (out["valid_output_slm"] == 1) if valid_required else True
    out["y_true_accept"] = ((out["primary_metric_slm"] >= quality_threshold) & validity_mask).astype(int)
    return out


def apply_quality_gate(matched_df: pd.DataFrame, gate_rules: dict) -> pd.DataFrame:
    out = matched_df.copy()
    max_latency_sec = gate_rules.get("max_latency_sec", float("inf"))
    out["y_pred_accept"] = (
        (out["difficulty_score"] <= gate_rules["max_difficulty"])
        & (out["valid_output_slm"] == 1)
        & (out["latency_sec_slm"] <= max_latency_sec)
    ).astype(int)
    return out


def _safe_divide(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def evaluate_quality_gate(gated_df: pd.DataFrame) -> dict[str, float]:
    y_true = gated_df["y_true_accept"].astype(int)
    y_pred = gated_df["y_pred_accept"].astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    return {"precision": float(precision), "recall": float(recall), "f1": float(f1)}
