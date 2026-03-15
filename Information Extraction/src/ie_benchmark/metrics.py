from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime

from ie_benchmark.dataset import Example
from ie_benchmark.inference import PredictionResult


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[,\.;:]", " ", value)
    return " ".join(value.split())


def normalize_amount(value: str) -> str:
    text = value.strip().lower()
    if not text:
        return ""
    text = text.replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return ""
    try:
        return f"{float(text):.2f}"
    except ValueError:
        return text


def normalize_date(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    text = text.split()[0]
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return normalize_text(text)


def normalize_field(field: str, value: str) -> str:
    if field == "total":
        return normalize_amount(value)
    if field == "date":
        return normalize_date(value)
    return normalize_text(value)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class RunMetrics:
    macro_f1: float
    micro_f1: float
    exact_match_rate: float
    schema_valid_rate: float
    hallucination_rate: float
    f1_clean: float | None
    f1_noisy: float | None
    robustness_drop: float | None
    avg_latency_seconds: float
    throughput_docs_per_min: float
    peak_gpu_memory_mb: float | None
    avg_input_tokens: float | None
    avg_output_tokens: float | None
    invalid_output_rate: float


def _compute_subset_micro_f1(rows: list[tuple[Example, PredictionResult]], target_fields: list[str]) -> float:
    if not rows:
        return 0.0
    correct = 0
    predicted = 0
    truth = 0
    for example, result in rows:
        for field in target_fields:
            predicted_value = normalize_text(result.prediction.get(field, ""))
            truth_value = normalize_field(field, example.fields.get(field, ""))
            predicted_value = normalize_field(field, result.prediction.get(field, ""))
            if predicted_value:
                predicted += 1
            if truth_value:
                truth += 1
            if predicted_value and predicted_value == truth_value:
                correct += 1
    precision = _safe_div(correct, predicted)
    recall = _safe_div(correct, truth)
    return _f1(precision, recall)


def compute_run_metrics(
    examples: list[Example],
    predictions: list[PredictionResult],
    target_fields: list[str],
) -> RunMetrics:
    by_id = {item.doc_id: item for item in examples}
    paired = [(by_id[pred.doc_id], pred) for pred in predictions if pred.doc_id in by_id]
    if not paired:
        raise ValueError("No predictions could be paired to examples.")

    total_correct = 0
    total_predicted = 0
    total_truth = 0
    macro_f1_values: list[float] = []
    exact_match_count = 0
    schema_valid_count = 0
    hallucination_count = 0
    hallucination_total = 0
    invalid_output_count = 0

    for example, result in paired:
        doc_correct = 0
        doc_predicted = 0
        doc_truth = 0
        doc_exact = True

        if result.schema_valid:
            schema_valid_count += 1
        else:
            invalid_output_count += 1

        normalized_source = normalize_text(example.text)

        for field in target_fields:
            truth_value = normalize_field(field, example.fields.get(field, ""))
            predicted_value = normalize_field(field, result.prediction.get(field, ""))

            if truth_value:
                total_truth += 1
                doc_truth += 1
            if predicted_value:
                total_predicted += 1
                doc_predicted += 1
                hallucination_total += 1
                grounding_value = normalize_text(result.prediction.get(field, ""))
                if grounding_value and grounding_value not in normalized_source:
                    hallucination_count += 1

            if predicted_value and predicted_value == truth_value:
                total_correct += 1
                doc_correct += 1
            if predicted_value != truth_value:
                doc_exact = False

        if doc_exact:
            exact_match_count += 1

        precision = _safe_div(doc_correct, doc_predicted)
        recall = _safe_div(doc_correct, doc_truth)
        macro_f1_values.append(_f1(precision, recall))

    micro_precision = _safe_div(total_correct, total_predicted)
    micro_recall = _safe_div(total_correct, total_truth)
    micro_f1 = _f1(micro_precision, micro_recall)

    clean_rows = [(example, result) for example, result in paired if example.split == "clean"]
    noisy_rows = [(example, result) for example, result in paired if example.split == "noisy"]
    f1_clean = _compute_subset_micro_f1(clean_rows, target_fields) if clean_rows else None
    f1_noisy = _compute_subset_micro_f1(noisy_rows, target_fields) if noisy_rows else None
    robustness_drop = None
    if f1_clean is not None and f1_noisy is not None:
        robustness_drop = f1_clean - f1_noisy

    latencies = [item.latency_seconds for item in predictions]
    avg_latency = sum(latencies) / len(latencies)
    throughput = len(predictions) / (sum(latencies) / 60.0) if sum(latencies) > 0 else math.inf

    peak_memory_values = [item.peak_memory_mb for item in predictions if item.peak_memory_mb is not None]
    input_tokens = [item.input_tokens for item in predictions if item.input_tokens is not None]
    output_tokens = [item.output_tokens for item in predictions if item.output_tokens is not None]

    return RunMetrics(
        macro_f1=sum(macro_f1_values) / len(macro_f1_values),
        micro_f1=micro_f1,
        exact_match_rate=exact_match_count / len(paired),
        schema_valid_rate=schema_valid_count / len(paired),
        hallucination_rate=_safe_div(hallucination_count, hallucination_total),
        f1_clean=f1_clean,
        f1_noisy=f1_noisy,
        robustness_drop=robustness_drop,
        avg_latency_seconds=avg_latency,
        throughput_docs_per_min=throughput,
        peak_gpu_memory_mb=max(peak_memory_values) if peak_memory_values else None,
        avg_input_tokens=(sum(input_tokens) / len(input_tokens)) if input_tokens else None,
        avg_output_tokens=(sum(output_tokens) / len(output_tokens)) if output_tokens else None,
        invalid_output_rate=invalid_output_count / len(paired),
    )


def aggregate_run_metrics(runs: list[RunMetrics]) -> dict[str, float | None]:
    def average(name: str) -> float | None:
        values = [getattr(run, name) for run in runs if getattr(run, name) is not None]
        if not values:
            return None
        return sum(values) / len(values)

    micro_f1_values = [run.micro_f1 for run in runs]
    micro_mean = sum(micro_f1_values) / len(micro_f1_values)
    f1_variance = sum((value - micro_mean) ** 2 for value in micro_f1_values) / len(micro_f1_values)

    return {
        "macro_f1": average("macro_f1"),
        "micro_f1": average("micro_f1"),
        "exact_match_rate": average("exact_match_rate"),
        "schema_valid_rate": average("schema_valid_rate"),
        "hallucination_rate": average("hallucination_rate"),
        "f1_clean": average("f1_clean"),
        "f1_noisy": average("f1_noisy"),
        "robustness_drop": average("robustness_drop"),
        "avg_latency_seconds": average("avg_latency_seconds"),
        "throughput_docs_per_min": average("throughput_docs_per_min"),
        "peak_gpu_memory_mb": average("peak_gpu_memory_mb"),
        "avg_input_tokens": average("avg_input_tokens"),
        "avg_output_tokens": average("avg_output_tokens"),
        "invalid_output_rate": average("invalid_output_rate"),
        "f1_variance": f1_variance,
    }


def prediction_consistency(all_runs: list[list[PredictionResult]], target_fields: list[str]) -> float | None:
    if len(all_runs) < 2:
        return None
    per_doc_runs: dict[str, list[dict[str, str]]] = {}
    for run in all_runs:
        for item in run:
            per_doc_runs.setdefault(item.doc_id, []).append(item.prediction)

    consistent = 0
    total = 0
    for run_predictions in per_doc_runs.values():
        if len(run_predictions) < 2:
            continue
        total += 1
        first = tuple(run_predictions[0].get(field, "") for field in target_fields)
        if all(tuple(pred.get(field, "") for field in target_fields) == first for pred in run_predictions[1:]):
            consistent += 1
    if total == 0:
        return None
    return consistent / total
