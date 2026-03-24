from __future__ import annotations

import numpy as np
import pandas as pd

from .curves import compute_ratio_curve, smooth_ratio_curve
from .tipping import estimate_tipping_point


def bootstrap_ratio_curve(
    matched_df: pd.DataFrame,
    n_boot: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    bins = sorted(matched_df["difficulty_bin"].dropna().unique())
    boot_rows: list[pd.Series] = []

    for _ in range(n_boot):
        sample = matched_df.sample(len(matched_df), replace=True, random_state=int(rng.integers(1_000_000_000)))
        curve = compute_ratio_curve(sample)
        boot_rows.append(curve.set_index("difficulty_bin")["ratio"])

    if not boot_rows:
        return pd.DataFrame(columns=["difficulty_bin", "ratio_ci_low", "ratio_ci_high", "ratio_boot_mean"])

    boot = pd.concat(boot_rows, axis=1).T
    summary = []
    for difficulty_bin in bins:
        values = boot[difficulty_bin].dropna().values
        summary.append(
            {
                "difficulty_bin": difficulty_bin,
                "ratio_ci_low": float(np.percentile(values, 2.5)),
                "ratio_ci_high": float(np.percentile(values, 97.5)),
                "ratio_boot_mean": float(np.mean(values)),
            }
        )
    return pd.DataFrame(summary)


def bootstrap_tipping_point(
    matched_df: pd.DataFrame,
    threshold: float = 0.95,
    n_boot: int = 1000,
    random_state: int = 42,
) -> dict[str, float | None]:
    rng = np.random.default_rng(random_state)
    tips: list[float] = []

    for _ in range(n_boot):
        sample = matched_df.sample(len(matched_df), replace=True, random_state=int(rng.integers(1_000_000_000)))
        curve = compute_ratio_curve(sample)
        smooth = smooth_ratio_curve(curve)
        tip = estimate_tipping_point(smooth, threshold=threshold)
        if tip is not None:
            tips.append(tip)

    if not tips:
        return {"tipping_point": None, "ci_low": None, "ci_high": None}

    return {
        "tipping_point": float(np.median(tips)),
        "ci_low": float(np.percentile(tips, 2.5)),
        "ci_high": float(np.percentile(tips, 97.5)),
    }
