from __future__ import annotations

import math
from collections import Counter
from typing import Any

import pandas as pd


TASK_DIMENSION_MAP = {
    "classification": "H",
    "summarization": "n_in",
    "retrieval_grounded": "n_in",
    "information_extraction": "|Gamma|",
    "instruction_following": "|Gamma|",
    "text_generation": "|Gamma|",
    "maths": "R_hat",
    "code_generation": "R_hat",
}


def compute_n_in(text: str, mode: str = "tokens") -> float:
    if not text:
        return 0.0
    if mode == "chars":
        return float(len(text))
    return float(len(str(text).split()))


def compute_entropy(text: str, level: str = "token") -> float:
    if not text:
        return 0.0
    units = str(text).split() if level == "token" else list(str(text))
    if not units:
        return 0.0
    counts = Counter(units)
    total = len(units)
    probs = [count / total for count in counts.values()]
    return float(-sum(prob * math.log2(prob) for prob in probs if prob > 0))


def _coerce_example(example: dict[str, Any] | str | None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(example, dict):
        payload = dict(example)
    else:
        payload = {}
        if example is not None:
            payload["text"] = str(example)
    if metadata:
        payload.update(metadata)
    return payload


def compute_constraint_count(example: dict[str, Any] | str, rules: dict[str, Any] | None = None) -> float:
    if not isinstance(example, dict):
        example = {"text": str(example)}

    count = 0
    count += len(example.get("required_fields", []) or [])
    count += len(example.get("format_rules", []) or [])
    count += len(example.get("content_rules", []) or [])
    count += len(example.get("length_rules", []) or [])
    count += len(example.get("ordering_rules", []) or [])

    if rules:
        count += len(rules.get("required_fields", []) or [])
        count += len(rules.get("format_rules", []) or [])
        count += len(rules.get("content_rules", []) or [])
        count += len(rules.get("length_rules", []) or [])
        count += len(rules.get("ordering_rules", []) or [])
    return float(count)


def compute_reasoning_proxy(example: dict[str, Any], baseline_stats: dict[str, Any] | None = None) -> float:
    # R_hat is a baseline-estimated reasoning proxy derived from observable signals.
    # It is not ground-truth reasoning complexity.
    score = 0.0
    question = str(example.get("question", example.get("prompt", example.get("text", ""))))
    score += len(question.split()) * 0.05
    score += float(example.get("num_steps", 0) or 0) * 1.0
    score += float(example.get("num_entities", 0) or 0) * 0.5
    score += float(example.get("has_composition", 0) or 0) * 1.0

    if baseline_stats:
        score += float(baseline_stats.get("step_weight_bonus", 0.0) or 0.0)
    return float(score)


def _dimension_for_task(task: str, rule_config: dict[str, Any] | None = None) -> str:
    task_map = TASK_DIMENSION_MAP.copy()
    if rule_config and rule_config.get("task_dimension_map"):
        task_map.update(rule_config["task_dimension_map"])
    return task_map.get(task, "n_in")


def _score_for_dimension(
    dimension: str,
    example: dict[str, Any],
    text: str,
    rule_config: dict[str, Any] | None = None,
) -> float:
    rules = rule_config or {}
    if dimension == "n_in":
        return compute_n_in(text, mode=rules.get("n_in_mode", "tokens"))
    if dimension == "H":
        return compute_entropy(text, level=rules.get("entropy_level", "token"))
    if dimension == "|Gamma|":
        return compute_constraint_count(example, rules=rules.get("constraint_rules"))
    if dimension == "R_hat":
        return compute_reasoning_proxy(example, baseline_stats=rules.get("baseline_stats"))
    raise ValueError(f"Unsupported difficulty dimension: {dimension}")


def annotate_dominant_dimension(
    df: pd.DataFrame,
    task: str,
    text_col: str = "input_text",
    prompt_col: str | None = None,
    metadata_col: str | None = None,
    rule_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    dimension = _dimension_for_task(task, rule_config=rule_config)

    def annotate_row(row: pd.Series) -> pd.Series:
        prompt_text = str(row.get(prompt_col, "")) if prompt_col else ""
        body_text = str(row.get(text_col, "")) if text_col in row else ""
        merged_text = " ".join(part for part in [body_text, prompt_text] if part).strip()
        metadata = row.get(metadata_col) if metadata_col else None
        if metadata_col and metadata is not None and not isinstance(metadata, dict):
            metadata = {"metadata": metadata}
        example = _coerce_example(row.to_dict(), metadata=metadata)
        score = _score_for_dimension(dimension, example, merged_text, rule_config=rule_config)
        row["difficulty_dim"] = dimension
        row["difficulty_score"] = float(score)
        return row

    return out.apply(annotate_row, axis=1)


def make_difficulty_bins(
    df: pd.DataFrame,
    score_col: str = "difficulty_score",
    n_bins: int = 5,
    method: str = "quantile",
) -> pd.DataFrame:
    out = df.copy()
    if score_col not in out.columns:
        raise ValueError(f"Missing score column: {score_col}")
    if out[score_col].dropna().empty:
        out["difficulty_bin"] = pd.Series([pd.NA] * len(out), dtype="Int64")
        return out

    if method == "quantile":
        out["difficulty_bin"] = pd.qcut(out[score_col], q=n_bins, labels=False, duplicates="drop")
    elif method == "uniform":
        out["difficulty_bin"] = pd.cut(out[score_col], bins=n_bins, labels=False, include_lowest=True)
    else:
        raise ValueError("method must be 'quantile' or 'uniform'")

    out["difficulty_bin"] = out["difficulty_bin"].astype("Int64")
    return out
