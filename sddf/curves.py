from __future__ import annotations

import pandas as pd


def compute_ratio_curve(
    matched_df: pd.DataFrame,
    metric_col_slm: str = "primary_metric_slm",
    metric_col_llm: str = "primary_metric_llm",
    bin_col: str = "difficulty_bin",
    higher_is_better: bool = True,
    eps: float = 1e-8,
) -> pd.DataFrame:
    rows = []
    for difficulty_bin, group in matched_df.groupby(bin_col):
        slm_mean = float(group[metric_col_slm].mean())
        llm_mean = float(group[metric_col_llm].mean())

        if higher_is_better:
            ratio = slm_mean / max(llm_mean, eps)
        else:
            ratio = llm_mean / max(slm_mean, eps)

        rows.append(
            {
                "difficulty_bin": difficulty_bin,
                "n": int(len(group)),
                "metric_slm": slm_mean,
                "metric_llm": llm_mean,
                "ratio": float(ratio),
                "delta": float(slm_mean - llm_mean),
                "bin_center": float(group["difficulty_score"].mean()),
                "latency_sec_slm": float(group["latency_sec_slm"].mean()) if "latency_sec_slm" in group else None,
                "latency_sec_llm": float(group["latency_sec_llm"].mean()) if "latency_sec_llm" in group else None,
                "valid_output_slm": float(group["valid_output_slm"].mean()) if "valid_output_slm" in group else None,
                "valid_output_llm": float(group["valid_output_llm"].mean()) if "valid_output_llm" in group else None,
            }
        )
    return pd.DataFrame(rows).sort_values("difficulty_bin").reset_index(drop=True)


def smooth_ratio_curve(
    ratio_df: pd.DataFrame,
    x_col: str = "bin_center",
    y_col: str = "ratio",
    method: str = "lowess",
    frac: float = 0.6,
) -> pd.DataFrame:
    out = ratio_df.sort_values(x_col).copy()
    if len(out) < 3:
        out["ratio_smooth"] = out[y_col]
        return out

    if method == "lowess":
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess

            out["ratio_smooth"] = lowess(out[y_col], out[x_col], frac=frac, return_sorted=False)
            return out
        except Exception:
            method = "rolling"

    if method == "rolling":
        window = max(2, min(len(out), int(round(len(out) * frac))))
        out["ratio_smooth"] = out[y_col].rolling(window=window, min_periods=1, center=True).mean()
        return out

    raise ValueError("method must be 'lowess' or 'rolling'")
