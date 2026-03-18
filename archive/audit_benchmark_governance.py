from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
PIPELINE_REGISTRY = json.loads((REPO_ROOT / "benchmark_pipeline_registry.json").read_text(encoding="utf-8"))
GOVERNANCE_REGISTRY = json.loads((REPO_ROOT / "benchmark_governance_registry.json").read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _merge_texts(paths: list[Path]) -> str:
    return "\n".join(_read_text(path) for path in paths)


def _status(score: int, full_score: int) -> str:
    if score >= full_score:
        return "pass"
    if score > 0:
        return "partial"
    return "missing"


def _pipeline_status(benchmark_name: str) -> str:
    benchmark = next(item for item in PIPELINE_REGISTRY["benchmarks"] if item["name"] == benchmark_name)
    expected = PIPELINE_REGISTRY["canonical_stage_order"]
    actual = [stage["stage"] for stage in benchmark["stages"]]
    return "pass" if actual == expected else "missing"


def audit_benchmark(entry: dict) -> dict:
    config_paths = [REPO_ROOT / path for path in entry["config_paths"]]
    code_paths = [REPO_ROOT / path for path in entry["code_paths"]]
    config_text = _merge_texts(config_paths)
    code_text = _merge_texts(code_paths)
    combined_text = f"{config_text}\n{code_text}"

    model_spec_score = sum(
        [
            _has_any(combined_text, ["model_name", "model_id", "name", "label"]),
            _has_any(combined_text, ["params", "3.8b", "2b", "1.5b", "0.5b", "description"]),
            _has_any(combined_text, ["quantization", "load_in_4bit", "4bit", "q4"]),
            _has_any(combined_text, ["backend", "ollama", "huggingface", "google", "openai", "provider", "kind"]),
            _has_any(combined_text, ["device", "cpu", "cuda"]),
        ]
    )

    run_config_score = sum(
        [
            _has_any(combined_text, ["temperature"]),
            _has_any(combined_text, ["max_new_tokens", "max_tokens", "num_predict"]),
            _has_any(combined_text, ["seed", "random_seed"]),
            _has_any(combined_text, ["backend", "model_type", "inference", "provider"]),
        ]
    )

    dataset_governance_score = sum(
        [
            _has_any(combined_text, ["dataset", "dataset_name", "config_name", "split"]),
            _has_any(combined_text, ["sample_size", "num_articles", "num_questions", "sampling_method", "profile"]),
            _has_any(combined_text, ["source"]),
            _has_any(combined_text, ["license"]),
        ]
    )

    hardware_score = sum(
        [
            _has_any(combined_text, ["cpu", "platform", "processor"]),
            _has_any(combined_text, ["ram", "memory_mb", "peak_ram_gb", "virtual_memory"]),
            _has_any(combined_text, ["gpu", "cuda", "peak gpu memory"]),
            _has_any(combined_text, ["python_version", "sys.version"]),
            _has_any(combined_text, ["backend", "inference_backend", "model_type"]),
        ]
    )

    determinism_score = sum(
        [
            _has_any(combined_text, ["seed"]),
            _has_any(combined_text, ["random.seed", "manual_seed", "dataset_seed"]),
            _has_any(combined_text, ["torch.manual_seed", "cuda.manual_seed_all"]),
        ]
    )

    artifact_score = sum(
        [
            _has_any(combined_text, ["run_dir", "suite_dir", "make_output_dir", "timestamp"]),
            _has_any(combined_text, ["config_snapshot", "metadata_path", "manifest"]),
            _has_any(combined_text, ["predictions", "jsonl", "results.json", "raw_results"]),
            _has_any(combined_text, ["report", "metrics", "summary"]),
            _has_any(combined_text, ["hardware.json"]),
        ]
    )

    return {
        "pipeline_stages": _pipeline_status(entry["name"]),
        "model_specification": _status(model_spec_score, 5),
        "run_configuration_metadata": _status(run_config_score, 4),
        "dataset_governance": _status(dataset_governance_score, 4),
        "hardware_metadata_logging": _status(hardware_score, 5),
        "deterministic_execution": _status(determinism_score, 3),
        "run_artifact_folder": _status(artifact_score, 5),
    }


def build_report() -> dict:
    report = {"benchmarks": {}}
    for entry in GOVERNANCE_REGISTRY["benchmarks"]:
        report["benchmarks"][entry["name"]] = audit_benchmark(entry)
    return report


def render_markdown(report: dict) -> str:
    headers = [
        "Benchmark",
        "Pipeline",
        "Model Spec",
        "Run Config",
        "Dataset Gov",
        "Hardware",
        "Deterministic",
        "Artifacts",
    ]
    lines = [
        "# Benchmark Governance Audit",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for name, result in report["benchmarks"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    result["pipeline_stages"],
                    result["model_specification"],
                    result["run_configuration_metadata"],
                    result["dataset_governance"],
                    result["hardware_metadata_logging"],
                    result["deterministic_execution"],
                    result["run_artifact_folder"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Canonical metadata location",
            "",
            "- Store benchmark metadata in `results/<benchmark>/<run_id>/run_manifest.json`.",
            "- Put dataset metadata in `dataset_manifest.json` and hardware metadata in `hardware.json` in the same folder.",
            "- Keep `config_snapshot.json`, `predictions.jsonl`, `metrics.json`, `report.md`, and `logs.txt` beside the manifest.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
