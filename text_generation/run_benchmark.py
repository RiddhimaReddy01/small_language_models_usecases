import json
import os
import argparse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from sddf.ingest import normalize_text_generation_results
from sddf.pipeline import run_sddf_postprocess
from scripts.data_loader import TextGenDataLoader
from scripts.inference_runner import TextGenInferenceRunner
from scripts.metrics_collector import TextGenMetricsCollector
from scripts.reporting import generate_reports, publish_report_bundle


def derive_model_name(args):
    if getattr(args, "model_name", None):
        return args.model_name
    if args.mock:
        return "mock"
    if args.model_type == "gguf":
        return os.path.splitext(os.path.basename(args.model_path))[0]
    return args.model_path


def build_parser():
    parser = argparse.ArgumentParser(description="SLM Text Generation Benchmark Runner")
    parser.add_argument("--model_path", type=str, help="Path to GGUF model file or remote model identifier")
    parser.add_argument("--model_name", type=str, help="Friendly model name to save in outputs")
    parser.add_argument("--task_type", type=str, default="samples", help="Task type to run (samples, summarization, etc.)")
    parser.add_argument("--output_name", type=str, default="results.json", help="Name of output file in the output directory")
    parser.add_argument("--output_dir", type=str, default="results", help="Directory where results and reports are saved")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (1 for serial)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no model needed)")
    parser.add_argument("--sample_size", type=int, default=None, help="Number of tasks to sample from the dataset")
    parser.add_argument("--temperature", type=float, default=0.7, help="Inference temperature")
    parser.add_argument("--model_type", type=str, default="gguf", choices=["gguf", "ollama", "google", "openai"], help="Model type (gguf, ollama, google, or openai)")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repetitions for reliability testing")
    parser.add_argument("--perturb", action="store_true", help="Add minor typos to test robustness")
    parser.add_argument("--api_key", type=str, help="API key for cloud models (e.g. Gemini)")
    parser.add_argument("--n_ctx", type=int, default=2048, help="Context window for local GGUF models")
    parser.add_argument("--n_threads", type=int, default=None, help="Thread count for local GGUF models")
    parser.add_argument("--n_batch", type=int, default=512, help="Batch size for local GGUF models")
    parser.add_argument("--gguf_engine", type=str, default="llama_cpp", choices=["llama_cpp", "llama_cli"], help="Inference engine for GGUF models")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for sampling and prompt perturbation")
    parser.add_argument("--cloud_request_delay_s", type=float, default=0.0, help="Delay before each cloud API request")
    parser.add_argument("--cloud_max_retries", type=int, default=0, help="Maximum retries for transient cloud API failures")
    parser.add_argument("--cloud_backoff_base_s", type=float, default=2.0, help="Base backoff in seconds for cloud API retries")
    parser.add_argument("--cloud_timeout_s", type=int, default=120, help="Timeout in seconds for cloud API requests")
    return parser


def validate_args(args):
    if not args.mock and not args.model_path:
        raise ValueError("--model_path is required unless --mock is used")

