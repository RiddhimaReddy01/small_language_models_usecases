from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .config import load_run_config
from .dataset_loader import load_task_pool
from .metrics import (
    format_compliance,
    has_expected_signature,
    instruction_adherence,
    is_valid_python,
    reproducibility_score,
    self_consistency_score,
    summarize_results,
)
from .models import create_model_adapter
from .prompts import build_prompt
from .reporting import (
    append_result_jsonl,
    create_run_directory,
    export_combined_benchmark_tables,
    export_benchmark_tables,
    write_markdown_report,
    write_results_jsonl,
    write_summary_json,
)
from .safety import scan_code_safety
from .sandbox import PASS_MARKER, build_execution_script, execute_code
from .types import RunConfig, Task, TaskRunResult
from sddf.ingest import normalize_code_generation_results
from sddf.pipeline import run_sddf_postprocess


def _classify_execution(stdout: str, stderr: str, returncode: int, timed_out: bool) -> tuple[str, str | None]:
    if timed_out:
        return "runtime_failure", "Execution timed out."
    if returncode == 0 and PASS_MARKER in stdout:
        return "passed", None
    if "AssertionError" in stderr:
        return "logical_failure", "Unit tests failed."
    if returncode != 0:
        return "runtime_failure", stderr.strip() or "Execution failed."
    return "runtime_failure", "Execution did not report success."


def _evaluate_task(model_label: str, model_name: str, adapter, task: Task, run_config: RunConfig) -> TaskRunResult:
    prompt = build_prompt(task, variant=run_config.evaluation.prompt_variant)

    primary_generation = adapter.generate(prompt)
    extra_codes = [primary_generation.code]

    for _ in range(max(0, run_config.evaluation.generations_per_task - 1)):
        extra_codes.append(adapter.generate(prompt).code)

    repro_codes = [primary_generation.code]
    for _ in range(max(0, run_config.evaluation.reproducibility_retries)):
        repro_codes.append(adapter.generate(prompt).code)

    format_ok = format_compliance(primary_generation.raw_text, primary_generation.code)
    signature_ok = has_expected_signature(primary_generation.code, task.entry_point, task.starter_code)
    adherent = instruction_adherence(primary_generation.raw_text, primary_generation.code)

    if not is_valid_python(primary_generation.code):
        return TaskRunResult(
            model_label=model_label,
            model_name=model_name,
            dataset=task.dataset,
            task_id=task.task_id,
            attempted=True,
            completed=True,
            passed=False,
            status="syntax_error",
            prompt=prompt,
            prompt_variant=run_config.evaluation.prompt_variant,
            entry_point=task.entry_point,
            raw_output=primary_generation.raw_text,
            generated_code=primary_generation.code,
            latency_seconds=primary_generation.latency_seconds,
            tokens_per_second=primary_generation.tokens_per_second,
            output_tokens=primary_generation.output_tokens,
            input_tokens=primary_generation.input_tokens,
            estimated_cost=primary_generation.output_cost,
            peak_ram_gb=0.0,
            format_compliant=format_ok,
            signature_compliant=signature_ok,
            instruction_adherent=adherent,
            deterministic_reproducible=reproducibility_score(repro_codes),
            self_consistency_score=self_consistency_score(extra_codes),
            unsafe=False,
            error_message="Generated code is not valid Python.",
        )

    safety = scan_code_safety(
        primary_generation.code,
        blocked_imports=run_config.evaluation.blocked_imports,
        blocked_calls=run_config.evaluation.blocked_calls,
    )
    if not safety.is_safe:
        return TaskRunResult(
            model_label=model_label,
            model_name=model_name,
            dataset=task.dataset,
            task_id=task.task_id,
            attempted=True,
            completed=True,
            passed=False,
            status="unsafe_code",
            prompt=prompt,
            prompt_variant=run_config.evaluation.prompt_variant,
            entry_point=task.entry_point,
            raw_output=primary_generation.raw_text,
            generated_code=primary_generation.code,
            latency_seconds=primary_generation.latency_seconds,
            tokens_per_second=primary_generation.tokens_per_second,
            output_tokens=primary_generation.output_tokens,
            input_tokens=primary_generation.input_tokens,
            estimated_cost=primary_generation.output_cost,
            peak_ram_gb=0.0,
            format_compliant=format_ok,
            signature_compliant=signature_ok,
            instruction_adherent=adherent,
            deterministic_reproducible=reproducibility_score(repro_codes),
            self_consistency_score=self_consistency_score(extra_codes),
            unsafe=True,
            unsafe_reasons=safety.reasons,
            error_message="Generated code was blocked by the safety policy.",
        )

    script = build_execution_script(task.dataset, primary_generation.code, task.test_code, task.entry_point)
    execution = execute_code(script, timeout_seconds=run_config.evaluation.execution_timeout_seconds)
    status, error_message = _classify_execution(
        stdout=str(execution["stdout"]),
        stderr=str(execution["stderr"]),
        returncode=int(execution["returncode"]),
        timed_out=bool(execution["timeout"]),
    )

    return TaskRunResult(
        model_label=model_label,
        model_name=model_name,
        dataset=task.dataset,
        task_id=task.task_id,
        attempted=True,
        completed=True,
        passed=status == "passed",
        status=status,
        prompt=prompt,
        prompt_variant=run_config.evaluation.prompt_variant,
        entry_point=task.entry_point,
        raw_output=primary_generation.raw_text,
        generated_code=primary_generation.code,
        latency_seconds=primary_generation.latency_seconds + float(execution["elapsed_seconds"]),
        tokens_per_second=primary_generation.tokens_per_second,
        output_tokens=primary_generation.output_tokens,
        input_tokens=primary_generation.input_tokens,
        estimated_cost=primary_generation.output_cost,
        peak_ram_gb=float(execution["peak_ram_gb"]),
        format_compliant=format_ok,
        signature_compliant=signature_ok,
        instruction_adherent=adherent,
        deterministic_reproducible=reproducibility_score(repro_codes),
        self_consistency_score=self_consistency_score(extra_codes),
        unsafe=False,
        error_message=error_message,
    )


