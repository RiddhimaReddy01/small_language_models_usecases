from __future__ import annotations

from typing import Any

from .s3_feature_scoring import score_s3_dimensions


DEFAULT_S3_WEIGHTS: dict[str, int] = {
    "TC": 3,
    "OS": 2,
    "SK": 4,
    "DS": 2,
    "LT": 3,
    "VL": 1,
}

_REQ_DIMS: tuple[str, ...] = ("TC", "OS", "SK", "DS", "LT", "VL")


def normalize_weights(weights: dict[str, Any] | None) -> dict[str, int]:
    src = dict(DEFAULT_S3_WEIGHTS if weights is None else weights)
    out: dict[str, int] = {}
    for dim in _REQ_DIMS:
        if dim not in src:
            raise ValueError(f"Missing weight dimension: {dim}")
        val = int(src[dim])
        if val < 1:
            raise ValueError(f"Weight must be >=1 for {dim}, got {val}")
        out[dim] = val
    if out["SK"] < out["TC"]:
        raise ValueError("Invalid weight profile: must satisfy SK >= TC")
    return out


def build_task_scores(task_inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for task, payload in task_inputs.items():
        cfg = dict(payload)
        cfg.setdefault("task", task)
        cfg.setdefault("prompt", str(payload.get("prompt", task.replace("_", " "))))
        out[task] = score_s3_dimensions(cfg)
    return out


def _default_profile(task_scores: dict[str, dict[str, int]]) -> dict[str, int]:
    if not task_scores:
        return {k: 3 for k in _REQ_DIMS}
    n = float(len(task_scores))
    return {
        dim: int(round(sum(float(scores[dim]) for scores in task_scores.values()) / n))
        for dim in _REQ_DIMS
    }


def build_s3_task_config(
    weights: dict[str, Any] | None,
    task_inputs: dict[str, dict[str, Any]],
    include_default_profile: bool = True,
) -> dict[str, Any]:
    w = normalize_weights(weights)
    scores = build_task_scores(task_inputs)
    task_scores: dict[str, Any] = {}
    if include_default_profile:
        task_scores["*"] = _default_profile(scores)
    task_scores.update(scores)
    return {"weights": w, "task_scores": task_scores}

