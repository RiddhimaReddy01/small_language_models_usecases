from __future__ import annotations

import pandas as pd


def assign_deployment_zone(
    row: pd.Series,
    ratio_threshold_safe: float = 0.95,
    ratio_threshold_hybrid: float = 0.85,
    latency_budget: float | None = None,
) -> str:
    ratio = row["ratio_smooth"]
    if latency_budget is not None and row.get("latency_sec_slm", 0) > latency_budget:
        return "C"
    if ratio >= ratio_threshold_safe:
        return "A"
    if ratio >= ratio_threshold_hybrid:
        return "B"
    return "C"


def assign_zone_capability_ops(row: pd.Series, safe_tau: float = 0.95, hybrid_tau: float = 0.85) -> str:
    cap = row["ratio_smooth"]
    valid = row.get("valid_output_slm", 1)
    latency_ok = row.get("latency_ok", 1)
    format_ok = row.get("format_ok", 1)

    if cap >= safe_tau and valid and latency_ok and format_ok:
        return "A"
    if cap >= hybrid_tau and valid:
        return "B"
    return "C"
