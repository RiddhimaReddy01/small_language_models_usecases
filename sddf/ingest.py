from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .schema import REQUIRED_RESULT_COLUMNS


API_PROVIDER_HINTS = {"google", "gemini", "openai", "anthropic", "api", "cloud"}
LLM_NAME_HINTS = ("gemini", "gpt", "claude", "openai")


def infer_model_family(model_name: str | None, provider: str | None = None, explicit: str | None = None) -> str:
    if explicit in {"SLM", "LLM"}:
        return explicit
    provider_value = (provider or "").lower()
    name_value = (model_name or "").lower()
    if provider_value in API_PROVIDER_HINTS or any(token in name_value for token in LLM_NAME_HINTS):
        return "LLM"
    return "SLM"


def _base_row() -> dict[str, Any]:
    return {column: None for column in REQUIRED_RESULT_COLUMNS + ["input_text", "metadata"]}


def _finalize_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for column in REQUIRED_RESULT_COLUMNS + ["input_text", "metadata"]:
        if column not in df.columns:
            df[column] = None
    df["valid_output"] = df["valid_output"].fillna(0).astype(int)
    return df


def normalize_classification_results(
    results: pd.DataFrame | list[dict[str, Any]],
    model_name: str,
    run_metadata: dict[str, Any] | None = None,
) -> pd.DataFrame:
    df = results.copy() if isinstance(results, pd.DataFrame) else pd.DataFrame(results)
    rows: list[dict[str, Any]] = []
    provider = None
    if run_metadata:
        provider = run_metadata.get("provider")

    for index, row in df.iterrows():
        item = _base_row()
        dataset = row.get("dataset", run_metadata.get("dataset_name") if run_metadata else "classification")
        text = row.get("text")
        reference = row.get("true_label")
        prediction = row.get("prediction")
        valid = int(bool(row.get("is_valid")))
        primary_metric = float(valid and prediction == reference)

        item.update(
            {
                "example_id": f"{dataset}:{index}",
                "task": "classification",
                "dataset": dataset,
                "model_name": model_name,
                "model_family": infer_model_family(model_name, provider=provider),
                "prediction": prediction,
                "reference": reference,
                "primary_metric": primary_metric,
                "valid_output": valid,
                "latency_sec": float(row.get("latency", 0.0) or 0.0),
                "memory_mb": None,
                "cpu_util": None,
                "difficulty_dim": None,
                "difficulty_score": None,
                "input_text": text,
                "metadata": {
                    "status": row.get("status"),
                    "task_type": run_metadata.get("task_type") if run_metadata else None,
                },
            }
        )
        rows.append(item)

    return _finalize_rows(rows)


