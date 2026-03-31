from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Sequence

from .difficulty import DIFFICULTY_FEATURES


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass
class DifficultyWeightLearner:
    """
    Learns non-negative, sum-to-1 feature weights for scalar difficulty.

    Training target should be semantic failure probability (1=failure, 0=success)
    from the training split. The learned weighted score is higher for harder inputs.
    """

    dimensions: Sequence[str] = field(default_factory=lambda: tuple(DIFFICULTY_FEATURES))
    learning_rate: float = 0.05
    steps: int = 600
    l2: float = 1e-3
    sigmoid_scale: float = 8.0

    def __post_init__(self) -> None:
        base = 1.0 / max(1, len(self.dimensions))
        self.weights: Dict[str, float] = {dim: base for dim in self.dimensions}
        self.norm_stats: Dict[str, dict[str, float]] = {
            dim: {"min": 0.0, "max": 1.0} for dim in self.dimensions
        }

    def _fit_norm(self, samples: Sequence[Mapping[str, float]]) -> None:
        for dim in self.dimensions:
            vals = [float(sample.get(dim, 0.0)) for sample in samples]
            if not vals:
                self.norm_stats[dim] = {"min": 0.0, "max": 1.0}
                continue
            lo = min(vals)
            hi = max(vals)
            if hi <= lo:
                hi = lo + 1.0
            self.norm_stats[dim] = {"min": float(lo), "max": float(hi)}

    def _norm(self, dim: str, value: float) -> float:
        bounds = self.norm_stats.get(dim, {"min": 0.0, "max": 1.0})
        lo = float(bounds["min"])
        hi = float(bounds["max"])
        if hi <= lo:
            return 0.0
        return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))

    def score(self, features: Mapping[str, float]) -> float:
        return float(
            sum(
                self.weights.get(dim, 0.0) * self._norm(dim, float(features.get(dim, 0.0)))
                for dim in self.dimensions
            )
        )

    def fit(self, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        samples: list[dict[str, float]] = []
        targets: list[float] = []
        for row in rows:
            sample = {dim: float(row.get(dim, 0.0) or 0.0) for dim in self.dimensions}
            target = float(row.get("target", 0.0) or 0.0)
            samples.append(sample)
            targets.append(max(0.0, min(1.0, target)))

        if not samples:
            return {"weights": dict(self.weights), "norm_stats": dict(self.norm_stats)}

        self._fit_norm(samples)
        n = float(len(samples))
        dims = list(self.dimensions)

        for _ in range(max(1, int(self.steps))):
            grads = {dim: 0.0 for dim in dims}
            for sample, target in zip(samples, targets):
                score = self.score(sample)
                prob_failure = _sigmoid(self.sigmoid_scale * (score - 0.5))
                err = prob_failure - target
                for dim in dims:
                    x = self._norm(dim, float(sample.get(dim, 0.0)))
                    grads[dim] += err * self.sigmoid_scale * x
            for dim in dims:
                self.weights[dim] -= self.learning_rate * ((grads[dim] / n) + self.l2 * self.weights[dim])
                if self.weights[dim] < 0.0:
                    self.weights[dim] = 0.0
            total = sum(self.weights.values())
            if total <= 0.0:
                base = 1.0 / max(1, len(dims))
                for dim in dims:
                    self.weights[dim] = base
            else:
                for dim in dims:
                    self.weights[dim] /= total

        return {
            "weights": dict(self.weights),
            "norm_stats": {dim: dict(stats) for dim, stats in self.norm_stats.items()},
        }
