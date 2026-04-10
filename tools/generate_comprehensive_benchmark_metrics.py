#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generate_benchmark75_sddf import (
    BASELINE_MODEL,
    BENCHMARK_ROOT,
    CANONICAL_MODELS,
    DISPLAY_NAMES,
    SUPPORTED_TASKS,
    _build_reference_lookup,
    _dedupe_rows,
    _evaluate_row,
    _load_jsonl,
)


TASK_PRIMARY_METRIC = {
    "classification": "accuracy",
    "maths": "exact_match",
    "code_generation": "pass@1",
    "summarization": "rouge_like_match",
    "information_extraction": "field_match",
    "retrieval_grounded": "exact_match",
    "instruction_following": "constraint_satisfaction",
    "text_generation": "constraint_satisfaction",
}


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    q = max(0.0, min(1.0, q))
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _aggregate_model_metrics(rows: list[dict[str, Any]], reference_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    capabilities: list[float] = []
    risks: list[float] = []
    latencies: list[float] = []
    bin_bucket: dict[int, list[tuple[float, float, float, int]]] = defaultdict(list)
    valid_count = 0
    success_count = 0
    error_count = 0

    for row in rows:
        capability, semantic_risk, _failure = _evaluate_row(row, reference_lookup)
        capabilities.append(float(capability))
        risks.append(float(semantic_risk))
        latency = float(row.get("latency_sec", 0.0) or 0.0)
        latencies.append(latency)
        valid = 1 if row.get("valid", False) else 0
        valid_count += valid
        if str(row.get("status", "")).lower() == "success":
            success_count += 1
        if row.get("error") or str(row.get("status", "")).lower() not in {"success"}:
            error_count += 1
        bin_bucket[int(row.get("bin", 0) or 0)].append((capability, semantic_risk, latency, valid))

    n = len(rows)
    sorted_latency = sorted(latencies)
    total_latency = sum(latencies)
    per_bin = {}
    for bin_id, vals in sorted(bin_bucket.items()):
        m = len(vals)
        cap = sum(v[0] for v in vals) / m if m else 0.0
        risk = sum(v[1] for v in vals) / m if m else 0.0
        lat = sum(v[2] for v in vals) / m if m else 0.0
        valid_rate = sum(v[3] for v in vals) / m if m else 0.0
        per_bin[bin_id] = {
            "sample_count": m,
            "capability": cap,
            "semantic_risk": risk,
            "avg_latency_sec": lat,
            "valid_output_rate": valid_rate,
        }

    return {
        "sample_count": n,
        "capability": {
            "score": (sum(capabilities) / n) if n else 0.0,
            "semantic_risk": (sum(risks) / n) if n else 0.0,
            "primary_metric_score_name": "task_primary_metric",
            "valid_output_rate": (valid_count / n) if n else 0.0,
            "per_bin": per_bin,
        },
        "operational": {
            "avg_latency_sec": (sum(latencies) / n) if n else 0.0,
            "p50_latency_sec": _percentile(sorted_latency, 0.50),
            "p95_latency_sec": _percentile(sorted_latency, 0.95),
            "p99_latency_sec": _percentile(sorted_latency, 0.99),
            "throughput_qps": (n / total_latency) if total_latency > 0 else 0.0,
            "success_rate": (success_count / n) if n else 0.0,
            "error_rate": (error_count / n) if n else 0.0,
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_model_rows(task_dir: Path, model_key: str) -> list[dict[str, Any]]:
    model_dir = task_dir / model_key
    rows: list[dict[str, Any]] = []
    for split_name in ("train", "val", "test"):
        p = model_dir / f"outputs_{split_name}.jsonl"
        if p.exists():
            rows.extend(_load_jsonl(p))
    if not rows:
        legacy = model_dir / "outputs.jsonl"
        if legacy.exists():
            rows = _load_jsonl(legacy)
    return _dedupe_rows(rows)


def main() -> None:
    global_summary: dict[str, Any] = {"tasks": {}}

    for task_dir in sorted(p for p in BENCHMARK_ROOT.iterdir() if p.is_dir() and p.name in SUPPORTED_TASKS):
        task = task_dir.name
        reference_lookup = _build_reference_lookup(task)
        task_metrics = {
            "task": task,
            "primary_metric": TASK_PRIMARY_METRIC.get(task, "task_primary_metric"),
            "baseline_model": DISPLAY_NAMES.get(BASELINE_MODEL, BASELINE_MODEL),
            "models": {},
        }

        for model_key in CANONICAL_MODELS:
            rows = _load_model_rows(task_dir, model_key)
            if not rows:
                continue
            metrics = _aggregate_model_metrics(rows, reference_lookup)
            metrics["capability"]["primary_metric_score_name"] = TASK_PRIMARY_METRIC.get(task, "task_primary_metric")
            metrics["model_key"] = model_key
            metrics["display_name"] = DISPLAY_NAMES.get(model_key, model_key)
            task_metrics["models"][model_key] = metrics

        if task_metrics["models"]:
            out_path = task_dir / "benchmarking" / "comprehensive_metrics.json"
            _write_json(out_path, task_metrics)
            global_summary["tasks"][task] = {
                "metrics_path": str(out_path),
                "model_count": len(task_metrics["models"]),
            }

    summary_path = BENCHMARK_ROOT / "benchmarking" / "comprehensive_metrics_summary.json"
    _write_json(summary_path, global_summary)
    print(f"Wrote comprehensive benchmarking metrics for {len(global_summary['tasks'])} tasks.")


if __name__ == "__main__":
    main()
