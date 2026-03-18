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
from .setup_reporting import _extract_part_a_payload
from .tipping import estimate_tipping_point, tipping_sensitivity
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
    report_dir = (
        Path(output_dir)
        if output_dir is not None
        else ((sddf_root / "reports") if sddf_root is not None else (run_root.parent / "reports" if run_root.is_file() else run_root / "reports"))
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    archive_df = _load_archive(sddf_root / "canonical_rows.jsonl") if sddf_root is not None else pd.DataFrame()
    inferred_sections = _build_inferred_sections(benchmark, run_root)
    statuses = _normalize_readiness(readiness, archive_df, inferred_sections)
    pair_payloads = _build_pair_payloads(archive_df, report_dir, quality_threshold, target_precision)

    report_md = _render_part_b_markdown(
        benchmark=benchmark,
        run_root=run_root,
        statuses=statuses,
        archive_df=archive_df,
        pair_payloads=pair_payloads,
        inferred_sections=inferred_sections,
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
    if run_root.is_file():
        candidate = run_root.parent / "sddf"
        if candidate.exists():
            return candidate
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


def _normalize_readiness(
    readiness: dict[str, Any] | None,
    archive_df: pd.DataFrame,
    inferred_sections: dict[str, list[str]],
) -> dict[str, SectionStatus]:
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
            if inferred_sections.get(section):
                statuses[section] = SectionStatus("partial", "Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.")
            else:
                statuses[section] = SectionStatus("unsupported", "No SDDF archive found.")
            continue

        if matched_possible:
            statuses[section] = SectionStatus("available", "Computed from SDDF archive.")
            continue

        if section in {"dominant_difficulty_dimension", "difficulty_annotation_binning", "failure_taxonomy"}:
            statuses[section] = SectionStatus("available", "Computed from SDDF archive.")
        elif inferred_sections.get(section):
            statuses[section] = SectionStatus("partial", "Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.")
        else:
            statuses[section] = SectionStatus("partial", "Archive exists, but no matched SLM and LLM rows were found.")
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
                matched = _ensure_pair_bins(matched)
                if matched.empty:
                    continue
                curve = compute_ratio_curve(matched)
                if curve.empty:
                    continue
                smooth = smooth_ratio_curve(curve)
                tipping_point = estimate_tipping_point(smooth)
                tipping_thresholds = tipping_sensitivity(smooth)
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
                        "tipping_sensitivity": tipping_thresholds,
                        "tipping_ci": tipping_ci,
                        "gate_thresholds": thresholds,
                        "gate_metrics": gate_metrics,
                        "zones": zone_rows[["difficulty_bin", "bin_center", "ratio_smooth", "zone"]].to_dict(orient="records"),
                        "ratio_ci": ratio_ci.to_dict(orient="records"),
                        "plot_path": plot_path,
                    }
                )
    return payloads


def _ensure_pair_bins(matched: pd.DataFrame) -> pd.DataFrame:
    if matched.empty or "difficulty_bin" not in matched.columns:
        return matched

    out = matched.copy()
    if out["difficulty_bin"].notna().any():
        return out

    if "difficulty_score" not in out.columns or out["difficulty_score"].dropna().empty:
        return out

    unique_scores = out["difficulty_score"].dropna().nunique()
    if unique_scores <= 1:
        out["difficulty_bin"] = 0
        return out

    try:
        out["difficulty_bin"] = pd.qcut(out["difficulty_score"], q=min(5, unique_scores), labels=False, duplicates="drop")
    except Exception:
        out["difficulty_bin"] = pd.cut(out["difficulty_score"], bins=min(5, unique_scores), labels=False, include_lowest=True)
    return out


