from __future__ import annotations

import os
import re
import time
from pathlib import Path

import google.generativeai as genai

try:
    import ollama
except ImportError:  # pragma: no cover - optional local backend
    ollama = None


class ModelWrapper:
    def predict(self, text, labels):
        raise NotImplementedError

    def _prepare_text(self, text, max_chars=600):
        text = (text or "").strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0].strip() + "..."

    def _clean_prediction(self, prediction):
        if not prediction:
            return prediction
        cleaned = prediction.strip().splitlines()[0].strip()
        cleaned = cleaned.strip("`\"' \t\r\n:.-")
        cleaned = re.sub(r"^(label|answer|prediction)\s*[:=-]\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned


def _load_google_api_key():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return api_key

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "GOOGLE_API_KEY":
            secret = value.strip().strip("\"'")
            if secret:
                os.environ["GOOGLE_API_KEY"] = secret
                return secret
    return None


class OllamaWrapper(ModelWrapper):
    def __init__(self, model_name, max_text_chars=600):
        self.model_name = model_name
        self.max_text_chars = max_text_chars

    def predict(self, text, labels):
        if ollama is None:
            return {
                "prediction": None,
                "latency": 0.0,
                "status": "error: ollama package is not installed",
            }
        prompt = self._build_prompt(text, labels)
        start_time = time.time()
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0,
                    "num_predict": 6,
                    "top_k": 1,
                    "top_p": 0.1,
                },
                keep_alive="15m",
            )
            return {
                "prediction": self._clean_prediction(response.get("response", "")),
                "latency": time.time() - start_time,
                "status": "success",
            }
        except Exception as exc:
            return {
                "prediction": None,
                "latency": time.time() - start_time,
                "status": f"error: {exc}",
            }

    def _build_prompt(self, text, labels):
        labels_str = ", ".join(labels)
        compact_text = self._prepare_text(text, max_chars=self.max_text_chars)
        return f"""You are a text classification system.

Choose exactly one label from the list:
{labels_str}

Respond with only one label and no extra words.

Text:
{compact_text}"""


class GeminiWrapper(ModelWrapper):
    def __init__(self, model_name="gemini-3.1-flash-lite-preview", max_text_chars=1200):
        api_key = _load_google_api_key()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.primary_model_name = model_name
        self.fallback_model_name = "gemini-2.5-flash-lite" if model_name == "gemini-3.1-flash-lite-preview" else None
        self.active_model_name = model_name
        self.model = genai.GenerativeModel(self.active_model_name)
        self.max_text_chars = max_text_chars

    def predict(self, text, labels):
        prompt = self._build_prompt(text, labels)
        start_time = time.time()
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0,
                    "top_k": 1,
                    "top_p": 0.1,
                    "max_output_tokens": 8,
                },
            )
            return {
                "prediction": self._clean_prediction(response.text),
                "latency": time.time() - start_time,
                "status": f"success:{self.active_model_name}",
            }
        except Exception as exc:
            if self._is_rate_limit_error(exc) and self._activate_fallback_model():
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0,
                            "top_k": 1,
                            "top_p": 0.1,
                            "max_output_tokens": 8,
                        },
                    )
                    return {
                        "prediction": self._clean_prediction(response.text),
                        "latency": time.time() - start_time,
                        "status": f"success:fallback_to_{self.active_model_name}",
                    }
                except Exception as fallback_exc:
                    return {
                        "prediction": None,
                        "latency": time.time() - start_time,
                        "status": f"error: fallback after rate limit failed: {fallback_exc}",
                    }

            return {
                "prediction": None,
                "latency": time.time() - start_time,
                "status": f"error: {exc}",
            }

    def _is_rate_limit_error(self, error):
        error_text = str(error).lower()
        return any(token in error_text for token in ("429", "resource_exhausted", "rate limit", "quota"))

    def _activate_fallback_model(self):
        if not self.fallback_model_name or self.active_model_name == self.fallback_model_name:
            return False
        self.active_model_name = self.fallback_model_name
        self.model = genai.GenerativeModel(self.active_model_name)
        return True

    def _build_prompt(self, text, labels):
        labels_str = ", ".join(labels)
        compact_text = self._prepare_text(text, max_chars=self.max_text_chars)
        return f"""You are a text classification system.

Choose exactly one label from the list:
{labels_str}

Respond with only one label and no extra words.

Text:
{compact_text}"""
