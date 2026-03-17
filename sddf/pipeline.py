from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .curves import compute_ratio_curve, smooth_ratio_curve
from .difficulty import annotate_dominant_dimension, make_difficulty_bins
from .matching import match_model_outputs
from .schema import validate_results_schema
from .tipping import estimate_tipping_point
from .uncertainty import bootstrap_ratio_curve, bootstrap_tipping_point


def run_sddf_postprocess(
    rows: pd.DataFrame,
    task: str,
    output_dir: str | Path,
    *,
    prompt_col: str | None = None,
    metadata_col: str = "metadata",
    text_col: str = "input_text",
    rule_config: dict[str, Any] | None = None,
    higher_is_better: bool = True,
    n_bins: int = 5,
) -> dict[str, Any]:
    validate_results_schema(rows)
    sddf_dir = Path(output_dir) / "sddf"
    sddf_dir.mkdir(parents=True, exist_ok=True)

    archive_path = sddf_dir / "canonical_rows.jsonl"
    analysis_dir = sddf_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    archive_df = _load_archive(archive_path)
    if archive_df.empty:
        combined = rows.copy()
    else:
        combined = pd.DataFrame(archive_df.to_dict(orient="records") + rows.to_dict(orient="records"))
    combined = _dedupe_rows(combined)

    annotated_frames = []
    for (_, dataset), group in combined.groupby(["task", "dataset"], dropna=False):
        annotated = annotate_dominant_dimension(
            group,
            task=task if group["task"].nunique() == 1 else str(group["task"].iloc[0]),
            text_col=text_col,
            prompt_col=prompt_col,
            metadata_col=metadata_col if metadata_col in group.columns else None,
            rule_config=rule_config,
        )
        annotated = make_difficulty_bins(annotated, n_bins=n_bins)
        annotated_frames.append(annotated)

    combined = pd.concat(annotated_frames, ignore_index=True) if annotated_frames else combined
    _write_archive(combined, archive_path)

    pair_summaries = _analyze_pairs(
        combined,
        analysis_dir=analysis_dir,
        higher_is_better=higher_is_better,
    )

    return {
        "archive_path": str(archive_path),
        "analysis_dir": str(analysis_dir),
        "pair_summaries": pair_summaries,
        "rows": len(rows),
        "archive_rows": len(combined),
    }


def _load_archive(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def _write_archive(df: pd.DataFrame, path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in df.to_dict(orient="records"):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _dedupe_rows(df: pd.DataFrame) -> pd.DataFrame:
    dedupe_keys = ["task", "dataset", "model_name", "example_id"]
    present_keys = [key for key in dedupe_keys if key in df.columns]
    if not present_keys:
        return df.reset_index(drop=True)
    return df.drop_duplicates(subset=present_keys, keep="last").reset_index(drop=True)


def _analyze_pairs(combined: pd.DataFrame, analysis_dir: Path, higher_is_better: bool) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for (task, dataset), group in combined.groupby(["task", "dataset"], dropna=False):
        if group["model_family"].nunique() < 2:
            continue

        slm_models = sorted(group.loc[group["model_family"] == "SLM", "model_name"].dropna().unique())
        llm_models = sorted(group.loc[group["model_family"] == "LLM", "model_name"].dropna().unique())
        if not slm_models or not llm_models:
            continue

        for slm_name in slm_models:
            for llm_name in llm_models:
                try:
                    matched = match_model_outputs(group, slm_name, llm_name)
                except Exception:
                    continue
                if matched.empty or matched["difficulty_bin"].nunique() == 0:
                    continue

                curve = compute_ratio_curve(matched, higher_is_better=higher_is_better)
                if curve.empty:
                    continue
                smooth = smooth_ratio_curve(curve)
                tip = estimate_tipping_point(smooth)
                ratio_ci = bootstrap_ratio_curve(matched, n_boot=min(200, max(20, len(matched) * 10)))
                tip_ci = bootstrap_tipping_point(matched, n_boot=min(200, max(20, len(matched) * 10)))

                pair_slug = _slugify(f"{task}_{dataset}_{slm_name}_vs_{llm_name}")
                smooth.to_csv(analysis_dir / f"{pair_slug}_curve.csv", index=False)
                ratio_ci.to_csv(analysis_dir / f"{pair_slug}_ratio_ci.csv", index=False)

                summary = {
                    "task": task,
                    "dataset": dataset,
                    "slm_name": slm_name,
                    "llm_name": llm_name,
                    "matched_examples": int(len(matched)),
                    "tipping_point": tip,
                    "tipping_ci": tip_ci,
                    "curve_path": str((analysis_dir / f"{pair_slug}_curve.csv").resolve()),
                    "ratio_ci_path": str((analysis_dir / f"{pair_slug}_ratio_ci.csv").resolve()),
                }
                (analysis_dir / f"{pair_slug}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
                summaries.append(summary)

    manifest_path = analysis_dir / "pair_summaries.json"
    manifest_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return summaries


def _slugify(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")
