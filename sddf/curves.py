from __future__ import annotations

import pandas as pd


def compute_ratio_curve(matched: pd.DataFrame) -> pd.DataFrame:
    """Compute the capability ratio curve between an SLM and LLM."""
    if matched.empty:
        return pd.DataFrame(columns=["difficulty_score", "ratio"])

    df = matched.copy()
    df = df.dropna(subset=["primary_metric_slm", "primary_metric_llm", "difficulty_score"])
    df["ratio"] = df["primary_metric_slm"] / df["primary_metric_llm"].clip(lower=1e-9)

    grouped = (
        df.groupby("difficulty_score", sort=True)
        .agg(
            ratio=("ratio", "mean"),
            latency_sec_slm=("latency_sec_slm", "mean"),
            latency_sec_llm=("latency_sec_llm", "mean"),
        )
        .reset_index()
    )
    return grouped


def smooth_ratio_curve(
    curve: pd.DataFrame,
    method: str = "rolling",
    frac: float = 0.5,
    **kwargs,
) -> pd.DataFrame:
    """Smooth the ratio curve to make tipping-point estimation more stable."""
    if "ratio" not in curve.columns:
        return curve.copy()

    out = curve.copy()
    if method == "rolling":
        length = len(out)
        window = max(1, int(max(1.0, length * frac)))
        out["ratio_smooth"] = out["ratio"].rolling(window=window, min_periods=1, center=False).mean()
    elif method in {"ewm", "exponential"}:
        alpha = kwargs.get("alpha", frac)
        out["ratio_smooth"] = out["ratio"].ewm(alpha=alpha, adjust=False).mean()
    else:
        out["ratio_smooth"] = out["ratio"].copy()
    return out
