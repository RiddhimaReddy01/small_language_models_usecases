"""Utility to learn difficulty weights from binned capability/risk data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from framework.sddf.difficulty_weights import DifficultyWeightLearner


def load_curve(path: Path) -> dict[int, float]:
    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    return {int(row["bin_id"]): float(row["value"]) for row in rows}


def load_features(path: Path) -> dict[int, dict[str, float]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    return {
        int(row["difficulty_bin"]): {
            k: float(v) for k, v in row.items() if k.startswith("difficulty_feature_")
        }
        for row in rows
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Learn SDDF difficulty weights")
    parser.add_argument("--features", required=True, type=Path, help="JSON file with per-bin features")
    parser.add_argument("--cap_curve", required=True, type=Path, help="JSON file with capability per bin")
    parser.add_argument("--risk_curve", required=True, type=Path, help="JSON file with risk per bin")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("difficulty_weights.json"))
    args = parser.parse_args()

    bin_features = load_features(args.features)
    cap_curve = load_curve(args.cap_curve)
    risk_curve = load_curve(args.risk_curve)

    learner = DifficultyWeightLearner()
    weights = learner.learn(bin_features, cap_curve, risk_curve, threshold=args.threshold)

    args.output.write_text(json.dumps(weights, indent=2), encoding="utf-8")
    print(f"Wrote learned weights to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