def run_evaluation(
    run_config: RunConfig,
    output_dir: str | Path,
    *,
    benchmark_output_dir: str | Path | None = None,
    source_config_path: str | Path | None = None,
) -> dict[str, object]:
    task_pool = load_task_pool(
        human_eval_limit=run_config.evaluation.human_eval_sample,
        mbpp_limit=run_config.evaluation.mbpp_sample,
        seed=run_config.evaluation.seed,
    )
    run_dir = create_run_directory(output_dir)
    results_path = run_dir / "task_results.jsonl"
    summary_path = run_dir / "summary.json"
    report_path = run_dir / "report.md"
    config_snapshot_path = run_dir / "config_snapshot.json"

    results_path.write_text("", encoding="utf-8")
    config_snapshot_path.write_text(
        json.dumps(
            {
                "evaluation": asdict(run_config.evaluation),
                "generation": asdict(run_config.generation),
                "models": [asdict(model) for model in run_config.models],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    results: list[TaskRunResult] = []
    for model_spec in run_config.models:
        adapter = create_model_adapter(model_spec, run_config.generation)
        deadline = time.perf_counter() + (run_config.evaluation.time_budget_minutes * 60)

        for task in task_pool:
            if time.perf_counter() >= deadline:
                break

            try:
                result = _evaluate_task(model_spec.label, model_spec.model_name, adapter, task, run_config)
            except Exception as exc:  # pragma: no cover - runtime integration
                prompt = build_prompt(task, variant=run_config.evaluation.prompt_variant)
                result = TaskRunResult(
                    model_label=model_spec.label,
                    model_name=model_spec.model_name,
                    dataset=task.dataset,
                    task_id=task.task_id,
                    attempted=True,
                    completed=False,
                    passed=False,
                    status="runtime_failure",
                    prompt=prompt,
                    prompt_variant=run_config.evaluation.prompt_variant,
                    entry_point=task.entry_point,
                    raw_output="",
                    generated_code="",
                    latency_seconds=0.0,
                    tokens_per_second=0.0,
                    output_tokens=0,
                    input_tokens=0,
                    estimated_cost=0.0,
                    peak_ram_gb=0.0,
                    format_compliant=False,
                    signature_compliant=False,
                    instruction_adherent=False,
                    deterministic_reproducible=None,
                    self_consistency_score=None,
                    unsafe=False,
                    error_message=str(exc),
                )
            results.append(result)
            append_result_jsonl(result, results_path)
            summaries = summarize_results(results, time_budget_minutes=run_config.evaluation.time_budget_minutes)
            write_summary_json(summaries, summary_path)
            write_markdown_report(summaries, report_path)

    summaries = summarize_results(results, time_budget_minutes=run_config.evaluation.time_budget_minutes)
    write_results_jsonl(results, results_path)
    write_summary_json(summaries, summary_path)
    write_markdown_report(summaries, report_path)
    sddf_rows = normalize_code_generation_results([result.to_dict() for result in results])
    run_sddf_postprocess(sddf_rows, task="code_generation", output_dir=run_dir)

    benchmark_dir = (
        Path(benchmark_output_dir)
        if benchmark_output_dir is not None
        else Path(output_dir).resolve().parent / "benchmarks"
    )
    benchmark_export = export_benchmark_tables(
        run_dir,
        benchmark_dir,
        source_config_path=source_config_path,
    )
    return {"run_dir": str(run_dir), "summary": summaries, "benchmark_export": benchmark_export}


def build_run_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a time-bounded code generation evaluation.")
    parser.add_argument("--config", required=True, help="Path to a JSON or YAML config file.")
    parser.add_argument(
        "--output-dir",
        default="runs",
        help="Directory where run artifacts will be written.",
    )
    return parser


def build_export_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export curated benchmark tables from an existing run.")
    parser.add_argument("--run-dir", required=True, help="Path to a completed run directory.")
    parser.add_argument(
        "--output-dir",
        default="benchmarks",
        help="Directory where curated benchmark artifacts will be written.",
    )
    parser.add_argument(
        "--source-config",
        default=None,
        help="Optional original config path to record in the benchmark manifest.",
    )
    return parser


def build_export_combined_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export curated benchmark tables from multiple runs.")
    parser.add_argument(
        "--run-dir",
        action="append",
        required=True,
        dest="run_dirs",
        help="Path to a completed run directory. Pass multiple times to merge runs.",
    )
    parser.add_argument(
        "--source-config",
        action="append",
        default=None,
        dest="source_configs",
        help="Optional original config path matching each --run-dir in order.",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks",
        help="Directory where curated benchmark artifacts will be written.",
    )
    parser.add_argument(
        "--deprecate-on-rate-limit",
        action="store_true",
        help="Skip runs that contain rate limit errors and record them as deprecated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = list(argv if argv is not None else sys.argv[1:])

    if args_list and args_list[0] == "export-tables":
        parser = build_export_arg_parser()
        args = parser.parse_args(args_list[1:])
        outcome = export_benchmark_tables(args.run_dir, args.output_dir, source_config_path=args.source_config)
        print(f"Curated benchmark tables written to {outcome['tables_dir']}")
        return 0

    if args_list and args_list[0] == "export-combined-tables":
        parser = build_export_combined_arg_parser()
        args = parser.parse_args(args_list[1:])
        outcome = export_combined_benchmark_tables(
            args.run_dirs,
            args.output_dir,
            source_config_paths=args.source_configs,
            deprecate_on_rate_limit=args.deprecate_on_rate_limit,
        )
        print(f"Curated benchmark tables written to {outcome['tables_dir']}")
        return 0

    if args_list and args_list[0] == "run":
        args_list = args_list[1:]

    parser = build_run_arg_parser()
    args = parser.parse_args(args_list)

    run_config = load_run_config(args.config)
    outcome = run_evaluation(
        run_config,
        args.output_dir,
        source_config_path=args.config,
    )
    print(f"Run completed. Artifacts written to {outcome['run_dir']}")
    return 0
