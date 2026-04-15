from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decision_lane(disqualified: bool, tier: str) -> str:
    if disqualified:
        return "Stop: disqualified"
    if tier == "pure_slm":
        return "SLM primary"
    if tier == "hybrid":
        return "Hybrid escalation"
    if tier == "llm_only":
        return "LLM only"
    return "Review required"


def _row_from_result(result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision", {})
    disqualified = bool(decision.get("disqualified", False))
    formula_tier = str(decision.get("formula_tier", decision.get("tier", "unknown")))
    final_tier = str(decision.get("final_tier", decision.get("tier", "unknown")))
    gate_min_tier = str(decision.get("gate_min_tier", "none"))
    tier = final_tier
    gate_reason = str(decision.get("gate_reason", ""))
    s3_score = float(decision.get("s3_score", 0.0))
    tau_route = float(decision.get("tau_route", -1.0))
    tau_cap = float(result.get("tau_cap", 0.0))
    tau_risk = float(result.get("tau_risk", 0.0))
    artifact_tau = float(result.get("artifact_tau", 0.0))

    return {
        "task": str(result.get("task", "")),
        "model": str(result.get("model", "")),
        "seed": int(result.get("seed", -1)),
        "formula_tier": formula_tier,
        "final_tier": final_tier,
        "tier": tier,
        "gate_min_tier": gate_min_tier,
        "lane": _decision_lane(disqualified=disqualified, tier=tier),
        "disqualified": disqualified,
        "gate_reason": gate_reason,
        "s3_score": round(s3_score, 4),
        "tau_cap": tau_cap,
        "tau_risk": tau_risk,
        "tau_route": tau_route,
        "artifact_tau": artifact_tau,
    }


def _build_summary(rows: list[dict[str, Any]], source: dict[str, Any]) -> dict[str, Any]:
    tier_counts = Counter(row["final_tier"] for row in rows)
    formula_tier_counts = Counter(row["formula_tier"] for row in rows)
    lane_counts = Counter(row["lane"] for row in rows)
    disqualified_count = sum(1 for row in rows if row["disqualified"])
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)

    task_summaries: dict[str, Any] = {}
    for task, task_rows in sorted(by_task.items()):
        task_rows_sorted = sorted(task_rows, key=lambda r: (r["disqualified"], r["tier"], -float(r["tau_route"])))
        task_summaries[task] = {
            "n_models": len(task_rows_sorted),
            "formula_tiers": dict(Counter(r["formula_tier"] for r in task_rows_sorted)),
            "tiers": dict(Counter(r["tier"] for r in task_rows_sorted)),
            "recommended_first_review": {
                "model": task_rows_sorted[0]["model"],
                "lane": task_rows_sorted[0]["lane"],
                "formula_tier": task_rows_sorted[0]["formula_tier"],
                "tier": task_rows_sorted[0]["tier"],
                "tau_route": task_rows_sorted[0]["tau_route"],
                "s3_score": task_rows_sorted[0]["s3_score"],
            },
        }

    return {
        "seed": int(source.get("seed", -1)),
        "tau_thresholds": source.get("tau_thresholds", {}),
        "n_rows": len(rows),
        "disqualified_count": disqualified_count,
        "formula_tier_counts": dict(formula_tier_counts),
        "tier_counts": dict(tier_counts),
        "lane_counts": dict(lane_counts),
        "tasks": task_summaries,
        "manager_note": (
            "S3 is governance-facing (tier and gate); SDDF provides runtime tau controls. "
            "Use lane/tier for policy communication, and tau_route for engineering enforcement."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export manager-friendly S3+SDDF dashboard files.")
    parser.add_argument(
        "--bridge-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/s3_sddf_bridge_seed42.json",
        help="Input bridge JSON from framework/benchmarking/s3_sddf_bridge.py",
    )
    parser.add_argument(
        "--output-dir",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/manager_dashboard",
        help="Output directory for CSV/JSON exports.",
    )
    args = parser.parse_args()

    bridge_path = Path(args.bridge_path).resolve()
    payload = _load_json(bridge_path)
    results = payload.get("results", [])
    rows = [_row_from_result(result) for result in results]
    summary = _build_summary(rows=rows, source=payload)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "s3_sddf_manager_dashboard.csv"
    json_path = output_dir / "s3_sddf_manager_summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "task",
                "model",
                "seed",
                "formula_tier",
                "final_tier",
                "tier",
                "gate_min_tier",
                "lane",
                "disqualified",
                "gate_reason",
                "s3_score",
                "tau_cap",
                "tau_risk",
                "tau_route",
                "artifact_tau",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {json_path}")
    print(f"Rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
