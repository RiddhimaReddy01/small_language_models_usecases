from __future__ import annotations

import pandas as pd


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
