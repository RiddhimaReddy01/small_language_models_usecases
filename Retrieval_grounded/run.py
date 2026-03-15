"""
Retrieval-Grounded QA Benchmark - Main Entry Point

Evaluates SLMs on answering questions using supplied context passages.
Uses worker pool: tasks are assigned to free workers for parallel execution.
"""

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import torch

from config import BenchmarkConfig
from dataset import sample_dataset, QAExample
from inference import load_model, run_inference, get_memory_mb
from metrics import (
    compute_em,
    compute_f1,
    compute_context_utilization_rate,
    compute_answer_length_accuracy,
    compute_hallucination_rate,
    compute_unsupported_answer_rate,
    compute_partial_answer_rate,
    add_operational_metrics,
)
from worker import eval_model as worker_eval_model

try:
    from inference_gemini import run_gemini_inference
except ImportError:
    run_gemini_inference = None


def parse_args():
    parser = argparse.ArgumentParser(description="Retrieval-Grounded QA Benchmark")
    parser.add_argument("--config", type=str, help="Path to JSON config file")
    parser.add_argument(
        "--dataset",
        type=str,
        default="squad",
        choices=["squad", "natural_questions", "nq"],
        help="Dataset to use (default: squad)",
    )
    parser.add_argument(
        "--num_questions",
        type=int,
        default=30,
        help="Number of questions to evaluate (default: 30)",
    )
    parser.add_argument(
        "--max_context_tokens",
        type=int,
        default=300,
        help="Max context length in tokens (default: 300)",
    )
    parser.add_argument(
        "--max_answer_tokens",
        type=int,
        default=10,
        help="Max answer length in tokens (default: 10)",
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=None,
        help="Model names to evaluate (default: Qwen2.5-Coder 0.5B, DeepSeek-Coder 1.3B, Qwen2.5-Coder 1.5B)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./results",
        help="Directory to save results",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for inference",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (uses free workers from pool; default: 1 = sequential)",
    )
    parser.add_argument(
        "--baseline-gemini",
        action="store_true",
        help="Run Gemini API as baseline (requires GEMINI_API_KEY or --gemini-key)",
    )
    parser.add_argument(
        "--gemini-key",
        type=str,
        default=None,
        help="Gemini API key (default: use GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--gemini-only",
        action="store_true",
        help="Run only Gemini baseline (skip SLM models)",
    )
    parser.add_argument(
        "--gemini-concurrency",
        type=int,
        default=10,
        help="Parallel Gemini API calls (default: 10; lower if rate limited)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.gemini_only:
        args.baseline_gemini = True

    if args.config:
        with open(args.config) as f:
            cfg_dict = json.load(f)
        config = BenchmarkConfig(**cfg_dict)
    else:
        config = BenchmarkConfig()
        config.dataset_name = args.dataset if args.dataset != "nq" else "natural_questions"
        config.num_questions = args.num_questions
        config.max_context_tokens = args.max_context_tokens
        config.max_answer_tokens = args.max_answer_tokens
        config.output_dir = args.output_dir
        if args.models:
            config.models = args.models
        if args.device == "auto":
            config.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            config.device = args.device

    models = config.models
    if args.baseline_gemini and run_gemini_inference is not None:
        api_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")
        if api_key and (not models or args.gemini_only):
            models = models or []  # Allow empty SLM list when --gemini-only

    print("=" * 60)
    print("Retrieval-Grounded QA Benchmark")
    print("=" * 60)
    print(f"Dataset: {config.dataset_name}")
    print(f"Questions: {config.num_questions}")
    print(f"Context <= {config.max_context_tokens} tokens, Answer <= {config.max_answer_tokens} tokens")
    print(f"Models: {models}")
    print(f"Device: {config.device}")
    print(f"Workers: {args.workers} (parallel; tasks go to free workers)")
    print("=" * 60)

    # Load data once so all models see same examples
    print("\nLoading benchmark data...")
    examples = sample_dataset(
        dataset_name=config.dataset_name,
        n_questions=config.num_questions,
        max_context_tokens=config.max_context_tokens,
        max_answer_tokens=config.max_answer_tokens,
        tokenizer=None,
    )
    print(f"Loaded {len(examples)} QA pairs")

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    all_predictions = {}
    num_workers = args.workers

    if args.gemini_only:
        models = []

    # Build config dict for workers
    cfg_dict = {
        "dataset_name": config.dataset_name,
        "dataset_split": config.dataset_split,
        "num_questions": config.num_questions,
        "max_context_tokens": config.max_context_tokens,
        "max_answer_tokens": config.max_answer_tokens,
        "models": config.models,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_new_tokens": config.max_new_tokens,
        "do_sample": config.do_sample,
        "device": config.device,
        "output_dir": config.output_dir,
    }

    if num_workers > 1:
        # Parallel: assign each model to a free worker from the pool
        n_workers = min(num_workers, len(models))
        print(f"\nUsing {n_workers} parallel workers (searching for free workers)")
        start_wall = time.time()
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(worker_eval_model, mid, cfg_dict, examples, wid): mid
                for wid, mid in enumerate(models)
            }
            for future in as_completed(futures):
                model_id = futures[future]
                try:
                    mid, results, preds = future.result()
                    all_results[mid] = results
                    all_predictions[mid] = preds
                    op = results.get("operational", {})
                    print(f"  [{mid}] EM: {results['capability']['exact_match']:.1f}% | "
                          f"Latency: {op.get('latency_ms', 0):.0f} ms | tok/s: {op.get('tokens_per_sec', 0):.1f}")
                except Exception as e:
                    print(f"  [{model_id}] ERROR: {e}")
        print(f"\nTotal wall time: {time.time() - start_wall:.1f}s")
    else:
        for model_id in models:
            print(f"\n{'=' * 60}")
            print(f"Evaluating: {model_id}")
            print("=" * 60)

            # Load model and tokenizer
            model, tokenizer = load_model(
                model_id,
                device=config.device,
                torch_dtype=torch.float32 if config.device == "cpu" else torch.bfloat16,
            )

            # Run inference
            start_time = time.time()
            inference_results = run_inference(
                model,
                tokenizer,
                examples,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                device=config.device,
            )
            wall_time = time.time() - start_time

            # Extract lists for metrics
            predictions = [r.predicted_answer for r in inference_results]
            references = [r.reference_answer for r in inference_results]
            contexts = [ex.context for ex in examples]

            # Capability metrics
            em = compute_em(predictions, references)
            f1 = compute_f1(predictions, references)
            cur = compute_context_utilization_rate(predictions, contexts)
            ala = compute_answer_length_accuracy(
                predictions, config.max_answer_tokens, tokenizer
            )

            # Reliability metrics
            halluc_rate = compute_hallucination_rate(predictions, contexts)
            unsupported_rate = compute_unsupported_answer_rate(predictions, contexts)
            partial_rate = compute_partial_answer_rate(predictions, references)

            # Operational metrics
            latencies_ms = [r.latency_sec * 1000 for r in inference_results]
            output_tokens = [r.output_tokens for r in inference_results]
            input_tokens = [r.input_tokens for r in inference_results]
            memory_mb = get_memory_mb()
            op_metrics = {}
            add_operational_metrics(
                op_metrics,
                latencies_ms=latencies_ms,
                output_tokens=output_tokens,
                input_tokens=input_tokens,
                memory_mb=memory_mb,
            )
            op_metrics["wall_time_sec"] = wall_time
            op_metrics["questions"] = len(examples)

            results = {
                "model": model_id,
                "capability": {
                    "exact_match": em,
                    "f1_score": f1,
                    "context_utilization_rate": cur,
                    "answer_length_accuracy": ala,
                },
                "reliability": {
                    "hallucination_rate": halluc_rate,
                    "unsupported_answer_rate": unsupported_rate,
                    "partial_answer_rate": partial_rate,
                },
                "operational": op_metrics,
            }
            all_results[model_id] = results
            all_predictions[model_id] = [
                {
                    "id": r.example_id,
                    "prediction": r.predicted_answer,
                    "reference": r.reference_answer,
                    "context": ctx[:200] + "..." if len(ctx) > 200 else ctx,
                }
                for r, ctx in zip(inference_results, contexts)
            ]

            print(f"  EM:  {em:.2f}%")
            print(f"  F1:  {f1:.2f}%")
            print(f"  CUR: {cur:.2f}%")
            print(f"  ALA: {ala:.2f}%")
            print(f"  Hallucination rate: {halluc_rate:.2f}%")
            print(f"  Partial answer rate: {partial_rate:.2f}%")
            print(f"  Latency: {op_metrics.get('latency_ms', 0):.1f} ms/query")
            print(f"  Throughput: {op_metrics.get('tokens_per_sec', 0):.1f} tok/s")

            # Free memory before loading next model
            del model
            del tokenizer
            if config.device == "cuda":
                torch.cuda.empty_cache()

    # Gemini baseline (API)
    if args.baseline_gemini and run_gemini_inference is not None:
        api_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("\n[!] Skipping Gemini baseline: no API key (set GEMINI_API_KEY or --gemini-key)")
        else:
            print(f"\n{'=' * 60}")
            print("Evaluating: Gemini (baseline)")
            print("=" * 60)
            try:
                model_name, inference_results = run_gemini_inference(
                    examples,
                    api_key=api_key,
                    max_new_tokens=config.max_new_tokens,
                    temperature=config.temperature,
                    concurrency=getattr(args, "gemini_concurrency", 10),
                )
                print(f"  Using model: {model_name}")

                predictions = [r.predicted_answer for r in inference_results]
                references = [r.reference_answer for r in inference_results]
                contexts = [ex.context for ex in examples]

                em = compute_em(predictions, references)
                f1 = compute_f1(predictions, references)
                cur = compute_context_utilization_rate(predictions, contexts)
                ala = compute_answer_length_accuracy(
                    predictions, config.max_answer_tokens, tokenizer=None
                )
                halluc_rate = compute_hallucination_rate(predictions, contexts)
                unsupported_rate = compute_unsupported_answer_rate(predictions, contexts)
                partial_rate = compute_partial_answer_rate(predictions, references)

                latencies_ms = [r.latency_sec * 1000 for r in inference_results]
                output_tokens = [r.output_tokens for r in inference_results]
                input_tokens = [r.input_tokens for r in inference_results]
                op_metrics = {}
                add_operational_metrics(
                    op_metrics,
                    latencies_ms=latencies_ms,
                    output_tokens=output_tokens,
                    input_tokens=input_tokens,
                    memory_mb=0.0,
                )
                op_metrics["wall_time_sec"] = sum(latencies_ms) / 1000.0
                op_metrics["questions"] = len(examples)

                gemini_id = f"gemini/{model_name}"
                all_results[gemini_id] = {
                    "model": gemini_id,
                    "capability": {
                        "exact_match": em,
                        "f1_score": f1,
                        "context_utilization_rate": cur,
                        "answer_length_accuracy": ala,
                    },
                    "reliability": {
                        "hallucination_rate": halluc_rate,
                        "unsupported_answer_rate": unsupported_rate,
                        "partial_answer_rate": partial_rate,
                    },
                    "operational": op_metrics,
                }
                all_predictions[gemini_id] = [
                    {
                        "id": r.example_id,
                        "prediction": r.predicted_answer,
                        "reference": r.reference_answer,
                        "context": ctx[:200] + "..." if len(ctx) > 200 else ctx,
                    }
                    for r, ctx in zip(inference_results, contexts)
                ]

                print(f"  EM:  {em:.2f}%")
                print(f"  F1:  {f1:.2f}%")
                print(f"  CUR: {cur:.2f}%")
                print(f"  ALA: {ala:.2f}%")
                print(f"  Hallucination rate: {halluc_rate:.2f}%")
                print(f"  Latency: {op_metrics.get('latency_ms', 0):.1f} ms/query")
            except Exception as e:
                print(f"  Gemini ERROR: {e}")
    elif args.baseline_gemini and run_gemini_inference is None:
        print("\n[!] Skipping Gemini: google-generativeai not installed (pip install google-generativeai)")

    # Save results
    out_path = output_dir / "results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Save per-model predictions for analysis (only for models that completed)
    for model_id in all_predictions:
        pred_path = output_dir / f"predictions_{model_id.replace('/', '_')}.json"
        with open(pred_path, "w") as f:
            json.dump(all_predictions[model_id], f, indent=2)

    print("\nDone.")
    return all_results


if __name__ == "__main__":
    main()
