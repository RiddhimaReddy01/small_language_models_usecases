"""Main experiment runner for retrieval-grounded QA benchmark."""

import argparse
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import torch

from .data_loaders import sample_dataset
from .inference import get_memory_mb, load_model, run_hf_api_inference, run_inference
from .metrics import (
    add_operational_metrics,
    compute_answer_length_accuracy,
    compute_context_utilization_rate,
    compute_em,
    compute_f1,
    compute_hallucination_rate,
    compute_partial_answer_rate,
    compute_unsupported_answer_rate,
)
from .parsers import BenchmarkConfig, load_config, to_dict
from .reporting import save_json, save_metric_tables
from .worker import eval_model as worker_eval_model
from sddf.ingest import normalize_retrieval_grounded_predictions
from sddf.pipeline import run_sddf_postprocess

try:
    from .inference_gemini import run_gemini_inference
except ImportError:
    run_gemini_inference = None

try:
    import transformers
except ImportError:
    transformers = None


def parse_args():
    parser = argparse.ArgumentParser(description="Retrieval-Grounded QA Benchmark")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Path to YAML/JSON config file")
    parser.add_argument("--dataset", type=str, default=None, choices=["squad", "natural_questions", "nq"])
    parser.add_argument("--num_questions", type=int, default=None)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--baseline-gemini", action="store_true")
    parser.add_argument("--gemini-key", type=str, default=None)
    parser.add_argument("--gemini-only", action="store_true")
    parser.add_argument("--gemini-concurrency", type=int, default=10)
    return parser.parse_args()


def run_experiment(config: BenchmarkConfig, args: argparse.Namespace) -> tuple[dict, dict]:
    models = config.models
    if args.gemini_only:
        models = []

    examples = sample_dataset(
        dataset_name=config.dataset_name,
        n_questions=config.num_questions,
        max_context_tokens=config.max_context_tokens,
        max_answer_tokens=config.max_answer_tokens,
        tokenizer=None,
    )

    all_results = {}
    all_predictions = {}

    cfg_dict = to_dict(config)
    if args.workers > 1 and models:
        n_workers = min(args.workers, len(models))
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(worker_eval_model, mid, cfg_dict, examples, wid): mid
                for wid, mid in enumerate(models)
            }
            for future in as_completed(futures):
                mid, results, preds = future.result()
                all_results[mid] = results
                all_predictions[mid] = preds
    else:
        for model_id in models:
            if model_id.startswith("hf_api:"):
                hf_model = model_id.split(":", 1)[1]
                start_time = time.time()
                inference_results = run_hf_api_inference(
                    hf_model,
                    examples,
                    max_new_tokens=config.max_new_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                )
                wall_time = time.time() - start_time

                predictions = [r.predicted_answer for r in inference_results]
                references = [r.reference_answer for r in inference_results]
                contexts = [ex.context for ex in examples]

                em = compute_em(predictions, references)
                f1 = compute_f1(predictions, references)
                cur = compute_context_utilization_rate(predictions, contexts)
                ala = compute_answer_length_accuracy(predictions, config.max_answer_tokens, tokenizer=None)
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
                op_metrics["wall_time_sec"] = wall_time
                op_metrics["questions"] = len(examples)

                labeled_model_id = f"hf_api:{hf_model}"
                all_results[labeled_model_id] = {
                    "model": labeled_model_id,
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
                all_predictions[labeled_model_id] = [
                    {
                        "id": r.example_id,
                        "prediction": r.predicted_answer,
                        "reference": r.reference_answer,
                        "context": ctx[:200] + "..." if len(ctx) > 200 else ctx,
                        "latency_sec": r.latency_sec,
                        "input_tokens": r.input_tokens,
                        "output_tokens": r.output_tokens,
                        "memory_mb": 0.0,
                    }
                    for r, ctx in zip(inference_results, contexts)
                ]
                continue

            model, tokenizer = load_model(
                model_id,
                device=config.device,
                torch_dtype=torch.float32 if config.device == "cpu" else torch.bfloat16,
            )
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

            predictions = [r.predicted_answer for r in inference_results]
            references = [r.reference_answer for r in inference_results]
            contexts = [ex.context for ex in examples]

            em = compute_em(predictions, references)
            f1 = compute_f1(predictions, references)
            cur = compute_context_utilization_rate(predictions, contexts)
            ala = compute_answer_length_accuracy(predictions, config.max_answer_tokens, tokenizer)
            halluc_rate = compute_hallucination_rate(predictions, contexts)
            unsupported_rate = compute_unsupported_answer_rate(predictions, contexts)
            partial_rate = compute_partial_answer_rate(predictions, references)

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

            all_results[model_id] = {
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
            all_predictions[model_id] = [
                {
                    "id": r.example_id,
                    "prediction": r.predicted_answer,
                    "reference": r.reference_answer,
                    "context": ctx[:200] + "..." if len(ctx) > 200 else ctx,
                    "latency_sec": r.latency_sec,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "memory_mb": memory_mb,
                }
                for r, ctx in zip(inference_results, contexts)
            ]

            del model
            del tokenizer
            if config.device == "cuda":
                torch.cuda.empty_cache()

    if args.baseline_gemini and run_gemini_inference is not None:
        api_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")
        if api_key:
            model_name, inference_results = run_gemini_inference(
                examples,
                api_key=api_key,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
                concurrency=getattr(args, "gemini_concurrency", 10),
            )
            predictions = [r.predicted_answer for r in inference_results]
            references = [r.reference_answer for r in inference_results]
            contexts = [ex.context for ex in examples]

            em = compute_em(predictions, references)
            f1 = compute_f1(predictions, references)
            cur = compute_context_utilization_rate(predictions, contexts)
            ala = compute_answer_length_accuracy(predictions, config.max_answer_tokens, tokenizer=None)
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
                    "latency_sec": r.latency_sec,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "memory_mb": 0.0,
                }
                for r, ctx in zip(inference_results, contexts)
            ]

    return all_results, all_predictions


def collect_environment_metadata() -> dict:
    """Capture environment details for reproducibility/debugging."""
    return {
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "torch_version": getattr(torch, "__version__", "unknown"),
        "transformers_version": getattr(transformers, "__version__", "not_installed"),
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.dataset:
        config.dataset_name = args.dataset if args.dataset != "nq" else "natural_questions"
    if args.num_questions:
        config.num_questions = args.num_questions
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.device == "auto":
        config.device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        config.device = args.device
    if args.gemini_only:
        args.baseline_gemini = True

    all_results, all_predictions = run_experiment(config, args)
    output_root = Path(config.output_dir)
    save_json(output_root / "metrics" / "results.json", all_results)
    for model_id, preds in all_predictions.items():
        safe_model = model_id.replace("/", "_")
        save_json(output_root / "predictions" / f"predictions_{safe_model}.json", preds)
    environment = collect_environment_metadata()
    save_metric_tables(output_root / "metrics", all_results, to_dict(config), environment)
    save_json(
        output_root / "logs" / "run_metadata.json",
        {"config": to_dict(config), "environment": environment},
    )
    sddf_rows = normalize_retrieval_grounded_predictions(all_predictions)
    run_sddf_postprocess(sddf_rows, task="retrieval_grounded", output_dir=output_root)
    print(f"Done. Outputs saved under {output_root}")


if __name__ == "__main__":
    main()
