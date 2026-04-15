from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.s3_framework import decide_s3_and_route


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_seed_artifacts(artifacts_root: Path, seed: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    suffix = f"__seed{seed}.json"
    for p in sorted(artifacts_root.rglob(f"*{suffix}")):
        if p.name in {"training_report.json", "test_evaluation_report.json", "generalization_report.json", "ablation_report.json"}:
            continue
        try:
            d = _load_json(p)
        except Exception:
            continue
        if "task" in d and "model" in d and "tau" in d:
            out.append(d)
    return out


def _default_scores_for_task(task_scores: dict[str, Any], task: str) -> dict[str, int]:
    if task in task_scores:
        return {k: int(v) for k, v in task_scores[task].items()}
    if "*" in task_scores:
        return {k: int(v) for k, v in task_scores["*"].items()}
    raise ValueError(f"Missing S3 scores for task '{task}' and no '*' default provided")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge S3 top-down tiering with SDDF tau limits.")
    parser.add_argument(
        "--s3-config",
        default="framework/benchmarking/s3_task_config.json",
        help="JSON with global weights and task score profiles.",
    )
    parser.add_argument(
        "--artifacts-root",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3",
        help="SDDF training artifacts root.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed artifacts to use.")
    parser.add_argument(
        "--tau-overrides",
        default="",
        help="Optional JSON mapping task->model->{tau_cap,tau_risk}. If absent, artifact tau is used for both.",
    )
    parser.add_argument(
        "--val-report-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_evaluation_report.json",
        help="Validation report from sddf_val_pipeline.py containing true tau_cap/tau_risk per task/model/seed.",
    )
    parser.add_argument(
        "--output-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/s3_sddf_bridge_seed42.json",
    )
    parser.add_argument("--tau1", type=float, default=3.2)
    parser.add_argument("--tau2", type=float, default=4.0)
    args = parser.parse_args()

    s3_cfg = _load_json(Path(args.s3_config).resolve())
    weights = {k: int(v) for k, v in s3_cfg["weights"].items()}
    task_scores = dict(s3_cfg["task_scores"])

    overrides: dict[str, Any] = {}
    if str(args.tau_overrides).strip():
        overrides = _load_json(Path(args.tau_overrides).resolve())

    val_report_map: dict[tuple[str, str, int], dict[str, Any]] = {}
    val_report_path = Path(args.val_report_path).resolve()
    if val_report_path.exists():
        vr = _load_json(val_report_path)
        for r in vr.get("runs", []):
            key = (str(r.get("task", "")), str(r.get("model", "")), int(r.get("seed", -1)))
            val_report_map[key] = r

    artifacts = _load_seed_artifacts(Path(args.artifacts_root).resolve(), seed=int(args.seed))
    results: list[dict[str, Any]] = []

    for art in artifacts:
        task = str(art["task"])
        model = str(art["model"])
        tau = float(art["tau"])
        scores = _default_scores_for_task(task_scores, task=task)

        ov = overrides.get(task, {}).get(model, {})
        vr = val_report_map.get((task, model, int(args.seed)), {})

        tau_cap_src = vr.get("tau_cap", None)
        tau_risk_src = vr.get("tau_risk", None)
        tau_cap = float(tau_cap_src) if tau_cap_src is not None else float(ov.get("tau_cap", tau))
        tau_risk = float(tau_risk_src) if tau_risk_src is not None else float(ov.get("tau_risk", tau))

        decision = decide_s3_and_route(
            scores=scores,  # type: ignore[arg-type]
            weights=weights,  # type: ignore[arg-type]
            tau_risk=tau_risk,
            tau_cap=tau_cap,
            tau1=float(args.tau1),
            tau2=float(args.tau2),
        )
        results.append(
            {
                "task": task,
                "model": model,
                "seed": int(args.seed),
                "s3_scores": scores,
                "s3_weights": weights,
                "tau_cap": tau_cap,
                "tau_risk": tau_risk,
                "artifact_tau": tau,
                "decision": decision,
            }
        )

    out = {
        "seed": int(args.seed),
        "tau_thresholds": {"tau1": float(args.tau1), "tau2": float(args.tau2)},
        "n_results": len(results),
        "results": results,
    }
    out_path = Path(args.output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Results={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
