import argparse
import json
import os
from datetime import datetime
from types import SimpleNamespace

from run_benchmark import run_benchmark
from scripts.model_registry import file_metadata, list_models, resolve_model_config, resolve_model_path
from scripts.reporting import generate_reports, publish_report_bundle


def build_parser():
    parser = argparse.ArgumentParser(description="Run text-generation benchmarks for one or more configured models")
    parser.add_argument("--models_config", type=str, default="configs/models.json", help="Path to the model registry JSON")
    parser.add_argument("--models", nargs="*", help="Optional subset of model names from the registry")
    parser.add_argument("--task_type", type=str, default="samples", help="Task type to benchmark")
    parser.add_argument("--output_root", type=str, default="results/runs", help="Root directory for timestamped benchmark suites")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers per model")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode for each configured model")
    parser.add_argument("--sample_size", type=int, default=None, help="Number of tasks to sample")
    parser.add_argument("--temperature", type=float, default=0.7, help="Inference temperature")
    parser.add_argument("--model_type", type=str, default="gguf", choices=["gguf", "ollama", "google", "openai"], help="Backend type")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repeated runs per task")
    parser.add_argument("--perturb", action="store_true", help="Enable prompt perturbation")
    parser.add_argument("--api_key", type=str, help="API key for cloud models")
    parser.add_argument("--gguf_engine", type=str, default="llama_cpp", choices=["llama_cpp", "llama_cli"], help="Inference engine for GGUF models")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for sampling and prompt perturbation")
    parser.add_argument("--cloud_request_delay_s", type=float, default=0.0, help="Delay before each cloud API request")
    parser.add_argument("--cloud_max_retries", type=int, default=0, help="Maximum retries for transient cloud API failures")
    parser.add_argument("--cloud_backoff_base_s", type=float, default=2.0, help="Base backoff in seconds for cloud API retries")
    parser.add_argument("--cloud_timeout_s", type=int, default=120, help="Timeout in seconds for cloud API requests")
    return parser


def sanitize_filename(value):
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)


def main():
    parser = build_parser()
    args = parser.parse_args()

    config_path = os.path.abspath(args.models_config)
    config_dir = os.path.dirname(config_path)
    project_root = os.path.abspath(os.getcwd())
    selected_models = args.models or list_models(config_path)

    suite_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_dir = os.path.abspath(os.path.join(args.output_root, f"suite_{suite_id}"))
    os.makedirs(suite_dir, exist_ok=True)

    suite_runs = []
    skipped = []
    resolved_models = []

    with open(config_path, "r", encoding="utf-8") as handle:
        config_snapshot = json.load(handle)
    config_snapshot_path = os.path.join(suite_dir, "models_config_snapshot.json")
    with open(config_snapshot_path, "w", encoding="utf-8") as handle:
        json.dump(config_snapshot, handle, indent=4)

    for model_name in selected_models:
        model_config = resolve_model_config(config_path, model_name)
        resolved_path = resolve_model_path(config_dir, model_config["model_path"], fallback_base_dir=project_root)
        model_file_info = file_metadata(resolved_path) if args.model_type == "gguf" else {"path": model_config["model_path"], "exists": True}
        if args.model_type == "gguf" and not args.mock:
            if not os.path.exists(resolved_path):
                skipped.append({"model": model_name, "reason": f"missing model file: {resolved_path}", "model_file": model_file_info})
                print(f"Skipping {model_name}: missing model file")
                continue
            if os.path.getsize(resolved_path) == 0:
                skipped.append({"model": model_name, "reason": f"empty model file: {resolved_path}", "model_file": model_file_info})
                print(f"Skipping {model_name}: model file is empty")
                continue

        resolved_models.append(
            {
                "model_name": model_name,
                "config": model_config,
                "resolved_model_path": resolved_path if args.model_type == "gguf" else model_config["model_path"],
                "model_file": model_file_info,
            }
        )

        model_output_name = f"{sanitize_filename(model_name)}.json"
        model_args = SimpleNamespace(
            model_path=resolved_path if args.model_type == "gguf" else model_config["model_path"],
            model_name=model_name,
            task_type=args.task_type,
            output_name=model_output_name,
            output_dir=suite_dir,
            workers=args.workers,
            mock=args.mock,
            sample_size=args.sample_size,
            temperature=args.temperature,
            model_type=args.model_type,
            repeats=args.repeats,
            perturb=args.perturb,
            api_key=args.api_key,
            gguf_engine=args.gguf_engine,
            seed=args.seed,
            cloud_request_delay_s=args.cloud_request_delay_s,
            cloud_max_retries=args.cloud_max_retries,
            cloud_backoff_base_s=args.cloud_backoff_base_s,
            cloud_timeout_s=args.cloud_timeout_s,
            n_ctx=model_config.get("n_ctx", 2048),
            n_threads=model_config.get("n_threads"),
            n_batch=model_config.get("n_batch", 512),
        )

        print(f"Running benchmark for {model_name}...")
        suite_runs.append(run_benchmark(model_args))

    report_outputs = None
    raw_files = [f"{sanitize_filename(item['model_name'])}.json" for item in suite_runs]
    if raw_files:
        report_outputs = generate_reports(suite_dir, input_files=raw_files)

    latest_outputs = None
    if report_outputs:
        latest_outputs = publish_report_bundle(
            report_outputs,
            os.path.join("results", "latest"),
            extra_manifest={
                "suite_id": suite_id,
                "suite_dir": suite_dir,
                "models_config": config_path,
                "models_config_snapshot": config_snapshot_path,
                "seed": args.seed,
                "task_type": args.task_type,
                "gguf_engine": args.gguf_engine,
                "cloud_request_delay_s": args.cloud_request_delay_s,
                "cloud_max_retries": args.cloud_max_retries,
                "cloud_backoff_base_s": args.cloud_backoff_base_s,
                "cloud_timeout_s": args.cloud_timeout_s,
                "raw_result_files": raw_files,
            },
        )

    manifest = {
        "suite_id": suite_id,
        "suite_dir": suite_dir,
        "models_config": config_path,
        "models_config_snapshot": config_snapshot_path,
        "task_type": args.task_type,
        "seed": args.seed,
        "temperature": args.temperature,
        "workers": args.workers,
        "repeats": args.repeats,
        "perturb": args.perturb,
        "gguf_engine": args.gguf_engine,
        "cloud_request_delay_s": args.cloud_request_delay_s,
        "cloud_max_retries": args.cloud_max_retries,
        "cloud_backoff_base_s": args.cloud_backoff_base_s,
        "cloud_timeout_s": args.cloud_timeout_s,
        "raw_result_files": raw_files,
        "resolved_models": resolved_models,
        "runs": suite_runs,
        "skipped": skipped,
        "report_outputs": report_outputs,
        "latest_outputs": latest_outputs,
    }
    manifest_path = os.path.join(suite_dir, "suite_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=4)

    print(f"Suite manifest: {manifest_path}")
    if report_outputs:
        print(f"Suite tables: {report_outputs['tables_path']}")
    if latest_outputs:
        print(f"Latest published tables: {latest_outputs['tables_md']}")
    if skipped:
        print(f"Skipped models: {len(skipped)}")


if __name__ == "__main__":
    main()
