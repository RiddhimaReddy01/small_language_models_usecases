from __future__ import annotations

import pandas as pd

DEFAULT_TIPPING_THRESHOLDS = [0.90, 0.93, 0.95, 0.97]


def estimate_tipping_point(
    smooth_df: pd.DataFrame,
    threshold: float = 0.95,
    require_consecutive: int = 2,
) -> float | None:
    below = (smooth_df["ratio_smooth"] < threshold).astype(int).tolist()
    xs = smooth_df["bin_center"].tolist()

    run = 0
    for index, flag in enumerate(below):
        if flag:
            run += 1
            if run >= require_consecutive:
                return float(xs[index - require_consecutive + 1])
        else:
            run = 0
    return None


def tipping_sensitivity(
    smooth_df: pd.DataFrame,
    thresholds: list[float] | None = None,
    require_consecutive: int = 2,
) -> dict[str, float | None]:
    thresholds = thresholds or DEFAULT_TIPPING_THRESHOLDS
    return {
        f"{threshold:.2f}": estimate_tipping_point(
            smooth_df,
            threshold=threshold,
            require_consecutive=require_consecutive,
        )
        for threshold in thresholds
    }
