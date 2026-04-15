from __future__ import annotations

from sddf.s3_config_builder import build_s3_task_config, normalize_weights


def test_normalize_weights_validates_and_keeps_dims() -> None:
    weights = normalize_weights({"TC": 3, "OS": 2, "SK": 4, "DS": 2, "LT": 3, "VL": 1})
    assert set(weights.keys()) == {"TC", "OS", "SK", "DS", "LT", "VL"}
    assert weights["SK"] >= weights["TC"]


def test_build_s3_task_config_from_inputs() -> None:
    cfg = build_s3_task_config(
        weights={"TC": 3, "OS": 2, "SK": 4, "DS": 2, "LT": 3, "VL": 1},
        task_inputs={
            "classification": {"prompt": "Classify support tickets.", "target_p99_ms": 800, "qps": 100},
            "maths": {"prompt": "Solve equations and provide exact answers.", "target_p99_ms": 1200, "qps": 20},
        },
        include_default_profile=True,
    )
    assert "weights" in cfg
    assert "task_scores" in cfg
    assert "*" in cfg["task_scores"]
    assert "classification" in cfg["task_scores"]
    assert "maths" in cfg["task_scores"]
    for task_name in ("*", "classification", "maths"):
        assert set(cfg["task_scores"][task_name].keys()) == {"TC", "OS", "SK", "DS", "LT", "VL"}

