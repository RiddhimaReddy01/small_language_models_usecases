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

    Training target = max(0, baseline_cap - slm_cap): binary 1 when the SLM
    fails and the baseline succeeds (route to baseline), 0 otherwise.
    The learned score is higher for queries where routing to baseline is beneficial.

    Key design choices:
    - Entropy regularization only (no L2): pushes weights toward uniform, preventing
      collapse to a single feature. L2 was removed — it conflicted with entropy reg.
    - Percentile normalization (5th–95th): robust to outliers vs. min-max.
    - Weighted loss: up-weights positive (routing-failure) examples to counter
      class imbalance (~34% positive rate).
    - Stratified CV: fold assignment by rank so each fold has the same target
      distribution.
    - Per-fold normalization: norm stats fitted inside each fold to avoid
      val-into-train normalization leakage.
    """

    dimensions: Sequence[str] = field(default_factory=lambda: tuple(DIFFICULTY_FEATURES))
    learning_rate: float = 0.05
    steps: int = 800
    l2: float = 0.0          # Disabled — conflicts with entropy reg.
    entropy_reg: float = 1e-2
    sigmoid_scale: float = 8.0
    cv_folds: int = 3
    l2_grid: Sequence[float] = field(default_factory=lambda: (0.0,))
    entropy_grid: Sequence[float] = field(default_factory=lambda: (1e-3, 1e-2, 0.1, 0.3))
    min_feature_corr: float = 0.03   # Minimum |Pearson r| with target to retain a feature.
                                      # Features below this threshold are zeroed before
                                      # optimization — they carry no routing signal and only
                                      # dilute gradient, causing the optimizer to collapse
                                      # onto the single strongest feature.

    def __post_init__(self) -> None:
        base = 1.0 / max(1, len(self.dimensions))
        self.weights: Dict[str, float] = {dim: base for dim in self.dimensions}
        self.norm_stats: Dict[str, dict[str, float]] = {
            dim: {"p05": 0.0, "p95": 1.0} for dim in self.dimensions
        }

    # ------------------------------------------------------------------
    # Normalization — percentile-based (robust to outliers)
    # ------------------------------------------------------------------

    def _fit_norm_on(self, samples: Sequence[Mapping[str, float]]) -> Dict[str, dict[str, float]]:
        """Return per-feature 5th/95th percentile bounds fitted on `samples`."""
        stats: Dict[str, dict[str, float]] = {}
        for dim in self.dimensions:
            vals = sorted(float(s.get(dim, 0.0)) for s in samples)
            n = len(vals)
            if n == 0:
                stats[dim] = {"p05": 0.0, "p95": 1.0}
                continue
            p05 = vals[max(0, int(0.05 * n))]
            p95 = vals[min(n - 1, int(0.95 * n))]
            if p95 <= p05:
                p95 = p05 + 1.0
            stats[dim] = {"p05": float(p05), "p95": float(p95)}
        return stats

    def _norm_with(self, dim: str, value: float, stats: Mapping[str, dict[str, float]]) -> float:
        bounds = stats.get(dim, {"p05": 0.0, "p95": 1.0})
        lo = float(bounds["p05"])
        hi = float(bounds["p95"])
        if hi <= lo:
            return 0.0
        return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))

    def _norm(self, dim: str, value: float) -> float:
        return self._norm_with(dim, value, self.norm_stats)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score(self, features: Mapping[str, float]) -> float:
        return float(
            sum(
                self.weights.get(dim, 0.0) * self._norm(dim, float(features.get(dim, 0.0)))
                for dim in self.dimensions
            )
        )

    def _score_with(
        self,
        features: Mapping[str, float],
        weights: Mapping[str, float],
        stats: Mapping[str, dict[str, float]],
    ) -> float:
        return float(
            sum(
                float(weights.get(dim, 0.0)) * self._norm_with(dim, float(features.get(dim, 0.0)), stats)
                for dim in self.dimensions
            )
        )

    # ------------------------------------------------------------------
    # Loss
    # ------------------------------------------------------------------

    @staticmethod
    def _logloss(prob: float, target: float, weight: float = 1.0, eps: float = 1e-9) -> float:
        p = max(eps, min(1.0 - eps, float(prob)))
        y = max(0.0, min(1.0, float(target)))
        return float(weight) * -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))

    # ------------------------------------------------------------------
    # Optimizer
    # ------------------------------------------------------------------

    def _optimize(
        self,
        samples: Sequence[Mapping[str, float]],
        targets: Sequence[float],
        norm_stats: Mapping[str, dict[str, float]],
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

        # Class-imbalance weight: up-weight positive (routing-failure) examples.
        n_pos = sum(1 for t in targets if float(t) > 0.5)
        n_neg = len(targets) - n_pos
        n_total = float(max(1, len(targets)))
        pos_w = (n_total / (2.0 * max(1, n_pos))) if n_pos > 0 else 1.0
        neg_w = (n_total / (2.0 * max(1, n_neg))) if n_neg > 0 else 1.0
        sample_weights = [pos_w if float(t) > 0.5 else neg_w for t in targets]

        eps = 1e-9
        for _ in range(max(1, int(self.steps))):
            grads = {dim: 0.0 for dim in dims}
            for sample, target, sw in zip(samples, targets, sample_weights):
                score = self._score_with(sample, weights, norm_stats)
                prob_failure = _sigmoid(self.sigmoid_scale * (score - 0.5))
                err = (prob_failure - float(target)) * sw
                for dim in dims:
                    x = self._norm_with(dim, float(sample.get(dim, 0.0)), norm_stats)
                    grads[dim] += err * self.sigmoid_scale * x

            # Entropy regularization on simplex — pushes toward uniform.
            # Gradient of -sum(w*log(w)) w.r.t. w_j = -(log(w_j) + 1).
            # Subtract from loss gradient so higher entropy (uniform) is preferred.
            for dim in dims:
                w = max(eps, float(weights[dim]))
                grads[dim] = (grads[dim] / n_total) - float(entropy_reg) * (math.log(w) + 1.0)
                weights[dim] = w - self.learning_rate * grads[dim]
                if weights[dim] < 0.0:
                    weights[dim] = 0.0

            total = sum(weights.values())
            if total <= 0.0:
                base = 1.0 / max(1, len(dims))
                weights = {dim: base for dim in dims}
            else:
                weights = {dim: max(eps, val / total) for dim, val in weights.items()}

            total = sum(weights.values())
            weights = {dim: val / total for dim, val in weights.items()}

        return weights

    # ------------------------------------------------------------------
    # Cross-validation — stratified folds, per-fold normalization
    # ------------------------------------------------------------------

    def _cv_select(self, samples: Sequence[Mapping[str, float]], targets: Sequence[float]) -> tuple[float, float]:
        n = len(samples)
        if n < 8:
            return float(self.l2), float(self.entropy_reg)
        folds = max(2, min(int(self.cv_folds), n))

        # Stratified fold assignment by rank: sort by target, assign fold = rank % folds.
        # This guarantees each fold has the same target distribution.
        sorted_by_target = sorted(range(n), key=lambda i: float(targets[i]))
        fold_of: list[int] = [0] * n
        for rank, orig_idx in enumerate(sorted_by_target):
            fold_of[orig_idx] = rank % folds

        best_pair = (float(self.l2), float(self.entropy_reg))
        best_loss = float("inf")
        for ent in self.entropy_grid:
            fold_losses: list[float] = []
            for f in range(folds):
                tr_idx = [i for i in range(n) if fold_of[i] != f]
                va_idx = [i for i in range(n) if fold_of[i] == f]
                if not tr_idx or not va_idx:
                    continue
                tr_samples = [samples[i] for i in tr_idx]
                tr_targets = [targets[i] for i in tr_idx]
                va_samples = [samples[i] for i in va_idx]
                va_targets = [targets[i] for i in va_idx]

                # Fit normalization on train fold only — prevents val leaking into norms.
                fold_norm = self._fit_norm_on(tr_samples)

                w = self._optimize(tr_samples, tr_targets, fold_norm, float(ent))
                losses = []
                for sample, target in zip(va_samples, va_targets):
                    score = self._score_with(sample, w, fold_norm)
                    prob = _sigmoid(self.sigmoid_scale * (score - 0.5))
                    losses.append(self._logloss(prob, target))
                if losses:
                    fold_losses.append(sum(losses) / len(losses))
            if not fold_losses:
                continue
            avg_loss = sum(fold_losses) / len(fold_losses)
            if avg_loss < best_loss:
                best_loss = avg_loss
                best_pair = (0.0, float(ent))
        return best_pair

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Feature pre-filtering — correlation-based
    # ------------------------------------------------------------------

    def _select_features(
        self,
        samples: list[dict[str, float]],
        targets: list[float],
    ) -> tuple[list[str], dict[str, float]]:
        """Return (active_dims, {dim: pearson_r}).

        Active dims are those with |Pearson r| >= self.min_feature_corr with the
        routing target.  If fewer than 2 features pass the threshold the top-2 by
        |r| are kept regardless, so the optimizer always has at least 2 dimensions
        to distribute weight across.

        Why pre-filter rather than just tune entropy_reg?
        - The entropy regularizer pushes weights toward uniform over *all* dims.
          If 7 of 9 features have r≈0 they add noise to the gradient, forcing the
          optimizer to either ignore them (collapse) or spread weight uselessly.
        - Removing uncorrelated features before training lets entropy_reg do its
          job: spread weight uniformly over the *informative* subset.
        """
        n = len(samples)
        if n == 0:
            return list(self.dimensions), {}

        y_vals = [float(t) for t in targets]
        y_mean = sum(y_vals) / n
        y_std  = math.sqrt(sum((v - y_mean) ** 2 for v in y_vals) / max(1, n))

        corrs: dict[str, float] = {}
        for dim in self.dimensions:
            x_vals = [float(s.get(dim, 0.0)) for s in samples]
            x_mean = sum(x_vals) / n
            x_std  = math.sqrt(sum((v - x_mean) ** 2 for v in x_vals) / max(1, n))
            if x_std < 1e-9 or y_std < 1e-9:
                corrs[dim] = 0.0
                continue
            cov = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n)) / n
            corrs[dim] = cov / (x_std * y_std)

        thresh = max(0.0, float(self.min_feature_corr))
        active = [dim for dim in self.dimensions if abs(corrs[dim]) >= thresh]

        # Always retain at least 2 features (top-2 by |r|).
        if len(active) < 2:
            active = sorted(self.dimensions, key=lambda d: -abs(corrs[d]))[:2]

        return active, corrs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        # ── Step 1: correlation-based feature pre-selection ──────────────────
        # Remove features with |r| < min_feature_corr before optimization.
        # Zeroed features stay at uniform weight among themselves so the full
        # simplex constraint is preserved downstream (scores still sum to 1).
        active_dims, feature_corrs = self._select_features(samples, targets)
        inactive_dims = [d for d in self.dimensions if d not in active_dims]

        # ── Step 2: adaptive entropy_reg — scale with signal sparsity ────────
        # When positive rate is low (< 10%) the gradient is dominated by the
        # majority class and collapses onto the single most predictive feature
        # even under mild entropy_reg.  Scale entropy_reg up for sparse tasks:
        #   pos_rate ≥ 0.20 → use CV-selected reg from entropy_grid
        #   pos_rate < 0.10 → force minimum 0.10 entropy_reg
        n_pos = sum(1 for t in targets if float(t) > 0.5)
        pos_rate = n_pos / max(1, len(targets))
        sparse_floor = 0.0
        if pos_rate < 0.10:
            sparse_floor = 0.10   # very sparse: enforce strong uniformity
        elif pos_rate < 0.20:
            sparse_floor = 0.03   # moderately sparse: mild boost

        # ── Step 3: fit norm, run CV, optimize on active dims only ───────────
        # Build a sub-learner restricted to active_dims so entropy_reg acts
        # only on the informative feature subspace.
        sub = DifficultyWeightLearner(
            dimensions=active_dims,
            learning_rate=self.learning_rate,
            steps=self.steps,
            l2=0.0,
            entropy_reg=max(sparse_floor, float(self.entropy_reg)),
            sigmoid_scale=self.sigmoid_scale,
            cv_folds=self.cv_folds,
            l2_grid=(0.0,),
            entropy_grid=tuple(
                e for e in self.entropy_grid if float(e) >= sparse_floor
            ) or (max(sparse_floor, 1e-3),),
            min_feature_corr=0.0,  # pre-filtering already done above
        )
        n = len(samples)
        norm_n = max(1, int(n * 0.8))
        sub.norm_stats = sub._fit_norm_on(samples[:norm_n])
        _best_l2, best_ent = sub._cv_select(samples, targets)
        best_ent = max(sparse_floor, float(best_ent))
        sub.entropy_reg = best_ent
        active_weights = sub._optimize(samples, targets, sub.norm_stats, best_ent)

        # ── Step 4: compose full weight vector ───────────────────────────────
        # Active dims carry the learned weights (sum ≈ 1 among themselves).
        # Inactive dims each get a tiny floor weight (eps) so a query can
        # still receive a non-zero score from any feature, but they contribute
        # negligibly.  Re-normalise the full vector to sum to 1.
        eps = 1e-9
        full_weights: dict[str, float] = {}
        for dim in self.dimensions:
            if dim in active_weights:
                full_weights[dim] = float(active_weights[dim])
            else:
                full_weights[dim] = eps
        total = sum(full_weights.values())
        full_weights = {d: v / total for d, v in full_weights.items()}

        # Update self so score() works correctly after fit().
        self.norm_stats = sub.norm_stats
        self.entropy_reg = best_ent
        self.weights = full_weights

        return {
            "weights": full_weights,
            "norm_stats": {dim: dict(stats) for dim, stats in sub.norm_stats.items()},
            "fit_config": {
                "l2": 0.0,
                "entropy_reg": best_ent,
                "steps": int(self.steps),
                "learning_rate": float(self.learning_rate),
                "cv_folds": int(self.cv_folds),
                "active_dims": active_dims,
                "inactive_dims": inactive_dims,
                "feature_corrs": {d: round(float(v), 4) for d, v in feature_corrs.items()},
                "pos_rate": round(pos_rate, 4),
                "sparse_floor_entropy": sparse_floor,
            },
        }
