from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Mapping, Sequence

from .difficulty import DIFFICULTY_FEATURES


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class DifficultyWeightLearner:
    """
    Learns weights for each difficulty feature using a gradient-ascent utility so that
    high-weight scores correlate with capability successes and low risk.
    """

    dimensions: Sequence[str] = field(default_factory=lambda: tuple(DIFFICULTY_FEATURES))
    learning_rate: float = 0.01
    alpha: float = 10.0
    lambda_risk: float = 1.0
    llm_cap: float = 0.95
    llm_risk: float = 0.05
    steps: int = 200

    def __post_init__(self) -> None:
        self.weights: Dict[str, float] = {dim: 1.0 for dim in self.dimensions}

    def score(self, features: Mapping[str, float]) -> float:
        return sum(self.weights.get(dim, 0.0) * features.get(dim, 0.0) for dim in self.dimensions)

    def learn(
        self,
        bin_features: Mapping[int, Mapping[str, float]],
        cap_curve: Mapping[int, float],
        risk_curve: Mapping[int, float],
        threshold: float = 0.5,
    ) -> Dict[str, float]:
        for _ in range(self.steps):
            gradients = {dim: 0.0 for dim in self.dimensions}
            for bin_id, features in bin_features.items():
                cap = cap_curve.get(bin_id, 0.0)
                risk = risk_curve.get(bin_id, 0.0)
                score = self.score(features)
                accept = _sigmoid(self.alpha * (score - threshold))
                u_accept = cap - self.lambda_risk * risk
                u_reject = self.llm_cap - self.lambda_risk * self.llm_risk
                delta = (u_accept - u_reject) * accept * (1 - accept) * self.alpha
                for dim in self.dimensions:
                    gradients[dim] += delta * features.get(dim, 0.0)

            for dim in self.dimensions:
                self.weights[dim] += self.learning_rate * gradients[dim]

        return dict(self.weights)
