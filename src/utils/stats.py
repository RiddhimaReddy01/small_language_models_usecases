"""Statistical utilities for confidence intervals and probability calculations."""

import math
from typing import Optional, Tuple


def wilson_interval(p: float, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute Wilson score confidence interval for a proportion.

    Args:
        p: Observed proportion (0 ≤ p ≤ 1)
        n: Sample size
        z: Z-score for desired confidence level (default 1.96 for 95%)

    Returns:
        (lower, upper) confidence interval bounds, or (None, None) if n=0
    """
    if n == 0:
        return None, None

    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n) / denom

    return max(0.0, center - margin), min(1.0, center + margin)
