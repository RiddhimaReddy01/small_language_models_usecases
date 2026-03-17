from __future__ import annotations

import numpy as np
import pandas as pd

from .gates import evaluate_quality_gate, label_slm_acceptability


def learn_routing_thresholds(matched_df: pd.DataFrame, target_precision: float = 0.95) -> dict | None:
    labeled = label_slm_acceptability(matched_df.copy(), quality_threshold=0.85)
    difficulties = labeled["difficulty_score"]
    if difficulties.empty:
        return None

    best = None
    for threshold in np.linspace(float(difficulties.min()), float(difficulties.max()), 50):
        trial = labeled.copy()
        trial["y_pred_accept"] = (trial["difficulty_score"] <= threshold).astype(int)
        metrics = evaluate_quality_gate(trial)
        if metrics["precision"] >= target_precision:
            best = {
                "max_difficulty": float(threshold),
                "gate_precision": float(metrics["precision"]),
                "gate_recall": float(metrics["recall"]),
            }
            break
    return best


def route_example(example: dict, thresholds: dict) -> str:
    difficulty = example["difficulty_score"]
    if difficulty <= thresholds["max_difficulty"]:
        return "SLM"
    return "LLM"


def route_example_three_way(example: dict, thresholds: dict) -> str:
    difficulty = example["difficulty_score"]
    if difficulty <= thresholds["safe_max"]:
        return "SLM"
    if difficulty <= thresholds["hybrid_max"]:
        return "SLM_WITH_GATE"
    return "LLM"
