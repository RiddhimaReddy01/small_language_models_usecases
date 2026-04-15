from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

import sddf_train_pipeline as sddf


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _predict_probs(x: np.ndarray, scaler_mean: np.ndarray, scaler_scale: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    denom = np.where(np.abs(scaler_scale) <= 1e-12, 1.0, scaler_scale)
    x_s = (x - scaler_mean) / denom
    logits = np.matmul(x_s, weights) + bias
    return _sigmoid(logits)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SDDF cross-model generalization per task family.")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--artifacts-dir", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3")
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--disable-embeddings", action="store_true")
    parser.add_argument("--output-path", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/generalization_report.json")
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    out_path = Path(args.output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    excludes = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]

    extractor = sddf.FeatureExtractorV2(embedding_model=args.embedding_model, disable_embeddings=bool(args.disable_embeddings))
    report: dict[str, Any] = {"runs": [], "errors": []}

    for task_dir in sorted([p for p in splits_root.iterdir() if p.is_dir() and (p / "split_query_ids.json").exists()]):
        task = task_dir.name
        task_art_dir = artifacts_dir / task
        if not task_art_dir.exists():
            continue
        source_artifacts = sorted(task_art_dir.glob("*__seed*.json"))
        target_model_dirs = sorted([p for p in task_dir.iterdir() if p.is_dir() and not any(x in p.name for x in excludes)])
        if not source_artifacts or not target_model_dirs:
            continue

        for art_path in source_artifacts:
            try:
                art = json.loads(art_path.read_text(encoding="utf-8"))
                source_model = str(art.get("model", ""))
                source_seed = int(art.get("seed", -1))
                features = [str(f) for f in art.get("features", [])]
                if not features:
                    raise ValueError("Artifact has no features")

                scaler_mean = np.asarray(art["scaler_mean"], dtype=float)
                scaler_scale = np.asarray(art["scaler_scale"], dtype=float)
                weights = np.asarray(art["weights"], dtype=float)
                bias = float(art["bias"])
                tau = float(art["tau"])
            except Exception as exc:
                report["errors"].append({"task": task, "artifact": str(art_path), "error": str(exc)})
                continue

            for target_model_dir in target_model_dirs:
                target_model = target_model_dir.name
                if target_model == source_model:
                    continue
                try:
                    test_rows = sddf._read_jsonl(target_model_dir / "test.jsonl")
                    if not test_rows:
                        raise ValueError("Missing target test split")
                    df_test = sddf._build_frame(task, test_rows, features, extractor)
                    x_test = df_test[features].to_numpy(dtype=float)
                    y_test = df_test["y"].astype(int).to_numpy()
                    p_test = _predict_probs(x=x_test, scaler_mean=scaler_mean, scaler_scale=scaler_scale, weights=weights, bias=bias)
                    metrics = sddf._split_metrics(y_true=y_test, p=p_test, threshold=tau)
                    report["runs"].append(
                        {
                            "task": task,
                            "source_model": source_model,
                            "source_seed": source_seed,
                            "target_model": target_model,
                            "n_test": int(len(y_test)),
                            "metrics": metrics,
                        }
                    )
                except Exception as exc:
                    report["errors"].append(
                        {
                            "task": task,
                            "source_model": source_model,
                            "source_seed": source_seed,
                            "target_model": target_model,
                            "error": str(exc),
                        }
                    )

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Runs={len(report['runs'])} Errors={len(report['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
