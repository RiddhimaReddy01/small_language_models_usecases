from __future__ import annotations

from ie_benchmark.config import load_config
from ie_benchmark.dataset import load_and_sample_dataset
from ie_benchmark.inference import build_generator
from ie_benchmark.metrics import aggregate_run_metrics, compute_run_metrics, prediction_consistency
from ie_benchmark.reporting import make_output_dir, write_csv, write_json, write_jsonl, write_markdown_table


def run_benchmark(config_path: str) -> int:
    config = load_config(config_path)
    examples = load_and_sample_dataset(config)
    output_dir = make_output_dir(config.output_dir)

    capability_rows: list[dict[str, object]] = []
    operational_rows: list[dict[str, object]] = []
    summary_payload: dict[str, object] = {
        "benchmark_name": config.benchmark_name,
        "sample_size": len(examples),
        "models": [],
    }
    prediction_dump: list[dict[str, object]] = []

    for model in config.models:
        generator = build_generator(model, config.inference)
        run_predictions = []
        run_summaries = []

        for run_idx in range(config.evaluation.runs_per_model):
            predictions = []
            for example in examples:
                result = generator.predict(example.doc_id, example.split, example.text, config.dataset.target_fields)
                predictions.append(result)
                prediction_dump.append(
                    {
                        "model": model.name,
                        "run": run_idx + 1,
                        "doc_id": result.doc_id,
                        "split": result.split,
                        "prediction": result.prediction,
                        "schema_valid": result.schema_valid,
                        "latency_seconds": result.latency_seconds,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "raw_output": result.raw_output,
                        "backend_metadata": result.backend_metadata,
                    }
                )
            run_predictions.append(predictions)
            run_summaries.append(compute_run_metrics(examples, predictions, config.dataset.target_fields))

        aggregate = aggregate_run_metrics(run_summaries)
        consistency = prediction_consistency(run_predictions, config.dataset.target_fields)

        capability_rows.append(
            {
                "Model": model.name,
                "Macro F1": aggregate["macro_f1"],
                "Micro F1": aggregate["micro_f1"],
                "Exact Match": aggregate["exact_match_rate"],
                "Schema Valid Rate": aggregate["schema_valid_rate"],
                "Hallucination Rate": aggregate["hallucination_rate"],
                "F1 Clean": aggregate["f1_clean"],
                "F1 Noisy": aggregate["f1_noisy"],
                "Robustness Drop": aggregate["robustness_drop"],
            }
        )
        operational_rows.append(
            {
                "Model": model.name,
                "Avg Latency / Doc (s)": aggregate["avg_latency_seconds"],
                "Throughput (docs/min)": aggregate["throughput_docs_per_min"],
                "Peak GPU Memory (MB)": aggregate["peak_gpu_memory_mb"],
                "Avg Input Tokens": aggregate["avg_input_tokens"],
                "Avg Output Tokens": aggregate["avg_output_tokens"],
            }
        )
        summary_payload["models"].append(
            {
                "model": model.name,
                "capability_metrics": capability_rows[-1],
                "operational_metrics": operational_rows[-1],
                "reliability_metrics": {
                    "f1_variance": aggregate["f1_variance"],
                    "prediction_consistency": consistency,
                    "invalid_output_rate": aggregate["invalid_output_rate"],
                },
            }
        )

    write_csv(output_dir / "capability_metrics.csv", capability_rows)
    write_csv(output_dir / "operational_metrics.csv", operational_rows)
    write_markdown_table(output_dir / "capability_metrics.md", capability_rows)
    write_markdown_table(output_dir / "operational_metrics.md", operational_rows)
    write_json(output_dir / "summary.json", summary_payload)
    write_jsonl(output_dir / "per_example_predictions.jsonl", prediction_dump)
    return 0