def normalize_text_generation_results(
    results: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metadata = metadata or {}
    model_name = metadata.get("model_name", "unknown")
    provider = metadata.get("model_type")

    for item_in in results:
        item = _base_row()
        prompt = item_in.get("prompt")
        response = item_in.get("response")
        op_metrics = item_in.get("metrics", {}).get("operational", {})
        framework = item_in.get("metrics", {}).get("framework", {})
        instruction = framework.get("instruction_following", {})
        factuality = framework.get("factuality", {})
        constraints = item_in.get("constraints") or {}

        primary_metric = instruction.get("constraint_satisfaction_rate")
        if primary_metric is None:
            primary_metric = 0.0 if item_in.get("error") else 1.0

        valid_output = 0 if item_in.get("error") else 1
        metadata_payload = {
            "task_type": item_in.get("task_type"),
            "run_id": item_in.get("run_id"),
            "task_id": item_in.get("task_id"),
            "format_compliance_rate": instruction.get("format_compliance_rate"),
            "hallucination_rate": factuality.get("hallucination_rate"),
            "constraints": constraints,
            "required_fields": _constraint_items(constraints, "required_fields"),
            "format_rules": _constraint_items(constraints, "format_rules", fallback_keys=("format", "style", "tone")),
            "content_rules": _constraint_items(constraints, "content_rules"),
            "length_rules": _constraint_items(constraints, "length_rules", fallback_keys=("length",)),
        }

        item.update(
            {
                "example_id": f"{metadata.get('task_type', 'text_generation')}:{item_in.get('task_id')}:{item_in.get('run_id', 0)}",
                "task": "text_generation",
                "dataset": metadata.get("task_type", "text_generation"),
                "model_name": model_name,
                "model_family": infer_model_family(model_name, provider=provider),
                "prediction": response,
                "reference": item_in.get("reference"),
                "primary_metric": float(primary_metric),
                "valid_output": valid_output,
                "latency_sec": float(op_metrics.get("total_time", 0.0) or 0.0),
                "memory_mb": _float_or_none(op_metrics.get("peak_ram_mb")),
                "cpu_util": None,
                "difficulty_dim": None,
                "difficulty_score": None,
                "input_text": prompt,
                "metadata": metadata_payload,
            }
        )
        rows.append(item)

    return _finalize_rows(rows)


def normalize_summarization_results(
    results: pd.DataFrame | list[dict[str, Any]],
    config: Any,
) -> pd.DataFrame:
    if isinstance(results, pd.DataFrame):
        df = results.copy()
    else:
        normalized = [asdict(item) if is_dataclass(item) else dict(item) for item in results]
        df = pd.DataFrame(normalized)

    rows: list[dict[str, Any]] = []
    model_name = config.model.model_name
    provider = getattr(config.model, "provider", None)
    dataset_name = f"{config.dataset.name}:{config.dataset.config_name}"

    for _, row in df.iterrows():
        item = _base_row()
        metadata_payload = {
            "reference_words": row.get("reference_words"),
            "summary_words": row.get("summary_words"),
            "output_tokens": row.get("output_tokens"),
            "hallucination_flag": row.get("hallucination_flag"),
            "length_violation_flag": row.get("length_violation_flag"),
            "information_loss_flag": row.get("information_loss_flag"),
            "word_limit": config.model.word_limit,
        }
        item.update(
            {
                "example_id": row.get("sample_id"),
                "task": "summarization",
                "dataset": dataset_name,
                "model_name": model_name,
                "model_family": infer_model_family(model_name, provider=provider),
                "prediction": row.get("generated_summary"),
                "reference": row.get("reference_summary"),
                "primary_metric": float(row.get("rouge_1_f1", 0.0) or 0.0),
                "valid_output": int(not bool(row.get("length_violation_flag", 0))),
                "latency_sec": float(row.get("latency_seconds", 0.0) or 0.0),
                "memory_mb": _float_or_none(row.get("memory_mb")),
                "cpu_util": None,
                "difficulty_dim": None,
                "difficulty_score": None,
                "input_text": row.get("article"),
                "metadata": metadata_payload,
            }
        )
        rows.append(item)

    return _finalize_rows(rows)


def normalize_instruction_following_results(
    results: list[dict[str, Any]],
    dataset_name: str | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model_result in results:
        model_name = model_result.get("model", "unknown")
        model_family = infer_model_family(model_name)
        responses = model_result.get("responses", [])
        for index, response_row in enumerate(responses):
            item = _base_row()
            instruction = response_row.get("instruction")
            constraints_total = response_row.get("total_constraints", 0) or 0
            constraints_satisfied = response_row.get("constraints_satisfied", 0) or 0
            primary_metric = (
                float(constraints_satisfied) / float(constraints_total)
                if constraints_total
                else float(int(bool(response_row.get("pass"))))
            )
            item.update(
                {
                    "example_id": f"{model_name}:{index}",
                    "task": "instruction_following",
                    "dataset": dataset_name or "instruction_following",
                    "model_name": model_name,
                    "model_family": model_family,
                    "prediction": response_row.get("response"),
                    "reference": {"constraints_total": constraints_total},
                    "primary_metric": primary_metric,
                    "valid_output": int(bool(response_row.get("response"))),
                    "latency_sec": float(response_row.get("latency_sec", 0.0) or 0.0),
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": None,
                    "difficulty_score": None,
                    "input_text": instruction,
                    "metadata": {
                        "output_tokens": response_row.get("output_tokens"),
                        "pass": response_row.get("pass"),
                        "required_fields": [],
                        "format_rules": [],
                        "content_rules": [],
                        "length_rules": [],
                    },
                }
            )
            rows.append(item)
    return _finalize_rows(rows)


def normalize_code_generation_results(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in results:
        item = _base_row()
        model_name = row.get("model_name") or row.get("model_label") or "unknown"
        item.update(
            {
                "example_id": row.get("task_id"),
                "task": "code_generation",
                "dataset": row.get("dataset", "code_generation"),
                "model_name": model_name,
                "model_family": infer_model_family(model_name),
                "prediction": row.get("generated_code"),
                "reference": {"entry_point": row.get("entry_point")},
                "primary_metric": float(int(bool(row.get("passed")))),
                "valid_output": int(bool(row.get("format_compliant")) and bool(row.get("generated_code"))),
                "latency_sec": float(row.get("latency_seconds", 0.0) or 0.0),
                "memory_mb": float(row.get("peak_ram_gb", 0.0) or 0.0) * 1024.0,
                "cpu_util": None,
                "difficulty_dim": None,
                "difficulty_score": None,
                "input_text": row.get("prompt"),
                "metadata": {
                    "status": row.get("status"),
                    "entry_point": row.get("entry_point"),
                    "format_ok": row.get("format_compliant"),
                    "signature_ok": row.get("signature_compliant"),
                    "instruction_ok": row.get("instruction_adherent"),
                    "unsafe": row.get("unsafe"),
                },
            }
        )
        rows.append(item)
    return _finalize_rows(rows)


def normalize_maths_results(payload: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for experiment in payload.get("experiments", []):
        model_name = experiment.get("model", "unknown")
        dataset_name = experiment.get("dataset", "maths")
        for record in experiment.get("records", []):
            base = record.get("base", {})
            item = _base_row()
            item.update(
                {
                    "example_id": base.get("request_id"),
                    "task": "maths",
                    "dataset": dataset_name,
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "prediction": base.get("prediction"),
                    "reference": base.get("gold"),
                    "primary_metric": float(int(bool(base.get("correct")))),
                    "valid_output": int(bool(base.get("prediction")) and base.get("status") == "ok"),
                    "latency_sec": float(base.get("latency", 0.0) or 0.0),
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": None,
                    "difficulty_score": None,
                    "input_text": record.get("question"),
                    "metadata": {
                        "source": record.get("source"),
                        "difficulty_label": record.get("difficulty"),
                        "repeat_metrics": record.get("repeat_metrics"),
                        "perturbation_metrics": record.get("perturbation_metrics"),
                    },
                }
            )
            rows.append(item)
    return _finalize_rows(rows)


def normalize_retrieval_grounded_predictions(
    predictions_by_model: dict[str, list[dict[str, Any]]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model_name, predictions in predictions_by_model.items():
        for row in predictions:
            item = _base_row()
            exact_match = int(str(row.get("prediction", "")).strip() == str(row.get("reference", "")).strip())
            item.update(
                {
                    "example_id": row.get("id"),
                    "task": "retrieval_grounded",
                    "dataset": "retrieval_grounded",
                    "model_name": model_name,
                    "model_family": infer_model_family(model_name),
                    "prediction": row.get("prediction"),
                    "reference": row.get("reference"),
                    "primary_metric": float(exact_match),
                    "valid_output": int(bool(row.get("prediction"))),
                    "latency_sec": float(row.get("latency_sec", 0.0) or 0.0),
                    "memory_mb": _float_or_none(row.get("memory_mb")),
                    "cpu_util": None,
                    "difficulty_dim": None,
                    "difficulty_score": None,
                    "input_text": row.get("context"),
                    "metadata": {
                        "input_tokens": row.get("input_tokens"),
                        "output_tokens": row.get("output_tokens"),
                    },
                }
            )
            rows.append(item)
    return _finalize_rows(rows)


def normalize_ie_predictions(
    predictions: list[dict[str, Any]],
    target_fields: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in predictions:
        item = _base_row()
        prediction = row.get("prediction") or {}
        reference = row.get("reference_fields") or {}
        correct = 0
        truth = 0
        predicted = 0
        for field in target_fields:
            pred_value = str(prediction.get(field, "") or "").strip()
            ref_value = str(reference.get(field, "") or "").strip()
            if pred_value:
                predicted += 1
            if ref_value:
                truth += 1
            if pred_value and pred_value == ref_value:
                correct += 1
        precision = correct / predicted if predicted else 0.0
        recall = correct / truth if truth else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        item.update(
            {
                "example_id": row.get("doc_id"),
                "task": "information_extraction",
                "dataset": row.get("split", "information_extraction"),
                "model_name": row.get("model"),
                "model_family": infer_model_family(row.get("model")),
                "prediction": prediction,
                "reference": reference,
                "primary_metric": float(f1),
                "valid_output": int(bool(row.get("schema_valid"))),
                "latency_sec": float(row.get("latency_seconds", 0.0) or 0.0),
                "memory_mb": _float_or_none((row.get("backend_metadata") or {}).get("peak_memory_mb")),
                "cpu_util": None,
                "difficulty_dim": None,
                "difficulty_score": None,
                "input_text": row.get("text"),
                "metadata": {
                    "raw_output": row.get("raw_output"),
                    "input_tokens": row.get("input_tokens"),
                    "output_tokens": row.get("output_tokens"),
                    "required_fields": list(target_fields),
                    "format_rules": ["json_schema"],
                },
            }
        )
        rows.append(item)
    return _finalize_rows(rows)


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "API", "API-managed"):
        return None
    return float(value)


def _constraint_items(
    constraints: Any,
    preferred_key: str,
    fallback_keys: tuple[str, ...] = (),
) -> list[Any]:
    if isinstance(constraints, dict):
        if preferred_key in constraints and constraints[preferred_key] is not None:
            value = constraints[preferred_key]
            return value if isinstance(value, list) else [value]
        values = []
        for key in fallback_keys:
            if key in constraints and constraints[key] is not None:
                value = constraints[key]
                values.extend(value if isinstance(value, list) else [value])
        return values
    if isinstance(constraints, list):
        return constraints
    return []
