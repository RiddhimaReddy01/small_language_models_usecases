from __future__ import annotations

import pandas as pd


def estimate_tipping_point(
    curve: pd.DataFrame,
    threshold: float = 0.95,
    require_consecutive: int = 2,
) -> float | None:
    """Estimate the difficulty where the capability ratio permanently falls below *threshold*."""
    if curve.empty:
        return None

    df = curve.copy()
    df = df.sort_values(by="difficulty_score") if "difficulty_score" in df.columns else df
    ratio_col = "ratio_smooth" if "ratio_smooth" in df.columns else "ratio"
    consecutive: list[float] = []

    for _, row in df.iterrows():
        ratio = float(row.get(ratio_col, 0.0))
        difficulty = float(row.get("difficulty_score", 0.0))
        if ratio < threshold:
            consecutive.append(difficulty)
            if len(consecutive) >= require_consecutive:
                return consecutive[-require_consecutive]
        else:
            consecutive.clear()
    return None
