import json
import os
import shutil
from collections import defaultdict


REPORT_FILES = {
    "summary_json": "benchmark_summary.json",
    "tables_md": "metrics_tables.md",
    "comparison_md": "model_comparison.md",
}
SKIP_JSON_FILES = {
    "latest_report_manifest.json",
    "suite_manifest.json",
    "models_config_snapshot.json",
}


def _safe_mean(values):
    numeric = [value for value in values if isinstance(value, (int, float))]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _format_num(value, digits=4):
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _markdown_table(headers, rows):
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join(["---"] * len(headers)) + " |"
    lines = [header, divider]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _infer_model_name(result_rows, fallback_name):
    for row in result_rows:
        model_name = row.get("model_name") or row.get("model")
        if model_name:
            return str(model_name)

    responses = [row.get("response", "") for row in result_rows if isinstance(row, dict)]
    if responses and all(str(response).startswith("Mock response for:") for response in responses if response):
        return "mock"
    return fallback_name


def load_results_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    raise ValueError(f"Unsupported results format in {path}")


def summarize_results(result_rows, fallback_name="unknown"):
    model_name = _infer_model_name(result_rows, fallback_name)
    total_tasks = len(result_rows)
    successful = [row for row in result_rows if "error" not in row]
    failed = [row for row in result_rows if "error" in row]

    op_rows = [row.get("metrics", {}).get("operational", {}) for row in successful]
    fw_rows = [row.get("metrics", {}).get("framework", {}) for row in successful]
    instruction = [row.get("instruction_following", {}) for row in fw_rows]
    quality = [row.get("generation_quality", {}) for row in fw_rows]
    factuality = [row.get("factuality", {}) for row in fw_rows]
    safety = [row.get("safety", {}) for row in fw_rows]

    return {
        "model": model_name,
        "total_tasks": total_tasks,
        "successful_tasks": len(successful),
        "failed_tasks": len(failed),
        "success_rate": (len(successful) / total_tasks) if total_tasks else 0.0,
        "failure_rate": (len(failed) / total_tasks) if total_tasks else 0.0,
        "avg_constraint_satisfaction_rate": _safe_mean(
            [row.get("constraint_satisfaction_rate") for row in instruction]
        ),
        "avg_format_compliance_rate": _safe_mean(
            [row.get("format_compliance_rate") for row in instruction]
        ),
        "avg_rouge1": _safe_mean([row.get("rouge_rouge1") for row in quality]),
        "avg_rouge2": _safe_mean([row.get("rouge_rouge2") for row in quality]),
        "avg_rougeL": _safe_mean([row.get("rouge_rougeL") for row in quality]),
        "avg_bert_score_f1": _safe_mean([row.get("bert_score_f1") for row in quality]),
        "avg_hallucination_rate": _safe_mean(
            [row.get("hallucination_rate") for row in factuality]
        ),
        "avg_unsupported_claim_count": _safe_mean(
            [row.get("unsupported_claim_count") for row in factuality]
        ),
        "avg_unsafe_response_rate": _safe_mean(
            [row.get("unsafe_response_rate") for row in safety]
        ),
        "avg_refusal_rate": _safe_mean([row.get("refusal_rate") for row in safety]),
        "avg_ttft": _safe_mean([row.get("ttft") for row in op_rows]),
        "avg_total_time": _safe_mean([row.get("total_time") for row in op_rows]),
        "avg_tokens_generated": _safe_mean([row.get("tokens_generated") for row in op_rows]),
        "avg_tps": _safe_mean([row.get("tps") for row in op_rows]),
        "avg_peak_ram_mb": _safe_mean([row.get("peak_ram_mb") for row in op_rows]),
        "avg_ram_delta_mb": _safe_mean([row.get("ram_delta_mb") for row in op_rows]),
        "avg_model_load_time": _safe_mean([row.get("model_load_time") for row in op_rows]),
        "avg_cost_usd": _safe_mean([row.get("cost_usd") for row in op_rows]),
        "total_cost_usd": sum(
            row.get("cost_usd", 0.0) for row in op_rows if isinstance(row.get("cost_usd"), (int, float))
        ),
    }


def render_tables(summaries):
    capability_headers = [
        "Model",
        "Total Tasks",
        "Success Rate",
        "Constraint Satisfaction",
        "Format Compliance",
        "ROUGE-1",
        "ROUGE-2",
        "ROUGE-L",
        "BERTScore F1",
        "Refusal Rate",
    ]
    capability_rows = []
    for item in summaries:
        capability_rows.append([
            item["model"],
            str(item["total_tasks"]),
            _format_num(item["success_rate"]),
            _format_num(item["avg_constraint_satisfaction_rate"]),
            _format_num(item["avg_format_compliance_rate"]),
            _format_num(item["avg_rouge1"]),
            _format_num(item["avg_rouge2"]),
            _format_num(item["avg_rougeL"]),
            _format_num(item["avg_bert_score_f1"]),
            _format_num(item["avg_refusal_rate"]),
        ])

    operational_headers = [
        "Model",
        "Successful Tasks",
        "Failed Tasks",
        "Avg TTFT (s)",
        "Avg Total Time (s)",
        "Avg Tokens",
        "Avg TPS",
        "Avg Peak RAM MB",
        "Avg Load Time (s)",
        "Total Cost USD",
    ]
    operational_rows = []
    for item in summaries:
        operational_rows.append([
            item["model"],
            str(item["successful_tasks"]),
            str(item["failed_tasks"]),
            _format_num(item["avg_ttft"]),
            _format_num(item["avg_total_time"]),
            _format_num(item["avg_tokens_generated"]),
            _format_num(item["avg_tps"]),
            _format_num(item["avg_peak_ram_mb"]),
            _format_num(item["avg_model_load_time"]),
            _format_num(item["total_cost_usd"]),
        ])

    return "\n".join([
        "# Metrics Tables",
        "",
        "## Capability Metrics",
        "",
        _markdown_table(capability_headers, capability_rows),
        "",
        "## Operational Metrics",
        "",
        _markdown_table(operational_headers, operational_rows),
        "",
    ])


