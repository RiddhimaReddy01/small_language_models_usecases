from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PART_A_SECTIONS = [
    "task_definition",
    "dataset_and_sampling",
    "experimental_setup",
    "metrics",
    "raw_benchmark_results",
]

PART_B_SECTIONS = [
    "dominant_difficulty_dimension",
    "difficulty_annotation_binning",
    "matched_slm_llm_analysis",
    "capability_curve_tipping_point",
    "uncertainty_analysis",
    "failure_taxonomy",
    "quality_gate",
    "deployment_zones",
    "routing_policy",
]


@dataclass
class SectionStatus:
    status: str
    reason: str


@dataclass
class RunReadiness:
    benchmark: str
    run_id: str
    path: str
    overall_status: str
    part_a: dict[str, SectionStatus] = field(default_factory=dict)
    part_b: dict[str, SectionStatus] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "run_id": self.run_id,
            "path": self.path,
            "overall_status": self.overall_status,
            "part_a": {key: asdict(value) for key, value in self.part_a.items()},
            "part_b": {key: asdict(value) for key, value in self.part_b.items()},
            "notes": list(self.notes),
        }


def validate_historical_runs(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    runs: list[RunReadiness] = []
    runs.extend(_scan_classification(root))
    runs.extend(_scan_text_generation(root))
    runs.extend(_scan_summarization(root))
    runs.extend(_scan_instruction_following(root))
    runs.extend(_scan_code_generation(root))
    runs.extend(_scan_maths(root))
    runs.extend(_scan_retrieval_grounded(root))
    runs.extend(_scan_information_extraction(root))
    return {
        "repo_root": str(root.resolve()),
        "runs": [run.to_dict() for run in runs],
    }


def save_historical_run_validation(repo_root: str | Path, output_path: str | Path) -> Path:
    payload = validate_historical_runs(repo_root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def _scan_classification(root: Path) -> list[RunReadiness]:
    results_dir = root / "classification" / "results"
    if not results_dir.exists():
        return []
    runs = []
    for raw_path in sorted(results_dir.glob("raw_results_*.csv")):
        run_id = raw_path.stem.replace("raw_results_", "")
        summary_path = results_dir / f"metrics_summary_{run_id}.json"
        sddf_archive = results_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("classification", run_id, results_dir)
        _set_part_a(run, summary_path.exists(), raw_path.exists(), summary_path.exists(), summary_path.exists(), raw_path.exists())
        _set_part_b(run, sddf_archive.exists(), matched_possible=False)
        if not summary_path.exists():
            run.notes.append("Missing metrics_summary JSON for this raw results file.")
        runs.append(_finalize_run(run))
    return runs


def _scan_text_generation(root: Path) -> list[RunReadiness]:
    runs_dir = root / "text_generation" / "results" / "runs"
    if not runs_dir.exists():
        return []
    runs = []
    for suite_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        manifest = suite_dir / "suite_manifest.json"
        has_raw = any(suite_dir.glob("*.json"))
        has_metadata = any(suite_dir.glob("*_metadata.json"))
        sddf_archive = suite_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("text_generation", suite_dir.name, suite_dir)
        _set_part_a(run, manifest.exists(), manifest.exists(), has_metadata or manifest.exists(), suite_dir.joinpath("benchmark_summary.json").exists(), has_raw)
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        if not manifest.exists():
            run.notes.append("Missing suite_manifest.json.")
        runs.append(_finalize_run(run))
    return runs


def _scan_summarization(root: Path) -> list[RunReadiness]:
    outputs_dir = root / "Summarization" / "outputs"
    if not outputs_dir.exists():
        return []
    runs = []
    candidates = [outputs_dir] + [path for path in outputs_dir.iterdir() if path.is_dir()]
    seen: set[str] = set()
    for run_dir in candidates:
        results_csv = run_dir / "summarization_results.csv"
        summary_json = run_dir / "summarization_summary.json"
        if not results_csv.exists() and not summary_json.exists():
            continue
        run_id = run_dir.name
        if run_id in seen:
            continue
        seen.add(run_id)
        sddf_archive = run_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("summarization", run_id, run_dir)
        _set_part_a(run, summary_json.exists(), summary_json.exists(), summary_json.exists(), summary_json.exists(), results_csv.exists())
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        runs.append(_finalize_run(run))
    return runs


def _scan_instruction_following(root: Path) -> list[RunReadiness]:
    results_dir = root / "instruction_following" / "results"
    if not results_dir.exists():
        return []
    runs = []
    for result_path in sorted(results_dir.glob("*.json")):
        if result_path.name == ".gitkeep":
            continue
        has_responses = _json_has_key(result_path, "responses")
        sddf_archive = results_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("instruction_following", result_path.stem, result_path)
        _set_part_a(run, has_responses, True, True, True, has_responses)
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        runs.append(_finalize_run(run))
    return runs


def _scan_code_generation(root: Path) -> list[RunReadiness]:
    runs_dir = root / "code_generation" / "archive" / "runs"
    if not runs_dir.exists():
        return []
    runs = []
    for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        config_snapshot = run_dir / "config_snapshot.json"
        summary_json = run_dir / "summary.json"
        task_results = run_dir / "task_results.jsonl"
        sddf_archive = run_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("code_generation", run_dir.name, run_dir)
        _set_part_a(run, config_snapshot.exists(), config_snapshot.exists(), config_snapshot.exists(), summary_json.exists(), task_results.exists())
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        runs.append(_finalize_run(run))
    return runs


def _scan_maths(root: Path) -> list[RunReadiness]:
    raw_dir = root / "maths" / "results" / "raw"
    if not raw_dir.exists():
        return []
    runs = []
    for result_path in sorted(raw_dir.glob("*.json")):
        payload = _safe_load_json(result_path)
        dry_run = bool(payload and payload.get("mode") == "dry_run")
        has_records = bool(payload and payload.get("experiments"))
        sddf_archive = result_path.parent / "sddf" / "canonical_rows.jsonl"
        run = _base_run("maths", result_path.stem, result_path)
        _set_part_a(run, has_records, has_records, has_records, has_records, has_records)
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        if dry_run:
            run.notes.append("Run is marked dry_run; empirical reporting is not trustworthy.")
            for section in PART_A_SECTIONS + PART_B_SECTIONS:
                status_map = run.part_a if section in run.part_a else run.part_b
                if section in status_map and status_map[section].status == "available":
                    status_map[section] = SectionStatus("partial", "Artifacts exist, but run is dry_run.")
        runs.append(_finalize_run(run))
    return runs


def _scan_retrieval_grounded(root: Path) -> list[RunReadiness]:
    candidates = [path for path in root.glob("Retrieval_grounded/outputs*") if path.is_dir()]
    runs = []
    for run_dir in sorted(candidates):
        metadata = run_dir / "logs" / "run_metadata.json"
        results_json = run_dir / "metrics" / "results.json"
        prediction_files = list((run_dir / "predictions").glob("predictions_*.json"))
        sddf_archive = run_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("retrieval_grounded", run_dir.name, run_dir)
        _set_part_a(run, metadata.exists(), metadata.exists(), metadata.exists(), results_json.exists(), bool(prediction_files))
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        if prediction_files and _predictions_have_truncated_context(prediction_files[0]):
            run.part_b["failure_taxonomy"] = SectionStatus("partial", "Predictions exist, but context is truncated.")
        runs.append(_finalize_run(run))
    return runs


def _scan_information_extraction(root: Path) -> list[RunReadiness]:
    outputs_dir = root / "Information Extraction" / "outputs"
    if not outputs_dir.exists():
        return []
    runs = []
    for run_dir in sorted(path for path in outputs_dir.iterdir() if path.is_dir()):
        summary = run_dir / "summary.json"
        predictions = run_dir / "per_example_predictions.jsonl"
        sddf_archive = run_dir / "sddf" / "canonical_rows.jsonl"
        run = _base_run("information_extraction", run_dir.name, run_dir)
        _set_part_a(run, summary.exists(), summary.exists(), summary.exists(), summary.exists(), predictions.exists())
        _set_part_b(run, sddf_archive.exists(), matched_possible=_count_model_families_in_archive(sddf_archive) >= 2)
        if predictions.exists() and not _ie_predictions_have_reference(predictions):
            run.part_b["matched_slm_llm_analysis"] = SectionStatus("partial", "Per-example predictions lack gold reference fields.")
            run.part_b["failure_taxonomy"] = SectionStatus("partial", "Per-example predictions lack source text or gold fields.")
        runs.append(_finalize_run(run))
    return runs


def _base_run(benchmark: str, run_id: str, path: Path) -> RunReadiness:
    return RunReadiness(
        benchmark=benchmark,
        run_id=run_id,
        path=str(path.resolve()),
        overall_status="unsupported",
        part_a={section: SectionStatus("unsupported", "Not assessed yet.") for section in PART_A_SECTIONS},
        part_b={section: SectionStatus("unsupported", "Not assessed yet.") for section in PART_B_SECTIONS},
    )


def _set_part_a(
    run: RunReadiness,
    task_definition: bool,
    dataset_sampling: bool,
    experimental_setup: bool,
    metrics: bool,
    raw_results: bool,
) -> None:
    mapping = {
        "task_definition": task_definition,
        "dataset_and_sampling": dataset_sampling,
        "experimental_setup": experimental_setup,
        "metrics": metrics,
        "raw_benchmark_results": raw_results,
    }
    for section, ok in mapping.items():
        run.part_a[section] = SectionStatus("available" if ok else "unsupported", "Artifacts present." if ok else "Required artifacts missing.")


def _set_part_b(run: RunReadiness, sddf_available: bool, matched_possible: bool) -> None:
    for section in PART_B_SECTIONS:
        if not sddf_available:
            run.part_b[section] = SectionStatus("unsupported", "No SDDF archive found for this run.")
            continue
        run.part_b[section] = SectionStatus("available", "SDDF artifacts available.")

    if sddf_available and not matched_possible:
        for section in [
            "matched_slm_llm_analysis",
            "capability_curve_tipping_point",
            "uncertainty_analysis",
            "quality_gate",
            "deployment_zones",
            "routing_policy",
        ]:
            run.part_b[section] = SectionStatus("partial", "SDDF archive exists, but no matched SLM and LLM rows were found.")


def _finalize_run(run: RunReadiness) -> RunReadiness:
    statuses = [item.status for item in list(run.part_a.values()) + list(run.part_b.values())]
    if statuses and all(status == "available" for status in statuses):
        run.overall_status = "available"
    elif "available" in statuses or "partial" in statuses:
        run.overall_status = "partial"
    else:
        run.overall_status = "unsupported"
    return run


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _json_has_key(path: Path, key: str) -> bool:
    payload = _safe_load_json(path)
    if isinstance(payload, list):
        return any(isinstance(item, dict) and key in item for item in payload)
    return isinstance(payload, dict) and key in payload


def _count_model_families_in_archive(path: Path) -> int:
    if not path.exists():
        return 0
    families: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            family = payload.get("model_family")
            if family:
                families.add(str(family))
    return len(families)


def _predictions_have_truncated_context(path: Path) -> bool:
    payload = _safe_load_json(path)
    if not isinstance(payload, list) or not payload:
        return False
    context = str(payload[0].get("context", ""))
    return context.endswith("...")


def _ie_predictions_have_reference(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
    except Exception:
        return False
    if not first_line:
        return False
    try:
        payload = json.loads(first_line)
    except Exception:
        return False
    return "reference_fields" in payload and "text" in payload
