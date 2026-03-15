"""
Model inference for Retrieval-Grounded QA.
Deterministic decoding: temperature=0, top_p=1.
"""

import gc
import time
from dataclasses import dataclass
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import PROMPT_TEMPLATE
from dataset import QAExample


@dataclass
class InferenceResult:
    """Result of a single inference."""
    example_id: str
    predicted_answer: str
    reference_answer: str
    latency_sec: float
    input_tokens: int
    output_tokens: int


def _build_prompt(context: str, question: str) -> str:
    return PROMPT_TEMPLATE.format(context=context.strip(), question=question.strip()).strip()


def load_model(
    model_name: str,
    device: str = "cpu",
    torch_dtype=torch.float32,
) -> tuple[AutoModelForCausalLM, AutoTokenizer]:
    """Load model and tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model = model.to(device)
    model.eval()
    return model, tokenizer


def run_inference(
    model,
    tokenizer,
    examples: list[QAExample],
    max_new_tokens: int = 30,
    temperature: float = 0.0,
    top_p: float = 1.0,
    device: str = "cpu",
    pad_token_id: Optional[int] = None,
) -> list[InferenceResult]:
    """
    Run inference on examples with deterministic decoding.
    temperature=0, top_p=1 → greedy/deterministic.
    """
    if pad_token_id is None:
        pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    results = []
    for ex in examples:
        prompt = _build_prompt(ex.context, ex.question)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)
        input_ids = inputs["input_ids"]
        input_token_count = input_ids.shape[1]

        start = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else 1.0,
                top_p=top_p,
                pad_token_id=pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.perf_counter() - start

        output_ids = outputs[0][input_ids.shape[1]:]
        output_token_count = len(output_ids)
        pred_text = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

        # Clean trailing newlines and common suffixes
        pred_text = pred_text.split("\n")[0].strip()

        results.append(InferenceResult(
            example_id=ex.id,
            predicted_answer=pred_text,
            reference_answer=ex.answer,
            latency_sec=elapsed,
            input_tokens=input_token_count,
            output_tokens=output_token_count,
        ))

    return results


def get_memory_mb() -> float:
    """Approximate PyTorch/CUDA memory in MB."""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024 / 1024
    return 0.0
