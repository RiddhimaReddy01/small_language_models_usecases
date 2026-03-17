"""
Worker for parallel model evaluation.
Runs in separate process; tasks are assigned to free workers from the pool.
"""

import time

import torch

from .data_loaders import QAExample
from .inference import get_memory_mb, load_model, run_inference
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
from .parsers import BenchmarkConfig


def _get_device_for_worker(device: str, worker_id: int) -> str:
    """Assign device to worker. For multi-GPU, use round-robin."""
    if device != "cuda":
        return device
    num_gpus = torch.cuda.device_count()
    if num_gpus <= 1:
        return "cuda"
    return f"cuda:{worker_id % num_gpus}"


def eval_model(
    model_id: str,
    cfg_dict: dict,
    examples: list[QAExample],
    worker_id: int = 0,
) -> tuple[str, dict, list[dict]]:
    """
    Evaluate a single model. Runs in worker process.
    Returns (model_id, results, predictions).
    """
    config = BenchmarkConfig(**cfg_dict)
    device = _get_device_for_worker(config.device, worker_id)

    model, tokenizer = load_model(
        model_id,
        device=device,
        torch_dtype=torch.float32 if device == "cpu" else torch.bfloat16,
    )

    start_time = time.time()
    inference_results = run_inference(
        model,
        tokenizer,
        examples,
        max_new_tokens=config.max_new_tokens,
        temperature=config.temperature,
        top_p=config.top_p,
        device=device,
    )
    wall_time = time.time() - start_time

    predictions = [r.predicted_answer for r in inference_results]
    references = [r.reference_answer for r in inference_results]
    contexts = [ex.context for ex in examples]

    em = compute_em(predictions, references)
    f1 = compute_f1(predictions, references)
    cur = compute_context_utilization_rate(predictions, contexts)
    ala = compute_answer_length_accuracy(
        predictions, config.max_answer_tokens, tokenizer
    )
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

    preds = [
        {
            "id": r.example_id,
            "prediction": r.predicted_answer,
            "reference": r.reference_answer,
            "context": ctx[:200] + "..." if len(ctx) > 200 else ctx,
            "latency_sec": r.latency_sec,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "memory_mb": None,
        }
        for r, ctx in zip(inference_results, contexts)
    ]

    del model
    del tokenizer
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    return model_id, results, preds
