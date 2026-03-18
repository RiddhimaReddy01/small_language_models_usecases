"""
Model inference for Retrieval-Grounded QA.
Deterministic decoding: temperature=0, top_p=1.
"""

import time
from dataclasses import dataclass
from typing import Optional

import torch
from huggingface_hub import InferenceClient
from transformers import AutoModelForCausalLM, AutoTokenizer

from .data_loaders import QAExample
from .prompts import PROMPT_TEMPLATE


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
    temperature=0, top_p=1 -> greedy/deterministic.
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


def run_hf_api_inference(
    model_name: str,
    examples: list[QAExample],
    *,
    max_new_tokens: int = 30,
    temperature: float = 0.0,
    top_p: float = 1.0,
    token_envs: tuple[str, ...] = ("HF_API_KEY", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"),
) -> list[InferenceResult]:
    token = None
    import os

    for env_name in token_envs:
        token = os.environ.get(env_name)
        if token:
            break
    if not token:
        raise RuntimeError("Hugging Face API token not found in HF_API_KEY, HF_TOKEN, or HUGGINGFACEHUB_API_TOKEN.")

    client = InferenceClient(model=model_name, token=token, provider="auto", timeout=180)
    results: list[InferenceResult] = []
    for ex in examples:
        prompt = _build_prompt(ex.context, ex.question)
        input_token_count = max(1, len(prompt.split()))
        start = time.perf_counter()
        try:
            pred_text = client.text_generation(
                prompt,
                model=model_name,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                return_full_text=False,
            )
            pred_text = str(pred_text).strip()
        except Exception as text_exc:
            try:
                response = client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_name,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                pred_text = _extract_chat_text(response)
            except Exception as chat_exc:
                raise RuntimeError(str(chat_exc) or str(text_exc)) from chat_exc
        elapsed = time.perf_counter() - start
        pred_text = pred_text.split("\n")[0].strip()
        output_token_count = max(1, len(pred_text.split()))
        results.append(
            InferenceResult(
                example_id=ex.id,
                predicted_answer=pred_text,
                reference_answer=ex.answer,
                latency_sec=elapsed,
                input_tokens=input_token_count,
                output_tokens=output_token_count,
            )
        )
    return results


def _extract_chat_text(response) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None:
        return ""
    content = getattr(message, "content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content or "").strip()


def get_memory_mb() -> float:
    """Approximate PyTorch/CUDA memory in MB."""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024 / 1024
    return 0.0
