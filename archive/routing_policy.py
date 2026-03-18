from __future__ import annotations

from typing import Any

import pandas as pd

from sddf.routing import learn_routing_thresholds


def route(task_difficulty: float, threshold: float) -> str:
    return "SLM" if task_difficulty < threshold else "LLM"


def optimize_threshold(curve: pd.DataFrame, target_precision: float = 0.95) -> dict[str, Any] | None:
    return learn_routing_thresholds(curve, target_precision=target_precision)
