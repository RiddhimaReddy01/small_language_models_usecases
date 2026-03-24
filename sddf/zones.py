from __future__ import annotations

import pandas as pd


def assign_deployment_zone(
    row: pd.Series,
    ratio_threshold_safe: float = 0.95,
    ratio_threshold_hybrid: float = 0.85,
) -> str:
    """Map the smoothed ratio to deployment zones (A/B/C)."""
    ratio = float(row.get("ratio_smooth", row.get("ratio", 0.0)))
    if ratio >= ratio_threshold_safe:
        return "A"
    if ratio >= ratio_threshold_hybrid:
        return "B"
    return "C"