def render_model_comparison(summaries):
    sorted_summaries = sorted(summaries, key=lambda item: item["success_rate"], reverse=True)
    lines = ["# Model Comparison", ""]
    if sorted_summaries:
        best = sorted_summaries[0]
        lines.extend([
            f"Best model by success rate: `{best['model']}`",
            "",
            "## Capability Metrics",
            "",
        ])
    lines.append(render_tables(sorted_summaries).split("## Capability Metrics", 1)[1].strip())
    lines.append("")
    return "\n".join(lines)


def generate_reports(results_dir="results", input_files=None):
    results_dir = os.path.abspath(results_dir)
    os.makedirs(results_dir, exist_ok=True)
    if input_files is None:
        candidate_files = sorted(
            file_name for file_name in os.listdir(results_dir)
            if (
                file_name.endswith(".json")
                and file_name not in REPORT_FILES.values()
                and file_name not in SKIP_JSON_FILES
                and not file_name.endswith("_metadata.json")
            )
        )
    else:
        candidate_files = [
            file_name for file_name in input_files
            if (
                file_name.endswith(".json")
                and file_name not in REPORT_FILES.values()
                and file_name not in SKIP_JSON_FILES
                and not file_name.endswith("_metadata.json")
            )
        ]

    if not candidate_files:
        raise FileNotFoundError(f"No raw result JSON files found in {results_dir}")

    grouped = defaultdict(list)
    source_files = {}
    for file_name in candidate_files:
        path = os.path.join(results_dir, file_name)
        try:
            rows = load_results_file(path)
        except ValueError:
            continue
        fallback_name = os.path.splitext(file_name)[0]
        summary = summarize_results(rows, fallback_name=fallback_name)
        grouped[summary["model"]].append(summary)
        source_files.setdefault(summary["model"], []).append(file_name)

    if not grouped:
        raise FileNotFoundError(f"No raw result JSON files found in {results_dir}")

    merged_summaries = []
    for model_name, summaries in grouped.items():
        merged = {"model": model_name}
        keys = [key for key in summaries[0] if key != "model"]
        for key in keys:
            values = [item[key] for item in summaries]
            if key in {"total_tasks", "successful_tasks", "failed_tasks"}:
                merged[key] = sum(values)
            else:
                merged[key] = _safe_mean(values)
        merged["source_files"] = source_files[model_name]
        merged_summaries.append(merged)

    merged_summaries.sort(key=lambda item: item["success_rate"], reverse=True)

    summary_path = os.path.join(results_dir, REPORT_FILES["summary_json"])
    tables_path = os.path.join(results_dir, REPORT_FILES["tables_md"])
    comparison_path = os.path.join(results_dir, REPORT_FILES["comparison_md"])

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(merged_summaries, handle, indent=2)
    with open(tables_path, "w", encoding="utf-8") as handle:
        handle.write(render_tables(merged_summaries))
    with open(comparison_path, "w", encoding="utf-8") as handle:
        handle.write(render_model_comparison(merged_summaries))

    return {
        "summary_path": summary_path,
        "tables_path": tables_path,
        "comparison_path": comparison_path,
        "models": [item["model"] for item in merged_summaries],
    }


def publish_report_bundle(report_outputs, publish_dir, extra_manifest=None):
    publish_dir = os.path.abspath(publish_dir)
    os.makedirs(publish_dir, exist_ok=True)

    published = {}
    for key, filename in REPORT_FILES.items():
        source_path = report_outputs[key.replace("_json", "_path")] if key == "summary_json" else None
        if key == "tables_md":
            source_path = report_outputs["tables_path"]
        elif key == "comparison_md":
            source_path = report_outputs["comparison_path"]
        elif key == "summary_json":
            source_path = report_outputs["summary_path"]

        target_path = os.path.join(publish_dir, filename)
        shutil.copyfile(source_path, target_path)
        published[key] = target_path

    latest_manifest_path = os.path.join(publish_dir, "latest_report_manifest.json")
    with open(latest_manifest_path, "w", encoding="utf-8") as handle:
        manifest = {
            "models": report_outputs.get("models", []),
            "summary_path": published["summary_json"],
            "tables_path": published["tables_md"],
            "comparison_path": published["comparison_md"],
        }
        if extra_manifest:
            manifest.update(extra_manifest)
        json.dump(manifest, handle, indent=2)
    published["manifest"] = latest_manifest_path
    return published
