import json
import os
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from scripts.data_loader import TextGenDataLoader
from scripts.inference_runner import TextGenInferenceRunner
from scripts.metrics_collector import TextGenMetricsCollector

def main():
    parser = argparse.ArgumentParser(description="SLM Text Generation Benchmark Runner")
    parser.add_argument("--model_path", type=str, required=True, help="Path to GGUF model file")
    parser.add_argument("--task_type", type=str, default="samples", help="Task type to run (samples, summarization, etc.)")
    parser.add_argument("--output_name", type=str, default="results.json", help="Name of output file in results/ directory")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (1 for serial)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no model needed)")
    parser.add_argument("--sample_size", type=int, default=None, help="Number of tasks to sample from the dataset")
    parser.add_argument("--temperature", type=float, default=0.7, help="Inference temperature")
    parser.add_argument("--model_type", type=str, default="gguf", choices=["gguf", "ollama", "google"], help="Model type (gguf, ollama, or google)")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repetitions for reliability testing")
    parser.add_argument("--perturb", action="store_true", help="Add minor typos to test robustness")
    parser.add_argument("--api_key", type=str, help="API key for cloud models (e.g. Gemini)")
    args = parser.parse_args()

    # 1. Load Data
    loader = TextGenDataLoader()
    tasks = loader.load_prompts(args.task_type)
    if not tasks:
        print("No tasks found. Exiting.")
        return
    
    if args.sample_size and args.sample_size < len(tasks):
        import random
        random.seed(42) # For reproducibility
        tasks = random.sample(tasks, args.sample_size)
        print(f"Sampled {args.sample_size} tasks for benchmarking.")

    # 2. Initialize Runner
    runner = TextGenInferenceRunner(
        model_path=args.model_path,
        n_ctx=2048,
        mock=args.mock,
        model_type=args.model_type
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
    output_path = os.path.join("results", args.output_name)
    os.makedirs("results", exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(final_results, f, indent=4)
    
    print(f"Benchmark complete. Results saved to {output_path}")

if __name__ == "__main__":
    main()
