from __future__ import annotations

import os
import math
import re
import time

import psutil
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from summarization_benchmark.config import ModelConfig, PromptConfig


def postprocess_summary(text: str) -> str:
    cleaned = text.strip().replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" \"'`")
    cleaned = re.sub(r"^(summary|headline)\s*:\s*", "", cleaned, flags=re.IGNORECASE)

    sentences = re.findall(r"[^.!?]+[.!?]", cleaned)
    if sentences:
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) >= 5:
                return sentence
        return sentences[0].strip()

    if cleaned and len(cleaned.split()) >= 5:
        return cleaned + "."
    return cleaned


def is_complete_sentence(text: str) -> bool:
    stripped = text.strip()
    if len(stripped.split()) < 5:
        return False
    return stripped.endswith((".", "!", "?"))


def load_model_components(model_config: ModelConfig):
    if model_config.provider == "gemini":
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        client = genai.Client(api_key=api_key)
        return None, client

    tokenizer = AutoTokenizer.from_pretrained(model_config.model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_config.model_name)
    model.eval()
    return tokenizer, model


def generate_summary(
    article: str,
    tokenizer,
    model,
    model_config: ModelConfig,
    prompt_config: PromptConfig,
    process: psutil.Process,
) -> dict:
    if model_config.provider == "gemini":
        from google.genai import types

        prompt = prompt_config.template.format(article=article)
        start = time.perf_counter()
        try:
            response = model.models.generate_content(
                model=model_config.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=model_config.temperature,
                    top_p=model_config.top_p,
                    max_output_tokens=model_config.max_new_tokens,
                    response_mime_type="text/plain",
                ),
            )
        except Exception as exc:
            if model_config.fallback_model_name and "429" in str(exc):
                response = model.models.generate_content(
                    model=model_config.fallback_model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=model_config.temperature,
                        top_p=model_config.top_p,
                        max_output_tokens=model_config.max_new_tokens,
                        response_mime_type="text/plain",
                    ),
                )
            else:
                raise
        latency_seconds = time.perf_counter() - start
        raw_response_text = response.text or ""
        generated_summary = postprocess_summary(raw_response_text)
        if not is_complete_sentence(generated_summary):
            generated_summary = ""
        output_tokens = len(generated_summary.split())
        return {
            "raw_response_text": raw_response_text,
            "generated_summary": generated_summary,
            "output_tokens": output_tokens,
            "latency_seconds": latency_seconds,
            "tokens_per_second": (output_tokens / latency_seconds) if latency_seconds > 0 else math.nan,
            "memory_mb": math.nan,
        }

    prompt = prompt_config.template.format(article=article)
    model_inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

    start = time.perf_counter()
    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            do_sample=model_config.do_sample,
            max_new_tokens=model_config.max_new_tokens,
        )
    latency_seconds = time.perf_counter() - start

    raw_response_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    generated_summary = postprocess_summary(raw_response_text)
    if not is_complete_sentence(generated_summary):
        generated_summary = ""
    output_tokens = len(tokenizer(generated_summary, truncation=False)["input_ids"])

    return {
        "raw_response_text": raw_response_text,
        "generated_summary": generated_summary,
        "output_tokens": output_tokens,
        "latency_seconds": latency_seconds,
        "tokens_per_second": (output_tokens / latency_seconds) if latency_seconds > 0 else math.nan,
        "memory_mb": process.memory_info().rss / (1024 * 1024),
    }
