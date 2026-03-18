from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from huggingface_hub import InferenceClient

from ie_benchmark.config import InferenceConfig, ModelConfig
from ie_benchmark.prompting import build_gemini_prompt, build_prompt


@dataclass
class BackendPrediction:
    raw_output: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    peak_memory_mb: float | None = None
    metadata: dict[str, Any] | None = None


class OpenAICompatibleBackend:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        self.model = model_config.backend_model or model_config.model_id
        self.api_base = (inference_config.api_base or "http://localhost:11434/v1").rstrip("/")
        self.api_key = inference_config.api_key or "ollama"
        self.timeout_seconds = inference_config.timeout_seconds
        self.inference_config = inference_config

    def predict(self, text: str, target_fields: list[str]) -> BackendPrediction:
        prompt = build_prompt(text, target_fields)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": self.inference_config.temperature,
            "top_p": self.inference_config.top_p,
            "max_tokens": self.inference_config.max_new_tokens,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.api_base}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach inference backend at {self.api_base}. Start Ollama or another compatible server."
            ) from exc
        latency = time.perf_counter() - start
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        usage = parsed.get("usage", {})
        return BackendPrediction(
            raw_output=str(content).strip(),
            latency_seconds=latency,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            metadata={"usage": usage},
        )


class GeminiBackend:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        self.model = model_config.backend_model or model_config.model_id
        self.api_base = (inference_config.api_base or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.api_key = inference_config.api_key or os.environ.get("GEMINI_API_KEY")
        self.timeout_seconds = inference_config.timeout_seconds
        self.inference_config = inference_config
        if not self.api_key:
            raise RuntimeError("Gemini backend requires an API key.")

    def predict(self, text: str, target_fields: list[str]) -> BackendPrediction:
        prompt = build_gemini_prompt(text, target_fields)
        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "You extract structured data from noisy OCR receipts. "
                            "Your response must be a single compact JSON object with the keys "
                            "company, address, date, total. No markdown. No extra text."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.inference_config.temperature,
                "topP": self.inference_config.top_p,
                "maxOutputTokens": self.inference_config.max_new_tokens,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.api_base}/models/{self.model}:generateContent?key={self.api_key}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Could not reach the Gemini API.") from exc
        latency = time.perf_counter() - start
        parsed = json.loads(raw)
        candidate = parsed["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])
        content = "".join(str(part.get("text", "")) for part in parts).strip()
        usage = parsed.get("usageMetadata", {})
        return BackendPrediction(
            raw_output=content,
            latency_seconds=latency,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            metadata={
                "finish_reason": candidate.get("finishReason"),
                "safety_ratings": candidate.get("safetyRatings"),
                "prompt_feedback": parsed.get("promptFeedback"),
                "raw_response": parsed,
            },
        )


class HuggingFaceApiBackend:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        self.model = model_config.backend_model or model_config.model_id
        self.timeout_seconds = inference_config.timeout_seconds
        self.inference_config = inference_config
        token = (
            inference_config.api_key
            or os.environ.get("HF_API_KEY")
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        )
        if not token:
            raise RuntimeError("Hugging Face backend requires an API key.")
        self.client = InferenceClient(model=self.model, token=token, provider="auto", timeout=self.timeout_seconds)

    def predict(self, text: str, target_fields: list[str]) -> BackendPrediction:
        prompt = build_prompt(text, target_fields)
        start = time.perf_counter()
        try:
            content = self.client.text_generation(
                prompt,
                model=self.model,
                max_new_tokens=self.inference_config.max_new_tokens,
                temperature=self.inference_config.temperature,
                top_p=self.inference_config.top_p,
                do_sample=self.inference_config.do_sample,
                return_full_text=False,
            )
            content = str(content).strip()
        except Exception as text_exc:
            try:
                response = self.client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    max_tokens=self.inference_config.max_new_tokens,
                    temperature=self.inference_config.temperature,
                    top_p=self.inference_config.top_p,
                )
                content = self._extract_chat_text(response)
            except Exception as chat_exc:
                raise RuntimeError(str(chat_exc) or str(text_exc)) from chat_exc
        latency = time.perf_counter() - start
        return BackendPrediction(
            raw_output=content,
            latency_seconds=latency,
            input_tokens=max(1, len(prompt.split())),
            output_tokens=max(1, len(content.split())),
            metadata={"backend": "huggingface_api"},
        )

    def _extract_chat_text(self, response) -> str:
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
