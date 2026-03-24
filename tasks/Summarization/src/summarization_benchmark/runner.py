from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

import pandas as pd
import psutil
import torch
from tqdm import tqdm

from sddf.ingest import normalize_summarization_results
from sddf.pipeline import run_sddf_postprocess

from summarization_benchmark.config import BenchmarkConfig
from summarization_benchmark.data import load_and_filter_samples
from summarization_benchmark.inference import generate_summary, load_model_components
from summarization_benchmark.metrics import MetricSuite


@dataclass
class ExampleResult:
    sample_id: str
    article_words: int
    reference_words: int
    summary_words: int
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    tokens_per_second: float
    memory_mb: float
    rouge_1_f1: float
    rouge_2_f1: float
    rouge_l_f1: float
    semantic_similarity: float
    compression_ratio: float
    hallucination_flag: int
    length_violation_flag: int
    information_loss_flag: int
    raw_response_text: str
    generated_summary: str
    reference_summary: str
    article: str


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def aggregate_results(config: BenchmarkConfig, results: list[ExampleResult]) -> dict:
    df = pd.DataFrame(asdict(result) for result in results)
    return {
        "model_name": config.model.model_name,
        "embedding_model": config.model.embedding_model,
        "dataset": f"{config.dataset.name}:{config.dataset.config_name}",
        "split": config.dataset.split,
        "num_articles": len(results),
        "sampling": {
            "num_articles": config.dataset.num_articles,
            "max_article_tokens": config.dataset.max_article_tokens,
            "seed": config.dataset.seed,
        },
        "prompt_template": config.prompt.template,
        "inference_settings": {
            "temperature": config.model.temperature,
            "top_p": config.model.top_p,
            "max_new_tokens": config.model.max_new_tokens,
            "sampling_enabled": config.model.do_sample,
        },
        "averages": {
            "rouge_1_f1": mean(df["rouge_1_f1"]),
            "rouge_2_f1": mean(df["rouge_2_f1"]),
            "rouge_l_f1": mean(df["rouge_l_f1"]),
            "semantic_similarity": mean(df["semantic_similarity"]),
            "compression_ratio": mean(df["compression_ratio"]),
            "latency_seconds": mean(df["latency_seconds"]),
            "tokens_per_second": mean(df["tokens_per_second"]),
            "memory_mb": mean(df["memory_mb"]),
            "input_tokens": mean(df["input_tokens"]),
        },
        "reliability": {
            "hallucination_rate": mean(df["hallucination_flag"]),
            "length_violation_rate": mean(df["length_violation_flag"]),
            "information_loss_rate": mean(df["information_loss_flag"]),
        },
    }


def format_metric(value: float | int | str | None, decimals: int = 4, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "N/A"
        return f"{value:.{decimals}f}{suffix}"
    return f"{value}{suffix}"


def build_metrics_tables(summary: dict) -> str:
    averages = summary.get("averages", {})
    reliability = summary.get("reliability", {})
    article_count = summary.get("num_articles", summary.get("completed_articles", "N/A"))
    wall_time = "N/A"
    if "latency_seconds" in averages and isinstance(article_count, int):
        latency = averages["latency_seconds"]
        if isinstance(latency, (int, float)) and not math.isnan(latency):
            wall_time = f"~{latency * article_count:.1f} s"
    memory_value = averages.get("memory_mb")
    memory_display = "API-managed" if memory_value is None or (isinstance(memory_value, float) and math.isnan(memory_value)) else format_metric(memory_value, decimals=2, suffix=" MB")

    lines = [
        "# Summarization Results Tables",
        "",
        "## Capability Metrics Results",
        "",
        "| Model | Articles | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Semantic Similarity | Compression Ratio | Hallucination Rate | Length Violation Rate | Information Loss Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| `{summary['model_name']}` | {article_count} | "
            f"{format_metric(averages.get('rouge_1_f1'))} | "
            f"{format_metric(averages.get('rouge_2_f1'))} | "
            f"{format_metric(averages.get('rouge_l_f1'))} | "
            f"{format_metric(averages.get('semantic_similarity'))} | "
            f"{format_metric(averages.get('compression_ratio'))} | "
            f"{format_metric(reliability.get('hallucination_rate'))} | "
            f"{format_metric(reliability.get('length_violation_rate'))} | "
            f"{format_metric(reliability.get('information_loss_rate'))} |"
        ),
        "",
        "## Operational Metrics Results",
        "",
        "| Model | Articles | Avg Latency / Article | Throughput | Avg Memory Usage | Avg Input Tokens | End-to-End Wall Time |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| `{summary['model_name']}` | {article_count} | "
            f"{format_metric(averages.get('latency_seconds'), suffix=' s')} | "
            f"{format_metric(averages.get('tokens_per_second'), suffix=' tokens/s')} | "
            f"{memory_display} | "
            f"{format_metric(averages.get('input_tokens'), decimals=2)} | "
            f"{wall_time} |"
        ),
    ]
    if summary.get("status") == "partial":
        lines.extend(["", "## Notes", "", "- This file was generated from a partial run."])
    return "\n".join(lines) + "\n"


