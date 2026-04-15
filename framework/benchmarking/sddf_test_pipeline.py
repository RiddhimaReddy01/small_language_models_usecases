from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sddf_train_pipeline import FeatureExtractorV2, _read_jsonl, _split_metrics


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


def _evaluate_artifact(
    artifact_path: Path,
    splits_root: Path,
    extractor: FeatureExtractorV2,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    task = str(artifact["task"])
    model = str(artifact["model"])
    features = [str(f) for f in artifact["features"]]
    tau = float(artifact["tau"])
    mean = np.array(artifact["scaler_mean"], dtype=float)
    scale = np.array(artifact["scaler_scale"], dtype=float)
    weights = np.array(artifact["weights"], dtype=float)
    bias = float(artifact["bias"])
    seed = artifact.get("seed")

    test_path = splits_root / task / model / "test.jsonl"
    rows = _read_jsonl(test_path)
    if not rows:
        raise ValueError(f"Missing test split rows at {test_path}")

    feature_rows: list[dict[str, float]] = []
    y: list[int] = []
    for row in rows:
        prompt = str(row.get("prompt", ""))
        feat = extractor.extract(task=task, prompt=prompt)
        feature_rows.append({k: float(feat.get(k, 0.0)) for k in features})
        y.append(_label_fail(row))

    x = pd.DataFrame(feature_rows)[features].to_numpy(dtype=float)
    denom = np.where(scale == 0.0, 1.0, scale)
    x_s = (x - mean) / denom
    z = x_s @ weights + bias
    p = _sigmoid(z)
    y_arr = np.array(y, dtype=int)
    metrics = _split_metrics(y_true=y_arr, p=p, threshold=tau)

    return {
        "task": task,
        "model": model,
        "seed": seed,
        "tau": tau,
        "artifact_path": str(artifact_path),
        "test_metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate frozen SDDF v3 artifacts on test split only (no refit).")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--artifacts-root", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3")
    parser.add_argument("--output-path", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/test_evaluation_report.json")
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--embedding-model", default="model_runs/local_models/all-MiniLM-L6-v2")
    parser.add_argument("--disable-embeddings", action="store_true")
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    artifacts_root = Path(args.artifacts_root).resolve()
    output_path = Path(args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exclude_model_substrings = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]
    extractor = FeatureExtractorV2(embedding_model=args.embedding_model, disable_embeddings=bool(args.disable_embeddings))

    runs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skip_names = {"training_report.json", "test_evaluation_report.json", "generalization_report.json", "ablation_report.json"}
    for artifact_path in sorted([p for p in artifacts_root.rglob("*.json") if p.name not in skip_names]):
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            model = str(payload.get("model", ""))
            if any(substr and substr in model for substr in exclude_model_substrings):
                continue
            result = _evaluate_artifact(artifact_path=artifact_path, splits_root=splits_root, extractor=extractor)
            runs.append(result)
        except Exception as exc:
            errors.append({"artifact_path": str(artifact_path), "error": str(exc)})

    report = {"runs": runs, "errors": errors}
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote: {output_path}")
    print(f"Runs={len(runs)} Errors={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
