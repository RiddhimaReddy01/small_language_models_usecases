from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .curves import compute_ratio_curve, smooth_ratio_curve
from .gates import apply_quality_gate, evaluate_quality_gate, label_slm_acceptability
from .matching import match_model_outputs
from .plots import plot_ratio_curve
from .routing import learn_routing_thresholds
from .tipping import estimate_tipping_point
from .uncertainty import bootstrap_ratio_curve, bootstrap_tipping_point
from .validator import PART_B_SECTIONS, SectionStatus
from .zones import assign_deployment_zone


def generate_part_b_report(
    run_path: str | Path,
    benchmark: str,
    *,
    output_dir: str | Path | None = None,
    readiness: dict[str, Any] | None = None,
    quality_threshold: float = 0.85,
    target_precision: float = 0.95,
) -> dict[str, str]:
    run_root = Path(run_path)
    sddf_root = _resolve_sddf_root(run_root)
    report_dir = Path(output_dir) if output_dir is not None else ((sddf_root / "reports") if sddf_root is not None else (run_root.parent / "reports" if run_root.is_file() else run_root / "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    archive_df = _load_archive(sddf_root / "canonical_rows.jsonl") if sddf_root is not None else pd.DataFrame()
    statuses = _normalize_readiness(readiness, archive_df)
    pair_payloads = _build_pair_payloads(archive_df, report_dir, quality_threshold, target_precision)

    report_md = _render_part_b_markdown(
        benchmark=benchmark,
        run_root=run_root,
        statuses=statuses,
        archive_df=archive_df,
        pair_payloads=pair_payloads,
    )
    report_path = report_dir / "part_b_report.md"
    report_path.write_text(report_md, encoding="utf-8")

    summary_path = report_dir / "part_b_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "benchmark": benchmark,
                "run_path": str(run_root.resolve()),
                "sddf_root": str(sddf_root.resolve()) if sddf_root is not None else None,
                "statuses": {key: {"status": value.status, "reason": value.reason} for key, value in statuses.items()},
                "pairs": pair_payloads,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"report_path": str(report_path), "summary_path": str(summary_path)}


def _resolve_sddf_root(run_root: Path) -> Path | None:
    if run_root.name == "sddf":
        return run_root
    candidate = run_root / "sddf"
    if candidate.exists():
        return candidate
    return None


def _load_archive(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return pd.DataFrame()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def _normalize_readiness(readiness: dict[str, Any] | None, archive_df: pd.DataFrame) -> dict[str, SectionStatus]:
    statuses: dict[str, SectionStatus] = {}
    if readiness and "part_b" in readiness:
        for section in PART_B_SECTIONS:
            value = readiness["part_b"].get(section, {})
            statuses[section] = SectionStatus(value.get("status", "unsupported"), value.get("reason", ""))
        return statuses

    has_archive = not archive_df.empty
    families = set(archive_df.get("model_family", pd.Series(dtype=object)).dropna().astype(str)) if has_archive else set()
    matched_possible = len(families) >= 2
    for section in PART_B_SECTIONS:
        if not has_archive:
            statuses[section] = SectionStatus("unsupported", "No SDDF archive found.")
        elif matched_possible:
            statuses[section] = SectionStatus("available", "Computed from SDDF archive.")
        else:
            statuses[section] = SectionStatus("partial", "Archive exists, but no matched SLM and LLM rows were found.")
    if has_archive and not matched_possible:
        for section in ["dominant_difficulty_dimension", "difficulty_annotation_binning", "failure_taxonomy"]:
            statuses[section] = SectionStatus("available", "Computed from SDDF archive.")
    return statuses


def _build_pair_payloads(
    archive_df: pd.DataFrame,
    report_dir: Path,
    quality_threshold: float,
    target_precision: float,
) -> list[dict[str, Any]]:
    if archive_df.empty:
        return []

    payloads: list[dict[str, Any]] = []
    for (_, dataset), group in archive_df.groupby(["task", "dataset"], dropna=False):
        slm_models = sorted(group.loc[group["model_family"] == "SLM", "model_name"].dropna().unique())
        llm_models = sorted(group.loc[group["model_family"] == "LLM", "model_name"].dropna().unique())
        for slm_name in slm_models:
            for llm_name in llm_models:
                matched = match_model_outputs(group, slm_name, llm_name)
                if matched.empty:
                    continue
                curve = compute_ratio_curve(matched)
                if curve.empty:
                    continue
                smooth = smooth_ratio_curve(curve)
                tipping_point = estimate_tipping_point(smooth)
                ratio_ci = bootstrap_ratio_curve(matched, n_boot=min(200, max(20, len(matched) * 10)))
                tipping_ci = bootstrap_tipping_point(matched, n_boot=min(200, max(20, len(matched) * 10)))

                plot_path = None
                try:
                    plot_path = str(
                        plot_ratio_curve(
                            smooth,
                            report_dir / f"{_slug(dataset)}_{_slug(slm_name)}_vs_{_slug(llm_name)}.png",
                        )
                    )
                except Exception:
                    plot_path = None

                gated = label_slm_acceptability(matched, quality_threshold=quality_threshold)
                thresholds = learn_routing_thresholds(matched, target_precision=target_precision)
                gate_metrics = None
                if thresholds:
                    gated = apply_quality_gate(gated, {"max_difficulty": thresholds["max_difficulty"]})
                    gate_metrics = evaluate_quality_gate(gated)

                zone_rows = smooth.copy()
                zone_rows["zone"] = zone_rows.apply(assign_deployment_zone, axis=1)

                payloads.append(
                    {
                        "dataset": dataset,
                        "slm_name": slm_name,
                        "llm_name": llm_name,
                        "matched_examples": int(len(matched)),
                        "tipping_point": tipping_point,
                        "tipping_ci": tipping_ci,
                        "gate_thresholds": thresholds,
                        "gate_metrics": gate_metrics,
                        "zones": zone_rows[["difficulty_bin", "bin_center", "ratio_smooth", "zone"]].to_dict(orient="records"),
                        "ratio_ci": ratio_ci.to_dict(orient="records"),
                        "plot_path": plot_path,
                    }
                )
    return payloads


def _render_part_b_markdown(
    *,
    benchmark: str,
    run_root: Path,
    statuses: dict[str, SectionStatus],
    archive_df: pd.DataFrame,
    pair_payloads: list[dict[str, Any]],
) -> str:
    lines = [
        "# Part B - SDDF Analysis",
        "",
        f"- Benchmark: `{benchmark}`",
        f"- Run path: `{run_root}`",
        "",
    ]
    lines.extend(_render_section("SDDF: Dominant Difficulty Dimension", statuses["dominant_difficulty_dimension"], _dominant_dimension_body(archive_df)))
    lines.extend(_render_section("Difficulty Annotation + Binning", statuses["difficulty_annotation_binning"], _difficulty_binning_body(archive_df)))
    lines.extend(_render_section("Matched SLM vs LLM Analysis", statuses["matched_slm_llm_analysis"], _matched_analysis_body(pair_payloads)))
    lines.extend(_render_section("Capability Curve + Tipping Point", statuses["capability_curve_tipping_point"], _curve_body(pair_payloads)))
    lines.extend(_render_section("Uncertainty Analysis", statuses["uncertainty_analysis"], _uncertainty_body(pair_payloads)))
    lines.extend(_render_section("Failure Taxonomy", statuses["failure_taxonomy"], _failure_taxonomy_body(archive_df)))
    lines.extend(_render_section("Quality Gate", statuses["quality_gate"], _quality_gate_body(pair_payloads)))
    lines.extend(_render_section("Deployment Zones", statuses["deployment_zones"], _zones_body(pair_payloads)))
    lines.extend(_render_section("Routing Policy", statuses["routing_policy"], _routing_body(pair_payloads)))
    return "\n".join(lines) + "\n"


def _render_section(title: str, status: SectionStatus, body: list[str]) -> list[str]:
    lines = [f"## {title}", "", f"- Status: `{status.status}`", f"- Reason: {status.reason or 'N/A'}", ""]
    if status.status in {"available", "partial"} and body:
        lines.extend(body)
    else:
        lines.append("Not enough evidence to render this section.")
    lines.append("")
    return lines


def _dominant_dimension_body(archive_df: pd.DataFrame) -> list[str]:
    if archive_df.empty or "difficulty_dim" not in archive_df.columns:
        return []
    counts = archive_df["difficulty_dim"].fillna("unknown").value_counts().to_dict()
    lines = ["### Summary", ""]
    for key, value in counts.items():
        lines.append(f"- `{key}`: {value} examples")
    return lines


def _difficulty_binning_body(archive_df: pd.DataFrame) -> list[str]:
    if archive_df.empty or "difficulty_bin" not in archive_df.columns:
        return []
    grouped = (
        archive_df.groupby(["difficulty_bin", "model_family"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values(["difficulty_bin", "model_family"])
    )
    lines = ["### Bin Counts", ""]
    for row in grouped.to_dict(orient="records"):
        lines.append(f"- Bin `{row['difficulty_bin']}` / `{row.get('model_family', 'unknown')}`: {row['n']} rows")
    return lines


def _matched_analysis_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = ["### Pairs", ""]
    for payload in pair_payloads:
        lines.append(f"- `{payload['slm_name']}` vs `{payload['llm_name']}` on `{payload['dataset']}`: {payload['matched_examples']} matched examples")
    return lines


def _curve_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = []
    for payload in pair_payloads:
        plot_path = payload.get("plot_path")
        lines.extend(
            [
                f"### {payload['slm_name']} vs {payload['llm_name']}",
                "",
                f"- Tipping point: `{payload['tipping_point']}`",
                f"- Plot file: `{plot_path}`" if plot_path else "- Plot file: not generated",
                "",
            ]
        )
        if plot_path:
            plot_name = Path(plot_path).name
            lines.append(f"![Capability curve]({plot_name})")
            lines.append("")
    return lines


def _uncertainty_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = []
    for payload in pair_payloads:
        ci = payload.get("tipping_ci", {})
        lines.extend([f"### {payload['slm_name']} vs {payload['llm_name']}", "", f"- Tipping median: `{ci.get('tipping_point')}`", f"- 95% CI: `{ci.get('ci_low')}` to `{ci.get('ci_high')}`", ""])
    return lines


def _failure_taxonomy_body(archive_df: pd.DataFrame) -> list[str]:
    if archive_df.empty:
        return []
    structural = 0
    fixable = 0
    invalid = int((archive_df["valid_output"].fillna(0).astype(int) == 0).sum()) if "valid_output" in archive_df.columns else 0
    for _, row in archive_df.iterrows():
        score = float(row.get("difficulty_score") or 0.0)
        dim = str(row.get("difficulty_dim") or "")
        valid = int(row.get("valid_output") or 0)
        metric = float(row.get("primary_metric") or 0.0)
        if valid == 0:
            fixable += 1
        elif dim == "R_hat" and score >= 3:
            structural += 1
        elif dim == "|Gamma|" or metric < 0.5:
            fixable += 1
    return [
        f"- Heuristic structural failures: {structural}",
        f"- Heuristic fixable failures: {fixable}",
        f"- Invalid outputs: {invalid}",
        "- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.",
    ]


def _quality_gate_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = []
    for payload in pair_payloads:
        metrics = payload.get("gate_metrics")
        thresholds = payload.get("gate_thresholds")
        lines.extend([f"### {payload['slm_name']} vs {payload['llm_name']}", ""])
        if thresholds:
            lines.append(f"- Max difficulty: `{thresholds.get('max_difficulty')}`")
            lines.append(f"- Gate precision: `{thresholds.get('gate_precision')}`")
            lines.append(f"- Gate recall: `{thresholds.get('gate_recall')}`")
        if metrics:
            lines.append(f"- Evaluated precision: `{metrics.get('precision')}`")
            lines.append(f"- Evaluated recall: `{metrics.get('recall')}`")
            lines.append(f"- Evaluated F1: `{metrics.get('f1')}`")
        lines.append("")
    return lines


def _zones_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = []
    for payload in pair_payloads:
        lines.extend([f"### {payload['slm_name']} vs {payload['llm_name']}", ""])
        for row in payload.get("zones", []):
            lines.append(f"- Bin `{row['difficulty_bin']}` at difficulty `{row['bin_center']:.3f}` -> Zone `{row['zone']}`")
        lines.append("")
    return lines


def _routing_body(pair_payloads: list[dict[str, Any]]) -> list[str]:
    if not pair_payloads:
        return []
    lines = []
    for payload in pair_payloads:
        thresholds = payload.get("gate_thresholds")
        lines.extend([f"### {payload['slm_name']} vs {payload['llm_name']}", ""])
        if thresholds:
            safe_max = thresholds.get("max_difficulty")
            hybrid_max = payload.get("tipping_point") or safe_max
            lines.append(f"- Suggested `SLM` threshold: difficulty <= `{safe_max}`")
            lines.append(f"- Suggested `SLM_WITH_GATE` threshold: difficulty <= `{hybrid_max}`")
            lines.append(f"- Suggested `LLM` threshold: difficulty > `{hybrid_max}`")
        else:
            lines.append("- No routing threshold learned.")
        lines.append("")
    return lines


def _slug(value: Any) -> str:
    raw = str(value or "unknown").lower()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")
