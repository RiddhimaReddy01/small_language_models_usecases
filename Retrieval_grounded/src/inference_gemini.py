"""
Gemini API inference for Retrieval-Grounded QA baseline.
Uses Gemini 3.1 Flash Lite; falls back to other models if deprecated or rate-limited.
Runs requests in parallel for faster completion.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .data_loaders import QAExample
from .inference import InferenceResult
from .prompts import PROMPT_TEMPLATE

GEMINI_MODEL_FALLBACK = [
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]

DEFAULT_CONCURRENCY = 10


def _build_prompt(context: str, question: str) -> str:
    return PROMPT_TEMPLATE.format(context=context.strip(), question=question.strip()).strip()


def _is_rate_limit(e: Exception) -> bool:
    err = str(e).lower()
    return "429" in err or "rate" in err or "resource_exhausted" in err


def _is_model_unavailable(e: Exception) -> bool:
    err = str(e).lower()
    return (
        "404" in err or "not found" in err or "deprecated" in err
        or "invalid" in err and "model" in err
    )


def _single_request(ex: QAExample, model, gen_cfg) -> InferenceResult:
    prompt = _build_prompt(ex.context, ex.question)
    start = time.perf_counter()
    response = model.generate_content(prompt, generation_config=gen_cfg)
    elapsed = time.perf_counter() - start
    text = (response.text or "").strip()
    text = text.split("\n")[0].strip() if text else ""
    input_approx = len(prompt.split()) * 4 // 3
    output_approx = max(1, len(text.split()) * 4 // 3)
    return InferenceResult(
        example_id=ex.id,
        predicted_answer=text,
        reference_answer=ex.answer,
        latency_sec=elapsed,
        input_tokens=input_approx,
        output_tokens=output_approx,
    )


def run_gemini_inference(
    examples: list[QAExample],
    api_key: str,
    max_new_tokens: int = 30,
    temperature: float = 0.0,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> tuple[str, list[InferenceResult]]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    model_idx = 0
    model_name = GEMINI_MODEL_FALLBACK[0]
    model = genai.GenerativeModel(model_name)
    gen_cfg = genai.GenerationConfig(
        max_output_tokens=max_new_tokens,
        temperature=temperature,
        top_p=1.0,
    )

    concurrency = min(concurrency, len(examples), 15)
    results = [None] * len(examples)
    pending = list(enumerate(examples))

    while pending:
        batch = pending[:concurrency]
        pending = pending[concurrency:]

        for attempt in range(6):
            try:
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = {
                        executor.submit(_single_request, ex, model, gen_cfg): (i, ex)
                        for i, ex in batch
                    }
                    for future in as_completed(futures):
                        i, _ = futures[future]
                        results[i] = future.result()
                break
            except Exception as e:
                if _is_rate_limit(e):
                    wait = min(2 ** (attempt + 1), 60)
                    time.sleep(wait)
                    continue
                if _is_model_unavailable(e) and model_idx + 1 < len(GEMINI_MODEL_FALLBACK):
                    model_idx += 1
                    model_name = GEMINI_MODEL_FALLBACK[model_idx]
                    model = genai.GenerativeModel(model_name)
                    continue
                raise

    return model_name, results
