from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.validation_dynamic import run_validation


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _label_fail(row: dict[str, Any]) -> int:
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def _evaluate_artifact_on_val(
    artifact_path: Path,
    splits_root: Path,
    score_source: str,
    cap_static: float,
    risk_static: float,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    task = str(artifact["task"])
    model = str(artifact["model"])
    seed = artifact.get("seed")

    val_path = splits_root / task / model / "val.jsonl"
    rows = _read_jsonl(val_path)
    if not rows:
        raise ValueError(f"Missing val split rows at {val_path}")

    ids: list[str] = []
    samples: list[dict[str, Any]] = []
    raw_scores: list[float] = []
    for i, row in enumerate(rows):
        sid = str(row.get("sample_id") or row.get("query_id") or f"{task}_{model}_{i}")
        ids.append(sid)
        if score_source == "score":
            sval = float(row.get("score", 0.5))
        else:
            bval = float(row.get("bin", 5.0))
            sval = bval / 9.0
        raw_scores.append(sval)
        samples.append(
            {
                "sample_id": sid,
                "slm_correct": bool(1 - _label_fail(row)),
                "llm_correct": bool(row.get("llm_correct", True)),
                "failure_category": row.get("failure_category"),
                "failure_type": row.get("failure_type"),
                "severity": row.get("severity"),
                "severity_score": row.get("severity_score"),
                "risk_weight": row.get("risk_weight"),
                "status": row.get("status"),
                "valid": row.get("valid"),
                "error": row.get("error"),
            }
        )

    # Normalize proxy scores to [0,1] to match validation interface.
    arr = np.array(raw_scores, dtype=float)
    lo = float(np.min(arr)) if arr.size else 0.0
    hi = float(np.max(arr)) if arr.size else 1.0
    if hi <= lo:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - lo) / (hi - lo)
    difficulty_scores = {ids[i]: float(norm[i]) for i in range(len(ids))}

    result = run_validation(
        val_samples=samples,
        scores=difficulty_scores,
        task=task,
        cap_static=cap_static,
        risk_static=risk_static,
    )

    cap_dyn = float(result.get("cap_dynamic", 0.0))
    risk_dyn = float(result.get("risk_dynamic", 1.0))
    selected_tau_score = result.get("selected_tau_score")
    selected_cap = float(result.get("selected_capability", 0.0))
    selected_risk = float(result.get("selected_risk", 1.0))
    pass_cap_gate = bool(selected_cap >= cap_dyn)
    pass_risk_gate = bool(selected_risk <= risk_dyn)
    pass_calibration_gate = bool(pass_cap_gate and pass_risk_gate)

    return {
        "task": task,
        "model": model,
        "seed": seed,
        "artifact_path": str(artifact_path),
        "selected_tau_score": selected_tau_score,
        "tau_source": result.get("tau_source"),
        "tau_candidates_count": result.get("tau_candidates_count"),
        "selected_capability": selected_cap,
        "selected_risk": selected_risk,
        "pass_cap_gate": pass_cap_gate,
        "pass_risk_gate": pass_risk_gate,
        "pass_calibration_gate": pass_calibration_gate,
        "cap_dynamic": cap_dyn,
        "risk_dynamic": risk_dyn,
        "feasible_tau_values": result.get("feasible_tau_values"),
        "feasible_tau_count": result.get("feasible_tau_count"),
        "feasible_tau_min": result.get("feasible_tau_min"),
        "feasible_tau_max": result.get("feasible_tau_max"),
        # Calibration diagnostics:
        "cap_curve": result.get("cap_curve"),
        "risk_curve": result.get("risk_curve"),
        "coverage_by_bin": result.get("coverage_by_bin"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run validation threshold calibration and export per-artifact calibration outcomes.")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--artifacts-root", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3")
    parser.add_argument("--output-path", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_threshold_calibration_report.json")
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--score-source", choices=["bin", "score"], default="bin")
    parser.add_argument("--cap-static", type=float, default=0.65)
    parser.add_argument("--risk-static", type=float, default=0.30)
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    artifacts_root = Path(args.artifacts_root).resolve()
    output_path = Path(args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    excludes = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]

    runs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    skip_names = {
        "training_report.json",
        "test_evaluation_report.json",
        "generalization_report.json",
        "ablation_report.json",
        "val_evaluation_report.json",
        "val_evaluation_report_continuous.json",
        "val_threshold_calibration_report.json",
    }
    for artifact_path in sorted([p for p in artifacts_root.rglob("*.json") if p.name not in skip_names and not p.name.startswith("s3_sddf_bridge")]):
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            model = str(payload.get("model", ""))
            if any(substr and substr in model for substr in excludes):
                continue
            runs.append(
                _evaluate_artifact_on_val(
                    artifact_path=artifact_path,
                    splits_root=splits_root,
                    score_source=str(args.score_source),
                    cap_static=float(args.cap_static),
                    risk_static=float(args.risk_static),
                )
            )
        except Exception as exc:
            errors.append({"artifact_path": str(artifact_path), "error": str(exc)})

    report = {
        "report_kind": "validation_threshold_calibration",
        "score_source": str(args.score_source),
        "cap_static": float(args.cap_static),
        "risk_static": float(args.risk_static),
        "runs": runs,
        "errors": errors,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote: {output_path}")
    print(f"Runs={len(runs)} Errors={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
