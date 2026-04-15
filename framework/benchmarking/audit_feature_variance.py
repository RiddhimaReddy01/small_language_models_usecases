from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from sddf_train_pipeline import FeatureExtractorV2, _read_jsonl


def _build_feature_frame(
    rows: list[dict[str, Any]],
    task: str,
    feature_names: list[str],
    extractor: FeatureExtractorV2,
) -> pd.DataFrame:
    items: list[dict[str, float]] = []
    for row in rows:
        prompt = str(row.get("prompt", ""))
        feat = extractor.extract(task=task, prompt=prompt)
        items.append({k: float(feat.get(k, 0.0)) for k in feature_names})
    return pd.DataFrame(items)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit per-feature variance for SDDF splits.")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--feature-schema-path", default="framework/benchmarking/sddf_feature_schema_v2.json")
    parser.add_argument("--split", default="train", choices=["train", "val", "test"])
    parser.add_argument("--output-csv", default="model_runs/sddf_training_splits_slm_only/feature_variance_audit_v2.csv")
    parser.add_argument("--output-json", default="model_runs/sddf_training_splits_slm_only/feature_variance_audit_v2.json")
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--embedding-model", default="model_runs/local_models/all-MiniLM-L6-v2")
    parser.add_argument("--disable-embeddings", action="store_true")
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    schema_path = Path(args.feature_schema_path).resolve()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    extractor = FeatureExtractorV2(
        embedding_model=args.embedding_model,
        disable_embeddings=bool(args.disable_embeddings),
    )
    exclude_model_substrings = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]

    rows_out: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"split": args.split, "tasks": {}}

    for task_dir in sorted([p for p in splits_root.iterdir() if p.is_dir() and (p / "split_query_ids.json").exists()]):
        task = task_dir.name
        if task not in schema:
            continue
        feature_names = [str(f) for f in schema[task]]
        summary["tasks"][task] = {}

        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            model = model_dir.name
            if any(substr and substr in model for substr in exclude_model_substrings):
                continue
            data_path = model_dir / f"{args.split}.jsonl"
            data_rows = _read_jsonl(data_path)
            if not data_rows:
                continue
            df = _build_feature_frame(data_rows, task=task, feature_names=feature_names, extractor=extractor)
            if df.empty:
                continue

            constant_features: list[str] = []
            for feat in feature_names:
                series = df[feat]
                variance = float(series.var(ddof=0))
                min_v = float(series.min())
                max_v = float(series.max())
                nunique = int(series.nunique(dropna=True))
                is_constant = bool(max_v - min_v <= 1e-12)
                if is_constant:
                    constant_features.append(feat)
                rows_out.append(
                    {
                        "task": task,
                        "model": model,
                        "split": args.split,
                        "feature": feat,
                        "variance": variance,
                        "min": min_v,
                        "max": max_v,
                        "nunique": nunique,
                        "is_constant": is_constant,
                        "n_rows": int(len(df)),
                    }
                )
            summary["tasks"][task][model] = {
                "n_rows": int(len(df)),
                "constant_features": constant_features,
            }

    out_csv = Path(args.output_csv).resolve()
    out_json = Path(args.output_json).resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows_out).to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote CSV: {out_csv}")
    print(f"Wrote JSON: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
