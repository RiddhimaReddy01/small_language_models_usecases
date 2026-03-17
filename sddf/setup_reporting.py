from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def generate_part_a_report(
    benchmark: str,
    run_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    run_root = Path(run_path)
    report_dir = Path(output_dir) if output_dir is not None else (run_root / "sddf" / "reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = _extract_part_a_payload(benchmark, run_root)
    report_md = _render_part_a_markdown(benchmark, run_root, payload)

    report_path = report_dir / "part_a_report.md"
    summary_path = report_dir / "part_a_summary.json"
    report_path.write_text(report_md, encoding="utf-8")
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"report_path": str(report_path), "summary_path": str(summary_path)}


def _extract_part_a_payload(benchmark: str, run_root: Path) -> dict[str, Any]:
    extractor = {
        "classification": _extract_classification,
        "text_generation": _extract_text_generation,
        "summarization": _extract_summarization,
        "instruction_following": _extract_instruction_following,
        "code_generation": _extract_code_generation,
        "maths": _extract_maths,
        "retrieval_grounded": _extract_retrieval_grounded,
        "information_extraction": _extract_information_extraction,
    }.get(benchmark)
    if not extractor:
        raise ValueError(f"Unsupported benchmark for Part A reporting: {benchmark}")
    return extractor(run_root)


def _extract_classification(run_root: Path) -> dict[str, Any]:
    results_dir = run_root if run_root.is_dir() else run_root.parent
    raw_files = sorted(results_dir.glob("raw_results_*.csv"))
    summary_files = sorted(results_dir.glob("metrics_summary_*.json"))
    summary = _load_json(summary_files[-1]) if summary_files else {}
    latest_raw = pd.read_csv(raw_files[-1]) if raw_files else pd.DataFrame()
    return {
        "task_definition": {"task": "classification", "datasets": list((summary.get("capability") or {}).keys())},
        "dataset_and_sampling": summary.get("metadata", {}),
        "experimental_setup": {"model": summary.get("metadata", {}).get("model"), "workers": summary.get("metadata", {}).get("workers")},
        "metrics": {"capability": summary.get("capability", {}), "operational": summary.get("operational", [])},
        "raw_benchmark_results": {
            "raw_result_file_count": len(raw_files),
            "latest_row_count": int(len(latest_raw)),
            "columns": list(latest_raw.columns),
        },
    }


def _extract_text_generation(run_root: Path) -> dict[str, Any]:
    manifest = _load_json(run_root / "suite_manifest.json")
    raw_files = [run_root / name for name in manifest.get("raw_result_files", [])]
    example_count = 0
    if raw_files and raw_files[0].exists():
        example_count = len(_load_json(raw_files[0]))
    return {
        "task_definition": {"task": "text_generation", "task_type": manifest.get("task_type")},
        "dataset_and_sampling": {"task_type": manifest.get("task_type"), "seed": manifest.get("seed"), "repeats": manifest.get("repeats")},
        "experimental_setup": {
            "resolved_models": manifest.get("resolved_models", []),
            "temperature": manifest.get("temperature"),
            "workers": manifest.get("workers"),
            "gguf_engine": manifest.get("gguf_engine"),
        },
        "metrics": {
            "benchmark_summary_path": str((run_root / "benchmark_summary.json").resolve()) if (run_root / "benchmark_summary.json").exists() else None,
            "metrics_tables_path": str((run_root / "metrics_tables.md").resolve()) if (run_root / "metrics_tables.md").exists() else None,
        },
        "raw_benchmark_results": {"raw_files": [str(path.resolve()) for path in raw_files if path.exists()], "example_count_per_run": example_count},
    }


def _extract_summarization(run_root: Path) -> dict[str, Any]:
    summary = _load_json(run_root / "summarization_summary.json")
    results_csv = run_root / "summarization_results.csv"
    results_df = pd.read_csv(results_csv) if results_csv.exists() else pd.DataFrame()
    return {
        "task_definition": {"task": "summarization", "dataset": summary.get("dataset"), "split": summary.get("split")},
        "dataset_and_sampling": summary.get("sampling", {}),
        "experimental_setup": {"model_name": summary.get("model_name"), "embedding_model": summary.get("embedding_model"), "inference_settings": summary.get("inference_settings")},
        "metrics": {"averages": summary.get("averages", {}), "reliability": summary.get("reliability", {})},
        "raw_benchmark_results": {"row_count": int(len(results_df)), "columns": list(results_df.columns)},
    }


def _extract_instruction_following(run_root: Path) -> dict[str, Any]:
    payload = _load_json(run_root)
    models = [item.get("model") for item in payload] if isinstance(payload, list) else []
    responses = sum(len(item.get("responses", [])) for item in payload) if isinstance(payload, list) else 0
    return {
        "task_definition": {"task": "instruction_following", "models": models},
        "dataset_and_sampling": {"num_models": len(models), "total_prompt_responses": responses},
        "experimental_setup": {"models": models},
        "metrics": payload,
        "raw_benchmark_results": {"response_count": responses},
    }


def _extract_code_generation(run_root: Path) -> dict[str, Any]:
    config = _load_json(run_root / "config_snapshot.json")
    summary = _load_json(run_root / "summary.json")
    task_results = list(_read_jsonl(run_root / "task_results.jsonl"))
    return {
        "task_definition": {"task": "code_generation", "datasets": sorted({row.get("dataset") for row in task_results})},
        "dataset_and_sampling": config.get("evaluation", {}),
        "experimental_setup": {"models": config.get("models", []), "generation": config.get("generation", {})},
        "metrics": summary,
        "raw_benchmark_results": {"task_result_count": len(task_results)},
    }


def _extract_maths(run_root: Path) -> dict[str, Any]:
    payload = _load_json(run_root)
    if isinstance(payload, dict) and "models" in payload:
        models = payload.get("models", {})
        datasets = set()
        for model_payload in models.values():
            for dataset in (((model_payload or {}).get("metadata") or {}).get("datasets") or []):
                datasets.add(dataset)
        return {
            "task_definition": {"task": "maths", "datasets": sorted(datasets)},
            "dataset_and_sampling": {"date": payload.get("date"), "benchmark": payload.get("benchmark"), "note": payload.get("critical_note")},
            "experimental_setup": {"models": sorted(models.keys())},
            "metrics": models,
            "raw_benchmark_results": {"model_count": len(models), "aggregate_only": True},
        }

    if isinstance(payload, dict) and "experiments" in payload:
        experiments = payload.get("experiments", [])
        return {
            "task_definition": {"task": "maths", "datasets": sorted({exp.get("dataset") for exp in experiments})},
            "dataset_and_sampling": {"seed": payload.get("seed"), "mode": payload.get("mode")},
            "experimental_setup": {"config_path": payload.get("config_path"), "models": sorted({exp.get("model") for exp in experiments})},
            "metrics": [exp.get("summary", {}) for exp in experiments],
            "raw_benchmark_results": {"experiment_count": len(experiments), "record_count": sum(len(exp.get("records", [])) for exp in experiments)},
        }

    results = payload.get("results", []) if isinstance(payload, dict) else []
    return {
        "task_definition": {"task": "maths", "datasets": sorted({exp.get("dataset") for exp in results})},
        "dataset_and_sampling": {"timestamp": payload.get("timestamp"), "mode": payload.get("mode")},
        "experimental_setup": {"model": payload.get("model"), "models": [payload.get("model")] if payload.get("model") else []},
        "metrics": [{"dataset": exp.get("dataset"), "accuracy": exp.get("accuracy"), "latency": exp.get("latency")} for exp in results],
        "raw_benchmark_results": {"experiment_count": len(results), "record_count": sum(len(exp.get("records", [])) for exp in results)},
    }


def _extract_retrieval_grounded(run_root: Path) -> dict[str, Any]:
    metadata = _load_json(run_root / "logs" / "run_metadata.json")
    results = _load_json(run_root / "metrics" / "results.json")
    prediction_files = sorted((run_root / "predictions").glob("predictions_*.json"))
    prediction_count = 0
    if prediction_files:
        prediction_count = len(_load_json(prediction_files[0]))
    return {
        "task_definition": {"task": "retrieval_grounded", "dataset": metadata.get("config", {}).get("dataset_name")},
        "dataset_and_sampling": {"num_questions": metadata.get("config", {}).get("num_questions"), "dataset_split": metadata.get("config", {}).get("dataset_split")},
        "experimental_setup": {"config": metadata.get("config", {}), "environment": metadata.get("environment", {})},
        "metrics": results,
        "raw_benchmark_results": {"prediction_files": [str(path.resolve()) for path in prediction_files], "example_count_per_prediction_file": prediction_count},
    }


def _extract_information_extraction(run_root: Path) -> dict[str, Any]:
    summary = _load_json(run_root / "summary.json")
    prediction_rows = list(_read_jsonl(run_root / "per_example_predictions.jsonl"))
    return {
        "task_definition": {"task": "information_extraction", "benchmark_name": summary.get("benchmark_name")},
        "dataset_and_sampling": {"sample_size": summary.get("sample_size")},
        "experimental_setup": {"models": [model.get("model") for model in summary.get("models", [])]},
        "metrics": summary.get("models", []),
        "raw_benchmark_results": {"prediction_row_count": len(prediction_rows)},
    }


def _render_part_a_markdown(benchmark: str, run_root: Path, payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Part A - Benchmark Setup",
            "",
            f"- Benchmark: `{benchmark}`",
            f"- Run path: `{run_root}`",
            "",
            "## Task Definition",
            "",
            _render_json_block(payload.get("task_definition", {})),
            "",
            "## Dataset and Sampling",
            "",
            _render_json_block(payload.get("dataset_and_sampling", {})),
            "",
            "## Experimental Setup",
            "",
            _render_json_block(payload.get("experimental_setup", {})),
            "",
            "## Metrics",
            "",
            _render_json_block(payload.get("metrics", {})),
            "",
            "## Raw Benchmark Results",
            "",
            _render_json_block(payload.get("raw_benchmark_results", {})),
            "",
        ]
    )


def _render_json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2) + "\n```"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)