def save_metrics_tables(summary: dict, output_dir: Path, partial: bool = False) -> Path:
    filename = "summarization_metrics_tables_partial.md" if partial else "summarization_metrics_tables.md"
    table_path = output_dir / filename
    table_path.write_text(build_metrics_tables(summary), encoding="utf-8")
    return table_path


def save_outputs(config: BenchmarkConfig, results: list[ExampleResult], summary: dict) -> tuple[Path, Path, Path]:
    output_dir = Path(config.output.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "summarization_results.csv"
    summary_path = output_dir / "summarization_summary.json"

    pd.DataFrame(asdict(result) for result in results).to_csv(results_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    tables_path = save_metrics_tables(summary, output_dir)
    sddf_rows = normalize_summarization_results(results, config)
    run_sddf_postprocess(sddf_rows, task="summarization", output_dir=output_dir)
    return results_path, summary_path, tables_path


def save_partial_outputs(config: BenchmarkConfig, results: list[ExampleResult]) -> tuple[Path, Path, Path]:
    output_dir = Path(config.output.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "summarization_results_partial.csv"
    summary_path = output_dir / "summarization_summary_partial.json"

    df = pd.DataFrame(asdict(result) for result in results)
    df.to_csv(results_path, index=False)

    partial_summary = {
        "model_name": config.model.model_name,
        "status": "partial",
        "completed_articles": len(results),
        "dataset": f"{config.dataset.name}:{config.dataset.config_name}",
    }
    if len(results) > 0:
        partial_summary["averages"] = {
            "rouge_1_f1": mean(df["rouge_1_f1"]),
            "rouge_2_f1": mean(df["rouge_2_f1"]),
            "rouge_l_f1": mean(df["rouge_l_f1"]),
            "semantic_similarity": mean(df["semantic_similarity"]),
            "compression_ratio": mean(df["compression_ratio"]),
            "latency_seconds": mean(df["latency_seconds"]),
            "tokens_per_second": mean(df["tokens_per_second"]),
            "input_tokens": mean(df["input_tokens"]),
        }
        partial_summary["reliability"] = {
            "hallucination_rate": mean(df["hallucination_flag"]),
            "length_violation_rate": mean(df["length_violation_flag"]),
            "information_loss_rate": mean(df["information_loss_flag"]),
        }
    summary_path.write_text(json.dumps(partial_summary, indent=2), encoding="utf-8")
    tables_path = save_metrics_tables(partial_summary, output_dir, partial=True)
    return results_path, summary_path, tables_path


def run_benchmark(config: BenchmarkConfig) -> tuple[dict, Path, Path, Path]:
    set_seed(config.dataset.seed)
    tokenizer, model = load_model_components(config.model)
    samples = load_and_filter_samples(config.dataset, tokenizer)
    metric_suite = MetricSuite(config.model.embedding_model)
    process = psutil.Process()

    results: list[ExampleResult] = []
    try:
        for sample in tqdm(samples, desc="Evaluating"):
            generation = generate_summary(
                article=sample["article"],
                tokenizer=tokenizer,
                model=model,
                model_config=config.model,
                prompt_config=config.prompt,
                process=process,
            )
            metric_values = metric_suite.score(
                article=sample["article"],
                reference=sample["reference"],
                summary=generation["generated_summary"],
                word_limit=config.model.word_limit,
            )
            results.append(
                ExampleResult(
                    sample_id=sample["id"],
                    input_tokens=sample["input_tokens"],
                    output_tokens=generation["output_tokens"],
                    latency_seconds=generation["latency_seconds"],
                    tokens_per_second=generation["tokens_per_second"],
                    memory_mb=generation["memory_mb"],
                    raw_response_text=generation["raw_response_text"],
                    generated_summary=generation["generated_summary"],
                    reference_summary=sample["reference"],
                    article=sample["article"],
                    **metric_values,
                )
            )
            save_partial_outputs(config, results)
    except Exception:
        if results:
            save_partial_outputs(config, results)
        raise

    summary = aggregate_results(config, results)
    results_path, summary_path, tables_path = save_outputs(config, results, summary)
    return summary, results_path, summary_path, tables_path
