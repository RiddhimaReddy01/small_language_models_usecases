from __future__ import annotations

import ast
import math
from collections import Counter, defaultdict
from statistics import mean

from .prompts import is_code_only_output
from .types import TaskRunResult


def is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def has_expected_signature(code: str, entry_point: str, starter_code: str) -> bool:
    try:
        generated_tree = ast.parse(code)
        starter_tree = ast.parse(starter_code)
    except SyntaxError:
        return False

    expected = next(
        (node for node in starter_tree.body if isinstance(node, ast.FunctionDef) and node.name == entry_point),
        None,
    )
    actual = next(
        (node for node in generated_tree.body if isinstance(node, ast.FunctionDef) and node.name == entry_point),
        None,
    )
    if expected is None or actual is None:
        return False

    expected_args = [arg.arg for arg in expected.args.args]
    actual_args = [arg.arg for arg in actual.args.args]
    return expected_args == actual_args


def format_compliance(raw_output: str, code: str) -> bool:
    normalized_code = code.strip()
    return bool(normalized_code) and is_code_only_output(raw_output) and is_valid_python(normalized_code)


def instruction_adherence(raw_output: str, code: str) -> bool:
    normalized_raw = raw_output.strip().lower()
    banned_prefixes = ("here is", "below is", "sure", "explanation", "this function")
    if any(normalized_raw.startswith(prefix) for prefix in banned_prefixes):
        return False
    return format_compliance(raw_output, code)


def self_consistency_score(codes: list[str]) -> float | None:
    normalized = [code.strip() for code in codes if code.strip()]
    if len(normalized) <= 1:
        return None
    counts = Counter(normalized)
    return max(counts.values()) / len(normalized)


def reproducibility_score(codes: list[str]) -> bool | None:
    normalized = [code.strip() for code in codes if code.strip()]
    if len(normalized) <= 1:
        return None
    return len(set(normalized)) == 1


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = math.ceil((pct / 100.0) * len(ordered)) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def summarize_results(results: list[TaskRunResult], time_budget_minutes: int) -> list[dict[str, object]]:
    grouped: dict[str, list[TaskRunResult]] = defaultdict(list)
    for result in results:
        grouped[result.model_label].append(result)

    summaries: list[dict[str, object]] = []
    for model_label, items in grouped.items():
        attempted = [item for item in items if item.attempted]
        total_attempted = len(attempted)
        if total_attempted == 0:
            continue

        completed = sum(1 for item in attempted if item.completed)
        passed = sum(1 for item in attempted if item.passed)
        syntax_errors = sum(1 for item in attempted if item.status == "syntax_error")
        runtime_failures = sum(1 for item in attempted if item.status == "runtime_failure")
        logical_failures = sum(1 for item in attempted if item.status == "logical_failure")
        unsafe = sum(1 for item in attempted if item.unsafe)

        human_attempted = sum(1 for item in attempted if item.dataset == "HumanEval")
        mbpp_attempted = sum(1 for item in attempted if item.dataset == "MBPP")

        latencies = [item.latency_seconds for item in attempted if item.latency_seconds > 0]
        throughputs = [item.tokens_per_second for item in attempted if item.tokens_per_second > 0]
        ram_values = [item.peak_ram_gb for item in attempted if item.peak_ram_gb >= 0]
        output_tokens = [item.output_tokens for item in attempted if item.output_tokens > 0]
        costs = [item.estimated_cost for item in attempted]

        consistency_values = [item.self_consistency_score for item in attempted if item.self_consistency_score is not None]
        reproducibility_values = [
            item.deterministic_reproducible for item in attempted if item.deterministic_reproducible is not None
        ]

        summary = {
            "model": model_label,
            "model_name": items[0].model_name,
            "time_budget_minutes": time_budget_minutes,
            "human_eval_attempted": human_attempted,
            "mbpp_attempted": mbpp_attempted,
            "total_attempted": total_attempted,
            "tasks_completed_in_budget": completed,
            "pass@1": passed / total_attempted,
            "syntax_error_rate": syntax_errors / total_attempted,
            "runtime_failure_rate": runtime_failures / total_attempted,
            "logical_failure_rate": logical_failures / total_attempted,
            "reliability_score": 1 - ((syntax_errors + runtime_failures + logical_failures) / total_attempted),
            "self_consistency_score": mean(consistency_values) if consistency_values else None,
            "format_compliance": sum(1 for item in attempted if item.format_compliant) / total_attempted,
            "signature_compliance": sum(1 for item in attempted if item.signature_compliant) / total_attempted,
            "instruction_adherence": sum(1 for item in attempted if item.instruction_adherent) / total_attempted,
            "deterministic_reproducibility": (
                sum(1 for flag in reproducibility_values if flag) / len(reproducibility_values)
                if reproducibility_values
                else None
            ),
            "unsafe_code_rate": unsafe / total_attempted,
            "avg_latency_seconds": mean(latencies) if latencies else 0.0,
            "p95_latency_seconds": percentile(latencies, 95) if latencies else 0.0,
            "tokens_per_second": mean(throughputs) if throughputs else 0.0,
            "peak_ram_gb": max(ram_values) if ram_values else 0.0,
            "avg_output_tokens": mean(output_tokens) if output_tokens else 0.0,
            "cost_per_request": mean(costs) if costs else 0.0,
        }
        summaries.append(summary)

    return summaries
