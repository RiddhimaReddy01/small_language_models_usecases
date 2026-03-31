from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = ROOT / "model_runs" / "benchmark_75"
MODEL_RUNS_ROOT = LEGACY_ROOT if LEGACY_ROOT.exists() else ROOT / "model_runs"
EXCLUDED = {"business_analytics", "benchmarking", "difficulty_weights"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def summarize_task(task_dir: Path) -> dict:
    thresholds_path = task_dir / "sddf" / "thresholds.json"
    routing_path = task_dir / "sddf" / "routing_policy.json"
    summary = {
        "task": task_dir.name,
        "thresholds_path": str(thresholds_path) if thresholds_path.exists() else None,
        "routing_policy_path": str(routing_path) if routing_path.exists() else None,
        "models": [],
    }
    if not thresholds_path.exists():
        summary["error"] = "missing thresholds.json"
        return summary

    payload = _load_json(thresholds_path)
    decision = payload.get("decision_matrix", {})
    for model_key, item in sorted(decision.items()):
        summary["models"].append(
            {
                "model_key": model_key,
                "display_name": item.get("display_name", model_key),
                "avg_expected_capability": item.get("avg_expected_capability"),
                "avg_expected_risk": item.get("avg_expected_risk"),
                "tau_quadrant": item.get("tau_quadrant", item.get("confidence_quadrant")),
            }
        )
    return summary


def main() -> int:
    task_dirs = [
        d
        for d in sorted(MODEL_RUNS_ROOT.iterdir())
        if d.is_dir() and d.name not in EXCLUDED
    ]
    report = [summarize_task(task_dir) for task_dir in task_dirs]
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
