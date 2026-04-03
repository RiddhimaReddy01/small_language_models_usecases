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
    steps: int = 800
    l2: float = 1e-3
    entropy_reg: float = 1e-2
    sigmoid_scale: float = 8.0
    cv_folds: int = 3
    l2_grid: Sequence[float] = field(default_factory=lambda: (1e-4, 1e-3, 1e-2))
    entropy_grid: Sequence[float] = field(default_factory=lambda: (0.0, 1e-3, 1e-2))

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

    def _score_with_weights(self, features: Mapping[str, float], weights: Mapping[str, float]) -> float:
        return float(
            sum(
                float(weights.get(dim, 0.0)) * self._norm(dim, float(features.get(dim, 0.0)))
                for dim in self.dimensions
            )
        )

    @staticmethod
    def _logloss(prob: float, target: float, eps: float = 1e-9) -> float:
        p = max(eps, min(1.0 - eps, float(prob)))
        y = max(0.0, min(1.0, float(target)))
        return -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))

    def _optimize(
        self,
        samples: Sequence[Mapping[str, float]],
        targets: Sequence[float],
        l2: float,
        entropy_reg: float,
        init_weights: Mapping[str, float] | None = None,
    ) -> Dict[str, float]:
        dims = list(self.dimensions)
        if init_weights:
            weights = {dim: max(0.0, float(init_weights.get(dim, 0.0))) for dim in dims}
            tot = sum(weights.values())
            if tot <= 0.0:
                base = 1.0 / max(1, len(dims))
                weights = {dim: base for dim in dims}
            else:
                weights = {dim: v / tot for dim, v in weights.items()}
        else:
            base = 1.0 / max(1, len(dims))
            weights = {dim: base for dim in dims}

        n = float(max(1, len(samples)))
        eps = 1e-9
        for _ in range(max(1, int(self.steps))):
            grads = {dim: 0.0 for dim in dims}
            for sample, target in zip(samples, targets):
                score = self._score_with_weights(sample, weights)
                prob_failure = _sigmoid(self.sigmoid_scale * (score - 0.5))
                err = prob_failure - float(target)
                for dim in dims:
                    x = self._norm(dim, float(sample.get(dim, 0.0)))
                    grads[dim] += err * self.sigmoid_scale * x

            # Gradient step with L2 + entropy regularization on simplex.
            for dim in dims:
                w = max(eps, float(weights[dim]))
                grads[dim] = (grads[dim] / n) + float(l2) * w + float(entropy_reg) * (math.log(w) + 1.0)
                weights[dim] = w - self.learning_rate * grads[dim]
                if weights[dim] < 0.0:
                    weights[dim] = 0.0

            total = sum(weights.values())
            if total <= 0.0:
                base = 1.0 / max(1, len(dims))
                weights = {dim: base for dim in dims}
            else:
                weights = {dim: max(eps, val / total) for dim, val in weights.items()}

            # Renormalize after epsilon floor.
            total = sum(weights.values())
            weights = {dim: val / total for dim, val in weights.items()}

        return weights

    def _cv_select(self, samples: Sequence[Mapping[str, float]], targets: Sequence[float]) -> tuple[float, float]:
        n = len(samples)
        if n < 8:
            return float(self.l2), float(self.entropy_reg)
        folds = max(2, min(int(self.cv_folds), n))
        idxs = list(range(n))
        best_pair = (float(self.l2), float(self.entropy_reg))
        best_loss = float("inf")
        for l2 in self.l2_grid:
            for ent in self.entropy_grid:
                fold_losses: list[float] = []
                for f in range(folds):
                    val_idx = [i for i in idxs if i % folds == f]
                    tr_idx = [i for i in idxs if i % folds != f]
                    if not tr_idx or not val_idx:
                        continue
                    tr_samples = [samples[i] for i in tr_idx]
                    tr_targets = [targets[i] for i in tr_idx]
                    va_samples = [samples[i] for i in val_idx]
                    va_targets = [targets[i] for i in val_idx]
                    w = self._optimize(tr_samples, tr_targets, float(l2), float(ent))
                    losses = []
                    for sample, target in zip(va_samples, va_targets):
                        score = self._score_with_weights(sample, w)
                        prob = _sigmoid(self.sigmoid_scale * (score - 0.5))
                        losses.append(self._logloss(prob, target))
                    if losses:
                        fold_losses.append(sum(losses) / len(losses))
                if not fold_losses:
                    continue
                avg_loss = sum(fold_losses) / len(fold_losses)
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    best_pair = (float(l2), float(ent))
        return best_pair

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
        best_l2, best_ent = self._cv_select(samples, targets)
        self.l2 = float(best_l2)
        self.entropy_reg = float(best_ent)
        self.weights = self._optimize(samples, targets, self.l2, self.entropy_reg, init_weights=self.weights)

        return {
            "weights": dict(self.weights),
            "norm_stats": {dim: dict(stats) for dim, stats in self.norm_stats.items()},
            "fit_config": {
                "l2": float(self.l2),
                "entropy_reg": float(self.entropy_reg),
                "steps": int(self.steps),
                "learning_rate": float(self.learning_rate),
                "cv_folds": int(self.cv_folds),
            },
        }