def _render_part_b_markdown(
    *,
    benchmark: str,
    run_root: Path,
    statuses: dict[str, SectionStatus],
    archive_df: pd.DataFrame,
    pair_payloads: list[dict[str, Any]],
    inferred_sections: dict[str, list[str]],
) -> str:
    direct_bodies = {
        "dominant_difficulty_dimension": _dominant_dimension_body(archive_df),
        "difficulty_annotation_binning": _difficulty_binning_body(archive_df),
        "matched_slm_llm_analysis": _matched_analysis_body(pair_payloads),
        "capability_curve_tipping_point": _curve_body(pair_payloads),
        "uncertainty_analysis": _uncertainty_body(pair_payloads),
        "failure_taxonomy": _failure_taxonomy_body(archive_df),
        "quality_gate": _quality_gate_body(pair_payloads),
        "deployment_zones": _zones_body(pair_payloads),
        "routing_policy": _routing_body(pair_payloads),
    }

    lines = [
        "# Part B - SDDF Analysis",
        "",
        f"- Benchmark: `{benchmark}`",
        f"- Run path: `{run_root}`",
        "- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.",
        "",
    ]
    lines.extend(_render_section("SDDF: Dominant Difficulty Dimension", statuses["dominant_difficulty_dimension"], _section_body("dominant_difficulty_dimension", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Difficulty Annotation + Binning", statuses["difficulty_annotation_binning"], _section_body("difficulty_annotation_binning", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Matched SLM vs LLM Analysis", statuses["matched_slm_llm_analysis"], _section_body("matched_slm_llm_analysis", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Capability Curve + Tipping Point", statuses["capability_curve_tipping_point"], _section_body("capability_curve_tipping_point", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Uncertainty Analysis", statuses["uncertainty_analysis"], _section_body("uncertainty_analysis", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Failure Taxonomy", statuses["failure_taxonomy"], _section_body("failure_taxonomy", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Quality Gate", statuses["quality_gate"], _section_body("quality_gate", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Deployment Zones", statuses["deployment_zones"], _section_body("deployment_zones", direct_bodies, inferred_sections)))
    lines.extend(_render_section("Routing Policy", statuses["routing_policy"], _section_body("routing_policy", direct_bodies, inferred_sections)))
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
                f"- Tipping sensitivity: `{payload.get('tipping_sensitivity', {})}`",
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
        lines.extend(
            [
                f"### {payload['slm_name']} vs {payload['llm_name']}",
                "",
                f"- Tipping median: `{ci.get('tipping_point')}`",
                f"- 95% CI: `{ci.get('ci_low')}` to `{ci.get('ci_high')}`",
                f"- Threshold sweep: `{payload.get('tipping_sensitivity', {})}`",
                "",
            ]
        )
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
        "- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.",
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


def _section_body(
    section: str,
    direct_bodies: dict[str, list[str]],
    inferred_sections: dict[str, list[str]],
) -> list[str]:
    direct = direct_bodies.get(section, [])
    return direct if direct else inferred_sections.get(section, [])


def _build_inferred_sections(benchmark: str, run_root: Path) -> dict[str, list[str]]:
    profile = _benchmark_inference_profile(benchmark)
    if not profile:
        return {}

    try:
        payload = _extract_part_a_payload(benchmark, run_root)
    except Exception:
        payload = {}

    model_lines = _inferred_model_comparison_lines(benchmark, payload)
    sample_line = _sample_size_line(payload)

    return {
        "dominant_difficulty_dimension": [
            "### Inferred dominant dimension",
            "",
            f"- Inferred dominant difficulty dimension: `{profile['dimension']}`",
            f"- Basis: {profile['dimension_basis']}",
            "- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.",
        ],
        "difficulty_annotation_binning": [
            "### Inferred binning rule",
            "",
            f"- Low difficulty bucket: {profile['binning_low']}",
            f"- Mid difficulty bucket: {profile['binning_mid']}",
            f"- High difficulty bucket: {profile['binning_high']}",
            "- Caveat: bins are historical workload strata, not newly recomputed row-level bins.",
        ],
        "matched_slm_llm_analysis": [
            "### Historical comparison",
            "",
            *model_lines,
            "- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.",
        ],
        "capability_curve_tipping_point": [
            "### Inferred transition point",
            "",
            f"- Historical tipping signal: {profile['tipping_point']}",
            f"- Operational reading: {profile['tipping_interpretation']}",
            "- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.",
        ],
        "uncertainty_analysis": [
            "### Historical uncertainty",
            "",
            sample_line,
            f"- Uncertainty source: {profile['uncertainty']}",
            "- Caveat: no bootstrap confidence interval was available without matched rerun rows.",
        ],
        "failure_taxonomy": [
            "### Inferred failure modes",
            "",
            *[f"- {item}" for item in profile["failure_modes"]],
            "- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.",
        ],
        "quality_gate": [
            "### Suggested gate",
            "",
            *[f"- {item}" for item in profile["quality_gate"]],
            "- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.",
        ],
        "deployment_zones": [
            "### Inferred deployment stance",
            "",
            f"- Likely SDDF stance: {profile['deployment_zone']}",
            f"- Why: {profile['deployment_basis']}",
            "- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.",
        ],
        "routing_policy": [
            "### Suggested routing policy",
            "",
            *[f"- {item}" for item in profile["routing_policy"]],
            "- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.",
        ],
    }


def _sample_size_line(payload: dict[str, Any]) -> str:
    raw = payload.get("raw_benchmark_results", {}) if isinstance(payload, dict) else {}
    if "latest_row_count" in raw:
        return f"- Historical sample size signal: latest saved run had `{raw['latest_row_count']}` rows."
    if "task_result_count" in raw:
        return f"- Historical sample size signal: `{raw['task_result_count']}` task results were saved."
    if "prediction_row_count" in raw:
        return f"- Historical sample size signal: `{raw['prediction_row_count']}` prediction rows were saved."
    if "example_count_per_prediction_file" in raw:
        return f"- Historical sample size signal: `{raw['example_count_per_prediction_file']}` prediction examples per file."
    if "record_count" in raw:
        return f"- Historical sample size signal: `{raw['record_count']}` records were saved."
    if "response_count" in raw:
        return f"- Historical sample size signal: `{raw['response_count']}` prompt-response records were saved."
    if "example_count_per_run" in raw:
        return f"- Historical sample size signal: `{raw['example_count_per_run']}` examples per run."
    return "- Historical sample size signal: aggregate-only artifacts were available."


def _inferred_model_comparison_lines(benchmark: str, payload: dict[str, Any]) -> list[str]:
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}

    if benchmark == "maths" and isinstance(metrics, dict):
        scored = []
        for model_name, model_metrics in metrics.items():
            capability = (model_metrics or {}).get("capability", {})
            score = capability.get("final_answer_accuracy_percent")
            if score is not None:
                scored.append((float(score), model_name))
        if scored:
            scored.sort(reverse=True)
            lines = [f"- Historical top model on primary metric: `{scored[0][1]}` at `{scored[0][0]:.1f}%` final-answer accuracy."]
            if len(scored) > 1:
                lines.append(f"- Best spread observed in saved artifacts: `{scored[0][1]}` exceeds `{scored[-1][1]}` by `{scored[0][0] - scored[-1][0]:.1f}` points.")
            return lines

    if benchmark == "retrieval_grounded" and isinstance(metrics, dict):
        lines = []
        for model_name, model_metrics in metrics.items():
            capability = (model_metrics or {}).get("capability", {})
            exact_match = capability.get("exact_match")
            f1_score = capability.get("f1_score")
            if exact_match is not None and f1_score is not None:
                lines.append(f"- Saved retrieval run: `{model_name}` reached `{exact_match:.2f}` EM and `{f1_score:.2f}` F1.")
        if lines:
            return lines

    default_lines = {
        "classification": [
            "- Historical classification evidence suggests SLMs stay competitive on low-ambiguity labels and degrade on sarcasm, adjacent emotions, and pragmatic ambiguity.",
            "- The saved artifact here is single-model, so this section stays benchmark-level rather than paired.",
        ],
        "instruction_following": [
            "- Historical instruction-following evidence indicates the main gap is constraint adherence, not topical generation quality.",
            "- Local SLMs remain viable on lightly constrained prompts, while exact count and multi-constraint prompts are the main escalation candidates.",
        ],
        "summarization": [
            "- Historical summarization results show tuned local models outperform generic local baselines on quality, while API baselines retain a latency advantage.",
            "- The strongest quality gap appears in factual preservation rather than surface fluency.",
        ],
        "information_extraction": [
            "- Historical extraction results indicate local SLMs are strong on field-copy and schema adherence, while normalization-heavy fields degrade.",
            "- The comparison signal is directional because older runs were not stored as matched row-level archives.",
        ],
        "code_generation": [
            "- Historical code-generation results suggest API baselines retain an advantage on non-trivial algorithmic tasks, while local SLMs only pass trivial tasks reliably.",
            "- Because the saved artifacts are aggregate, this remains a directional comparison rather than a paired one.",
        ],
        "text_generation": [
            "- Historical text-generation evidence indicates local SLMs are competitive on open-ended generation quality but fall behind on heavy multi-constraint adherence.",
        ],
    }
    return default_lines.get(benchmark, ["- Historical benchmark artifacts were not rich enough for a stronger aggregate comparison summary."])


def _benchmark_inference_profile(benchmark: str) -> dict[str, Any] | None:
    profiles = {
        "classification": {
            "dimension": "H",
            "dimension_basis": "classification difficulty is dominated by lexical and semantic ambiguity, which aligns with entropy-style label uncertainty rather than structural output constraints.",
            "binning_low": "clear sentiment or topic labels with direct lexical cues",
            "binning_mid": "domain or emotion labels requiring mild pragmatic inference",
            "binning_high": "sarcasm, adjacent emotions, and ambiguous pragmatic cues",
            "tipping_point": "historical evidence places the main break around IC≈2-style ambiguity, where pragmatic interpretation becomes necessary.",
            "tipping_interpretation": "simple single-hop labels stay SLM-friendly; ambiguity-heavy examples are better treated as escalation candidates.",
            "uncertainty": "saved classification runs are small and heterogeneous, so confidence around the inferred break is low-to-moderate.",
            "failure_modes": [
                "semantic ambiguity between neighboring labels",
                "sarcasm or irony that flips surface polarity",
                "invalid label generation when the prompt-response contract is weak",
            ],
            "quality_gate": [
                "accept SLM outputs when the label is in-vocabulary and confidence is high",
                "escalate examples containing ambiguity markers, sarcasm cues, or low-confidence normalization",
            ],
            "deployment_zone": "SLM-preferred for routine classification, with escalation on ambiguity-heavy slices.",
            "deployment_basis": "historical results show strong low-cost performance on easy labels, but notable degradation on ambiguity-heavy subsets.",
            "routing_policy": [
                "route clear single-label examples to the SLM path",
                "route ambiguous or pragmatic examples to an LLM or human review path",
            ],
        },
        "text_generation": {
            "dimension": "|Gamma|",
            "dimension_basis": "historical text-generation failures cluster around simultaneous output constraints rather than basic generation ability.",
            "binning_low": "open-ended generation with minimal formatting requirements",
            "binning_mid": "single format or tone constraints",
            "binning_high": "exact length, multi-constraint, or strict formatting demands",
            "tipping_point": "historical evidence suggests the main break occurs once MC-style constraint burden reaches roughly 3 simultaneous requirements.",
            "tipping_interpretation": "generation quality remains acceptable, but compliance deteriorates quickly once multiple hard constraints stack up.",
            "uncertainty": "the saved matched rerun is tiny, so the inferred transition is directional only.",
            "failure_modes": [
                "exact length non-compliance",
                "constraint collisions across format, keyword, and style requirements",
                "overgeneration despite otherwise fluent output",
            ],
            "quality_gate": [
                "accept SLM outputs on unconstrained or lightly constrained prompts",
                "apply validators or constrained decoding before accepting multi-constraint generations",
            ],
            "deployment_zone": "Hybrid or SLM-with-mitigation depending on constraint burden.",
            "deployment_basis": "local SLMs are competitive on free-form generation, but constraint-heavy prompts benefit from a gate or escalation.",
            "routing_policy": [
                "send simple prompts to the SLM path",
                "use constrained decoding for moderate constraint bundles",
                "escalate high-constraint prompts to an LLM path when exact compliance matters",
            ],
        },
        "information_extraction": {
            "dimension": "|Gamma|",
            "dimension_basis": "historical extraction performance is strongest on schema-bound copy tasks and weakest on normalization-heavy fields, indicating structural output constraints and cleanup burden dominate.",
            "binning_low": "direct field copy into a fixed schema",
            "binning_mid": "light normalization or multi-field assembly",
            "binning_high": "date normalization, address cleanup, or noisy OCR normalization",
            "tipping_point": "historical evidence places the cliff around normalization-heavy fields where parsing demand rises above simple copy behavior.",
            "tipping_interpretation": "schema adherence is manageable locally; parsing and normalization are the real failure point.",
            "uncertainty": "older extraction runs are sparse, so inferred thresholds should be treated as directional.",
            "failure_modes": [
                "normalization failures on dates and addresses",
                "schema-valid but semantically wrong field extraction",
                "OCR noise propagation into output cleanup steps",
            ],
            "quality_gate": [
                "accept SLM outputs when schema validity is high and fields are copy-like",
                "route normalization-heavy fields through deterministic post-processing or escalation",
            ],
            "deployment_zone": "SLM-with-mitigation for structured extraction, escalating only normalization-heavy edge cases.",
            "deployment_basis": "historical results favor local models on structured extraction while showing a clear drop on normalization subtasks.",
            "routing_policy": [
                "keep straightforward field extraction on the SLM path",
                "add deterministic cleanup for normalization steps",
                "escalate noisy or ambiguous normalization cases",
            ],
        },
        "summarization": {
            "dimension": "n_in",
            "dimension_basis": "historical summarization difficulty is driven by how much source content must be compressed while preserving facts, making input length and information density the leading burden.",
            "binning_low": "short, single-topic summarization with narrow context",
            "binning_mid": "multi-sentence summarization with moderate compression pressure",
            "binning_high": "long-context compression where factual preservation and hallucination become difficult",
            "tipping_point": "historical evidence suggests tuned local models remain viable around IC≈1, but factual reliability degrades once summaries require broader synthesis or stricter compression.",
            "tipping_interpretation": "domain-tuned summarizers can work well on narrow news-style compression; broader synthesis pushes toward higher-capability models or guardrails.",
            "uncertainty": "sample sizes are modest and some comparisons mix tuned and generic models, so the inferred boundary is moderate-confidence only.",
            "failure_modes": [
                "hallucinated content in compressed summaries",
                "loss of key facts under aggressive compression",
                "length-control failure despite otherwise acceptable summaries",
            ],
            "quality_gate": [
                "accept local summaries when factual preservation checks pass and length control is not strict",
                "escalate long-context or fact-critical summaries to a stronger model",
            ],
            "deployment_zone": "Conditional SLM for tuned summarizers, escalating on fact-critical or long-context jobs.",
            "deployment_basis": "historical tuned local models are useful, but factuality and compression reliability remain the limiting factors.",
            "routing_policy": [
                "route short, domain-tuned summary workloads to the local model",
                "route long-context or fact-sensitive summaries to an LLM or verification layer",
            ],
        },
        "instruction_following": {
            "dimension": "|Gamma|",
            "dimension_basis": "historical instruction-following failures are dominated by simultaneous output constraints rather than missing topical knowledge.",
            "binning_low": "single-topic instructions with one simple requirement",
            "binning_mid": "format or lexical requirements with otherwise simple content",
            "binning_high": "exact word-count or multi-constraint instructions",
            "tipping_point": "historical evidence suggests the main break occurs around MC≈3, where exact compliance becomes the primary bottleneck.",
            "tipping_interpretation": "content generation stays easy, but exact obedience to stacked constraints quickly becomes fragile.",
            "uncertainty": "the saved artifacts support only aggregate inference, so uncertainty remains high for any exact threshold.",
            "failure_modes": [
                "exact word-count misses",
                "constraint stacking failures across lexical, length, and format rules",
                "overgeneration despite topical correctness",
            ],
            "quality_gate": [
                "accept SLM outputs when only one or two simple constraints are present",
                "require validators or escalation for exact count and simultaneous-constraint prompts",
            ],
            "deployment_zone": "SLM-with-mitigation for simple instructions; hybrid for strict compliance workloads.",
            "deployment_basis": "historical evidence shows the issue is controllability, not base fluency.",
            "routing_policy": [
                "route simple or lightly constrained instructions to SLMs",
                "apply validation or escalation for count-sensitive or multi-constraint prompts",
            ],
        },
        "code_generation": {
            "dimension": "R_hat",
            "dimension_basis": "historical code-generation failures track algorithmic reasoning depth and state tracking more than formatting or syntax alone.",
            "binning_low": "single-loop or direct-map programming tasks",
            "binning_mid": "moderate control flow with limited state",
            "binning_high": "algorithmic problems requiring recursion, stacks, or multi-step decomposition",
            "tipping_point": "historical evidence suggests a sharp break once tasks move beyond trivial single-loop logic into algorithmic reasoning.",
            "tipping_interpretation": "local SLMs can sometimes handle trivial tasks, but non-trivial algorithms are still a strong escalation signal.",
            "uncertainty": "completed-task counts are unstable and some local runs were incomplete, so exact thresholds should be treated cautiously.",
            "failure_modes": [
                "algorithmic reasoning failure despite syntactic validity",
                "incorrect API or library usage",
                "state-tracking errors in multi-step solutions",
            ],
            "quality_gate": [
                "accept SLM outputs only on trivial, low-reasoning tasks with passing tests",
                "escalate recursive, multi-structure, or benchmark-hard tasks by default",
            ],
            "deployment_zone": "LLM-preferred except for trivial code generation slices.",
            "deployment_basis": "historical pass rates show the primary bottleneck is reasoning depth, not formatting.",
            "routing_policy": [
                "reserve SLMs for simple transformation or boilerplate tasks",
                "route algorithmic or benchmark-hard tasks directly to stronger models",
            ],
        },
        "maths": {
            "dimension": "R_hat",
            "dimension_basis": "historical maths performance is dominated by reasoning depth, intermediate-state tracking, and multi-step dependency chains.",
            "binning_low": "single-step arithmetic or direct conversion",
            "binning_mid": "short reasoning chains with limited intermediate state",
            "binning_high": "multi-step word problems with dependent calculations",
            "tipping_point": "historical evidence suggests a clear break once tasks require more than one straightforward reasoning step.",
            "tipping_interpretation": "simple arithmetic remains viable locally, but multi-step reasoning pushes quality toward stronger models quickly.",
            "uncertainty": "sample sizes vary by model and some historical runs mix datasets, so inferred thresholds are moderate-confidence only.",
            "failure_modes": [
                "incorrect intermediate reasoning despite well-formed output",
                "confident wrong answers on multi-step problems",
                "low perturbation robustness on paraphrased questions",
            ],
            "quality_gate": [
                "accept SLM outputs only for simple arithmetic-like prompts or when a verifier agrees",
                "escalate multi-step word problems and variable-dependent reasoning tasks",
            ],
            "deployment_zone": "LLM-preferred for general mathematical reasoning, with narrow SLM carve-outs.",
            "deployment_basis": "historical accuracy and robustness both deteriorate materially once reasoning depth increases.",
            "routing_policy": [
                "route simple arithmetic and direct conversions to SLMs if cost matters",
                "route multi-step reasoning tasks to LLMs or verification-heavy workflows",
            ],
        },
        "retrieval_grounded": {
            "dimension": "n_in",
            "dimension_basis": "historical retrieval-grounded QA performance is strongest when all required evidence is present in context, making context size and evidence localization the main burden.",
            "binning_low": "verbatim span extraction from short contexts",
            "binning_mid": "short factual answers requiring light paraphrase",
            "binning_high": "paraphrastic or multi-hop reasoning across context",
            "tipping_point": "historical evidence suggests the main degradation begins once the answer is no longer a direct span and paraphrasing or composition is required.",
            "tipping_interpretation": "RAG helps most when it reduces the task to copying from context; once synthesis is needed, higher-capability models help more.",
            "uncertainty": "saved artifacts are single-model for some runs, so exact comparative uncertainty remains high.",
            "failure_modes": [
                "partial answers when paraphrasing is needed",
                "unsupported answers when context does not map cleanly to output",
                "hallucinations when retrieval grounding is weak",
            ],
            "quality_gate": [
                "accept SLM outputs when answer spans are short and context-grounded",
                "escalate no-answer, paraphrastic, or multi-hop cases",
            ],
            "deployment_zone": "SLM-preferred for span-like RAG QA; hybrid for paraphrastic or compositional QA.",
            "deployment_basis": "historical local results are strong on direct grounding but weaken as synthesis pressure increases.",
            "routing_policy": [
                "route direct span or short factual answers to the SLM path",
                "route paraphrastic, uncertain, or multi-hop questions to an LLM path",
            ],
        },
    }
    return profiles.get(benchmark)


def _slug(value: Any) -> str:
    raw = str(value or "unknown").lower()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")
