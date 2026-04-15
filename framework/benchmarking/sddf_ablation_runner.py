from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ABLATIONS = {
    "all_features": lambda base, task: list(base[task]),
    "no_embedding": lambda base, task: [f for f in base[task] if f != "embedding_query_context_cosine"],
    "lexical_surface": lambda base, task: [f for f in base[task] if ("token" in f or "ratio" in f or "density" in f or "reading" in f or "grade" in f or "fog" in f or "smog" in f)],
    "retrieval_context": lambda base, task: [f for f in base[task] if ("context" in f or "query" in f or "bm25" in f or "compression" in f or "embedding" in f)],
    "syntax_entities": lambda base, task: [f for f in base[task] if ("noun" in f or "verb" in f or "adj" in f or "dep_tree" in f or "entity" in f or "imperative" in f)],
}


def _load_schema(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for task, features in data.items():
        out[str(task)] = [str(f) for f in features]
    return out


def _build_ablation_schema(base_schema: dict[str, list[str]], ablation: str) -> dict[str, list[str]]:
    selector = ABLATIONS[ablation]
    schema: dict[str, list[str]] = {}
    for task in base_schema:
        feat = selector(base_schema, task)
        if not feat:
            feat = list(base_schema[task])
        schema[task] = feat
    return schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SDDF v3 ablations by generating task-wise feature schemas.")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--base-feature-schema-path", default="framework/benchmarking/sddf_feature_schema_v2.json")
    parser.add_argument("--output-root", default="model_runs/sddf_training_splits_slm_only/sddf_ablations_v3")
    parser.add_argument("--class-weight", default="balanced", choices=["balanced", "none"])
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--disable-embeddings", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seeds", default="42,43,44,45,46")
    parser.add_argument("--variance-threshold", type=float, default=1e-12)
    parser.add_argument("--corr-threshold", type=float, default=0.95)
    args = parser.parse_args()

    script_path = Path("framework/benchmarking/sddf_train_pipeline.py").resolve()
    base_schema_path = Path(args.base_feature_schema_path).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    base_schema = _load_schema(base_schema_path)
    summary: dict[str, Any] = {"runs": [], "errors": []}

    for ablation in ABLATIONS:
        schema = _build_ablation_schema(base_schema, ablation)
        ablation_dir = output_root / ablation
        ablation_dir.mkdir(parents=True, exist_ok=True)
        schema_path = ablation_dir / "feature_schema.json"
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

        cmd = [
            args.python_bin,
            str(script_path),
            "--splits-root",
            args.splits_root,
            "--feature-schema-path",
            str(schema_path),
            "--output-dir",
            str(ablation_dir / "artifacts"),
            "--class-weight",
            args.class_weight,
            "--exclude-model-substrings",
            args.exclude_model_substrings,
            "--embedding-model",
            args.embedding_model,
            "--jobs",
            str(args.jobs),
            "--seeds",
            args.seeds,
            "--variance-threshold",
            str(args.variance_threshold),
            "--corr-threshold",
            str(args.corr_threshold),
        ]
        if args.disable_embeddings:
            cmd.append("--disable-embeddings")

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            summary["runs"].append({"ablation": ablation, "schema": str(schema_path), "output_dir": str(ablation_dir / "artifacts")})
        else:
            summary["errors"].append(
                {
                    "ablation": ablation,
                    "returncode": int(proc.returncode),
                    "stdout_tail": proc.stdout[-1200:],
                    "stderr_tail": proc.stderr[-1200:],
                }
            )

    report_path = output_root / "ablation_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote: {report_path}")
    print(f"Successes={len(summary['runs'])} Errors={len(summary['errors'])}")
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
