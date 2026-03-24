from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable

import pandas as pd


def infer_model_family(model_name: str, provider: str | None = None) -> str:
    provider_name = (provider or "").lower()
    model_value = (model_name or "").lower()
    llm_markers = ("gemini", "gpt", "claude")
    if provider_name in {"google", "openai", "anthropic"} or any(marker in model_value for marker in llm_markers):
        return "LLM"
    return "SLM"


def _frame(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def normalize_classification_results(records: list[dict[str, Any]], model_name: str, run_metadata: dict[str, Any] | None = None) -> pd.DataFrame:
    normalized = []
    for index, record in enumerate(records):
        prediction = record.get("prediction")
        reference = record.get("true_label")
        normalized.append(
            {
                "example_id": record.get("id", f"classification_{index}"),
                "task": "classification",
                "dataset": record.get("dataset", "unknown"),
                "model_name": model_name,
                "model_family": infer_model_family(model_name, provider=(run_metadata or {}).get("provider")),
                "prediction": prediction,
                "reference": reference,
                "primary_metric": 1.0 if prediction == reference else 0.0,
                "valid_output": 1 if record.get("is_valid", True) else 0,
                "latency_sec": float(record.get("latency", 0.0) or 0.0),
                "input_text": record.get("text", ""),
                "metadata": run_metadata or {},
            }
        )
    return _frame(normalized)


def normalize_text_generation_results(records: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> pd.DataFrame:
    meta = metadata or {}
    normalized = []
    for index, record in enumerate(records):
        framework_metrics = ((record.get("metrics") or {}).get("framework") or {}).get("instruction_following") or {}
        operational = ((record.get("metrics") or {}).get("operational") or {})
        normalized.append(
            {
                "example_id": f"textgen_{index}",
                "task": "text_generation",
                "dataset": meta.get("task_type", "unknown"),
                "model_name": meta.get("model_name", "unknown"),
                "model_family": infer_model_family(meta.get("model_name", "unknown"), provider=meta.get("model_type")),
                "prediction": record.get("response", ""),
                "reference": record.get("reference", ""),
                "primary_metric": float(framework_metrics.get("constraint_satisfaction_rate", 0.0) or 0.0),
                "valid_output": 1,
                "latency_sec": float(operational.get("total_time", 0.0) or 0.0),
                "input_text": record.get("prompt", ""),
                "metadata": meta,
            }
        )
    return _frame(normalized)


def normalize_summarization_results(records: list[dict[str, Any]], config: SimpleNamespace) -> pd.DataFrame:
    normalized = []
    dataset_name = getattr(getattr(config, "dataset", None), "name", "unknown")
    model_name = getattr(getattr(config, "model", None), "model_name", "unknown")
    provider = getattr(getattr(config, "model", None), "provider", None)
    for index, record in enumerate(records):
        normalized.append(
            {
                "example_id": record.get("sample_id", f"summary_{index}"),
                "task": "summarization",
                "dataset": dataset_name,
                "model_name": model_name,
                "model_family": infer_model_family(model_name, provider=provider),
                "prediction": record.get("generated_summary", ""),
                "reference": record.get("reference_summary", ""),
                "primary_metric": float(record.get("rouge_1_f1", 0.0) or 0.0),
                "valid_output": 1 if not record.get("length_violation_flag", 0) else 0,
                "latency_sec": float(record.get("latency_seconds", 0.0) or 0.0),
                "input_text": record.get("article", ""),
                "metadata": {"word_limit": getattr(getattr(config, "model", None), "word_limit", None)},
            }
        )
    return _frame(normalized)


def normalize_instruction_following_results(records: list[dict[str, Any]]) -> pd.DataFrame:
    normalized = []
    for outer in records:
        model_name = outer.get("model", "unknown")
        for index, response in enumerate(outer.get("responses", [])):
            total_constraints = max(int(response.get("total_constraints", 0) or 0), 1)
            score = float(response.get("constraints_satisfied", 0) or 0) / total_constraints
            normalized.append(
                {
                    "example_id": f"if_{index}",
                    "task": "instruction_following",
                    "dataset": "instruction_following",
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "prediction": response.get("response", ""),
                    "reference": response.get("instruction", ""),
                    "primary_metric": score,
                    "valid_output": 1 if response.get("pass", False) else 0,
                    "latency_sec": float(response.get("latency_sec", 0.0) or 0.0),
                    "input_text": response.get("instruction", ""),
                    "metadata": {},
                }
            )
    return _frame(normalized)


def normalize_code_generation_results(records: list[dict[str, Any]]) -> pd.DataFrame:
    normalized = []
    for index, record in enumerate(records):
        model_name = record.get("model_name", "unknown")
        normalized.append(
            {
                "example_id": record.get("task_id", f"code_{index}"),
                "task": "code_generation",
                "dataset": record.get("dataset", "unknown"),
                "model_name": model_name,
                "model_family": infer_model_family(model_name),
                "prediction": record.get("generated_code", ""),
                "reference": record.get("entry_point", ""),
                "primary_metric": 1.0 if record.get("passed") else 0.0,
                "valid_output": 1 if record.get("format_compliant", False) else 0,
                "latency_sec": float(record.get("latency_seconds", 0.0) or 0.0),
                "input_text": record.get("prompt", ""),
                "metadata": {},
            }
        )
    return _frame(normalized)


def normalize_maths_results(payload: dict[str, Any]) -> pd.DataFrame:
    normalized = []
    for experiment in payload.get("experiments", []):
        model_name = experiment.get("model", "unknown")
        dataset = experiment.get("dataset", "unknown")
        for index, record in enumerate(experiment.get("records", [])):
            base = record.get("base", {})
            normalized.append(
                {
                    "example_id": base.get("request_id", f"maths_{index}"),
                    "task": "maths",
                    "dataset": dataset,
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "prediction": base.get("prediction", ""),
                    "reference": base.get("gold", ""),
                    "primary_metric": 1.0 if base.get("correct") else 0.0,
                    "valid_output": 1 if base.get("status") == "ok" else 0,
                    "latency_sec": float(base.get("latency", 0.0) or 0.0),
                    "input_text": record.get("question", ""),
                    "metadata": {"difficulty": record.get("difficulty"), "source": record.get("source")},
                }
            )
    return _frame(normalized)


def normalize_retrieval_grounded_predictions(payload: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    normalized = []
    for model_name, records in payload.items():
        for index, record in enumerate(records):
            normalized.append(
                {
                    "example_id": record.get("id", f"retrieval_{index}"),
                    "task": "retrieval_grounded",
                    "dataset": "retrieval_grounded",
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "prediction": record.get("prediction", ""),
                    "reference": record.get("reference", ""),
                    "primary_metric": 1.0 if record.get("prediction") == record.get("reference") else 0.0,
                    "valid_output": 1,
                    "latency_sec": float(record.get("latency_sec", 0.0) or 0.0),
                    "input_text": record.get("context", ""),
                    "metadata": {},
                }
            )
    return _frame(normalized)


def normalize_ie_predictions(records: list[dict[str, Any]], required_fields: list[str]) -> pd.DataFrame:
    normalized = []
    for index, record in enumerate(records):
        prediction = record.get("prediction", {}) or {}
        reference = record.get("reference_fields", {}) or {}
        score = 1.0 if all(prediction.get(field) == reference.get(field) for field in required_fields) else 0.0
        normalized.append(
            {
                "example_id": record.get("doc_id", f"ie_{index}"),
                "task": "information_extraction",
                "dataset": record.get("split", "unknown"),
                "model_name": record.get("model", "unknown"),
                "model_family": infer_model_family(record.get("model", "unknown")),
                "prediction": prediction,
                "reference": reference,
                "primary_metric": score,
                "valid_output": 1 if record.get("schema_valid", False) else 0,
                "latency_sec": float(record.get("latency_seconds", 0.0) or 0.0),
                "input_text": record.get("text", ""),
                "metadata": {"raw_output": record.get("raw_output", "")},
            }
        )
    return _frame(normalized)