def run_benchmark(args):
    validate_args(args)

    # 1. Load Data
    loader = TextGenDataLoader()
    tasks = loader.load_prompts(args.task_type)
    if not tasks:
        print("No tasks found. Exiting.")
        return
    
    if args.sample_size and args.sample_size < len(tasks):
        random.seed(args.seed)
        tasks = random.sample(tasks, args.sample_size)
        print(f"Sampled {args.sample_size} tasks for benchmarking.")

    # 2. Initialize Runner
    runner = TextGenInferenceRunner(
        model_path=args.model_path,
        n_ctx=args.n_ctx,
        n_threads=args.n_threads,
        n_batch=args.n_batch,
        mock=args.mock,
        model_type=args.model_type,
        gguf_engine=args.gguf_engine,
        cloud_request_delay_s=args.cloud_request_delay_s,
        cloud_max_retries=args.cloud_max_retries,
        cloud_backoff_base_s=args.cloud_backoff_base_s,
        cloud_timeout_s=args.cloud_timeout_s,
    )
    runner.load_model(api_key=args.api_key)

    # 3. Setup Metrics
    collector = TextGenMetricsCollector()

    # 4. Run Benchmark
    print(f"Running benchmark for {len(tasks)} tasks (repeats={args.repeats}, perturb={args.perturb}) using {args.workers} worker(s)...")
    final_results = []

    def perturb_prompt(prompt):
        """Robustness: add minor typos."""
        if not prompt or len(prompt) < 10: return prompt
        # Simple swap of two adjacent characters
        p_list = list(prompt)
        idx = len(prompt) // 2
        p_list[idx], p_list[idx+1] = p_list[idx+1], p_list[idx]
        return "".join(p_list)

    def process_task(task, run_id=0):
        prompt = task.get("prompt", "")
        if args.perturb:
            prompt = perturb_prompt(prompt)
            
        reference = task.get("reference", None)
        constraints = task.get("constraints", None)

        try:
            # Generate
            response, operational_metrics = runner.run_inference(prompt, temperature=args.temperature)
            
            # Add Model Load Time and Cost estimate
            operational_metrics["model_load_time"] = runner.load_time
            # Estimate cost: Gemini 1.5 Flash is roughly $0.075/1M tokens (very cheap)
            if args.model_type == "google":
                operational_metrics["cost_usd"] = (operational_metrics.get("tokens_generated", 0) / 1000000) * 0.075
            elif args.model_type == "openai":
                operational_metrics["cost_usd"] = (operational_metrics.get("tokens_generated", 0) / 1000000) * 0.60
            else:
                operational_metrics["cost_usd"] = 0.0 # Local SLM

            # Evaluate
            advanced_metrics = collector.aggregate_metrics(
                response, 
                reference=reference, 
                constraints=constraints
            )

            return {
                "task_id": task.get("id"),
                "run_id": run_id,
                "model_name": derive_model_name(args),
                "task_type": task.get("task"),
                "prompt": prompt,
                "response": response,
                "metrics": {
                    "operational": operational_metrics,
                    "framework": advanced_metrics
                }
            }
        except Exception as e:
            print(f"Inference failed for task {task.get('id')}: {e}")
            return {
                "task_id": task.get("id"),
                "run_id": run_id,
                "model_name": derive_model_name(args),
                "error": str(e),
                "metrics": {"operational": {"status": "failed"}}
            }

    # Execute with repeats
    for i in range(args.repeats):
        if args.workers > 1 and args.model_type != "gguf": # ThreadPool is tricky with llama-cpp sometimes
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_to_task = {executor.submit(process_task, task, i): task for task in tasks}
                for future in as_completed(future_to_task):
                    final_results.append(future.result())
        else:
            for task in tasks:
                final_results.append(process_task(task, i))

    # 5. Save Results
    output_path = os.path.join(args.output_dir, args.output_name)
    os.makedirs(args.output_dir, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(final_results, f, indent=4)

    metadata = {
        "model_name": derive_model_name(args),
        "model_path": args.model_path,
        "model_type": args.model_type,
        "mock": args.mock,
        "task_type": args.task_type,
        "sample_size": args.sample_size,
        "temperature": args.temperature,
        "workers": args.workers,
        "repeats": args.repeats,
        "perturb": args.perturb,
        "n_ctx": args.n_ctx,
        "n_threads": args.n_threads,
        "n_batch": args.n_batch,
        "gguf_engine": args.gguf_engine,
        "seed": args.seed,
        "cloud_request_delay_s": args.cloud_request_delay_s,
        "cloud_max_retries": args.cloud_max_retries,
        "cloud_backoff_base_s": args.cloud_backoff_base_s,
        "cloud_timeout_s": args.cloud_timeout_s,
        "result_file": args.output_name,
    }
    metadata_path = os.path.join(args.output_dir, f"{os.path.splitext(args.output_name)[0]}_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=4)

    sddf_rows = normalize_text_generation_results(final_results, metadata=metadata)
    sddf_summary = run_sddf_postprocess(
        sddf_rows,
        task="text_generation",
        output_dir=args.output_dir,
        rule_config={"constraint_rules": {}},
    )

    report_outputs = generate_reports(args.output_dir)
    latest_outputs = publish_report_bundle(
        report_outputs,
        os.path.join("results", "latest"),
        extra_manifest={
            "model_name": metadata["model_name"],
            "task_type": args.task_type,
            "seed": args.seed,
            "result_file": output_path,
            "metadata_path": metadata_path,
            "gguf_engine": args.gguf_engine,
            "cloud_request_delay_s": args.cloud_request_delay_s,
            "cloud_max_retries": args.cloud_max_retries,
            "cloud_backoff_base_s": args.cloud_backoff_base_s,
            "cloud_timeout_s": args.cloud_timeout_s,
        },
    )
    print(f"Benchmark complete. Results saved to {output_path}")
    print(f"SDDF rows archived to {sddf_summary['archive_path']}")
    print(f"Summary tables saved to {report_outputs['tables_path']}")
    print(f"Latest published tables saved to {latest_outputs['tables_md']}")
    return {
        "results_path": output_path,
        "metadata_path": metadata_path,
        "sddf_summary": sddf_summary,
        "report_outputs": report_outputs,
        "latest_outputs": latest_outputs,
        "model_name": metadata["model_name"],
    }


def main():
    parser = build_parser()
    args = parser.parse_args()
    run_benchmark(args)

if __name__ == "__main__":
    main()
