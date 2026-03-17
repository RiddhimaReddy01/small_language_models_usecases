from __future__ import annotations

from pathlib import Path

import pandas as pd


def plot_ratio_curve(
    ratio_df: pd.DataFrame,
    output_path: str | Path,
    x_col: str = "bin_center",
    y_col: str = "ratio",
    y_smooth_col: str = "ratio_smooth",
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError("matplotlib is required for SDDF plotting") from exc

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 4))
    plt.plot(ratio_df[x_col], ratio_df[y_col], marker="o", label="Ratio")
    if y_smooth_col in ratio_df.columns:
        plt.plot(ratio_df[x_col], ratio_df[y_smooth_col], linewidth=2, label="Smoothed")
    plt.axhline(0.95, color="tab:red", linestyle="--", linewidth=1, label="0.95 threshold")
    plt.xlabel("Difficulty")
    plt.ylabel("SLM / LLM ratio")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return output
