import hashlib
import os
import re
import time
from typing import Any, Dict, Optional

import requests
from huggingface_hub import InferenceClient


class RunnerConfigError(RuntimeError):
    pass


class BaseRunner:
    def __init__(self, model_id: str, dry_run: bool = False):
        self.model_id = model_id
        self.dry_run = dry_run

    def run(self, prompt: str, timeout: int = 30, request_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError()


class LocalSLMRunner(BaseRunner):
    def __init__(self, model_id: str, endpoint_env: str = None, provider_model: str = None, dry_run: bool = False):
        super().__init__(model_id=model_id, dry_run=dry_run)
        self.endpoint_env = endpoint_env
        self.endpoint = os.environ.get(endpoint_env) if endpoint_env else None
        self.provider_model = provider_model or model_id

    def _simulate(self, prompt: str, request_id: Optional[str]) -> Dict[str, Any]:
        seed_material = f"{self.model_id}:{request_id or 'default'}:{prompt}".encode("utf-8")
        digest = hashlib.sha256(seed_material).hexdigest()
        base = int(digest[:8], 16)
        latency = 0.05 + (base % 150) / 1000.0
        numbers = [int(token) for token in re.findall(r"\d+", prompt)]
        guess = str(sum(numbers[:2])) if numbers else str(base % 10)
        time.sleep(latency)
        return {
            "text": f"Reasoning: simulated steps...\nFinal Answer: {guess}",
            "latency": latency,
            "status": "ok",
            "error": None,
            "mode": "dry_run",
        }

    def run(self, prompt: str, timeout: int = 30, request_id: Optional[str] = None) -> Dict[str, Any]:
        if self.dry_run:
            return self._simulate(prompt, request_id)
        if not self.endpoint:
            raise RunnerConfigError(
                f"Missing local endpoint for model '{self.model_id}'. Set env var '{self.endpoint_env}'."
            )
        start = time.time()
        try:
            body = {"prompt": prompt}
            if self.endpoint and "11434" in self.endpoint:
                body = {
                    "model": self.provider_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0},
                }
            response = requests.post(self.endpoint, json=body, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            text = data.get("text") or data.get("output") or data.get("response") or str(data)
            return {"text": text, "latency": time.time() - start, "status": "ok", "error": None, "mode": "live"}
        except Exception as exc:
            return {"text": None, "latency": time.time() - start, "status": "error", "error": str(exc), "mode": "live"}


class HuggingFaceRunner(BaseRunner):
    def __init__(self, model_id: str, hf_model: str = None, api_key_env: str = "HF_API_KEY", dry_run: bool = False):
        super().__init__(model_id=model_id, dry_run=dry_run)
        self.hf_model = hf_model or model_id
        self.api_key = os.environ.get(api_key_env)
        self.api_key_env = api_key_env
        self.client = InferenceClient(model=self.hf_model, token=self.api_key, provider="auto", timeout=180)

    def _simulate(self, prompt: str, request_id: Optional[str]) -> Dict[str, Any]:
        seed_material = f"{self.model_id}:{request_id or 'default'}:{prompt}".encode("utf-8")
        digest = hashlib.sha256(seed_material).hexdigest()
        latency = 0.05 + (int(digest[:8], 16) % 100) / 1000.0
        numbers = [int(token) for token in re.findall(r"\d+", prompt)]
        guess = str(sum(numbers[:2])) if numbers else "0"
        time.sleep(latency)
        return {
            "text": f"Reasoning: dry-run HF response.\nFinal Answer: {guess}",
            "latency": latency,
            "status": "ok",
            "error": None,
            "mode": "dry_run",
        }

    def run(self, prompt: str, timeout: int = 30, request_id: Optional[str] = None) -> Dict[str, Any]:
        if self.dry_run:
            return self._simulate(prompt, request_id)
        if not self.api_key:
            raise RunnerConfigError(f"Missing Hugging Face API key. Set env var '{self.api_key_env}'.")
        start = time.time()
        try:
            try:
                text = self.client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=256,
                    temperature=0.0,
                ).choices[0].message.content
            except Exception:
                text = self.client.text_generation(prompt, max_new_tokens=256, temperature=0.0)
            return {"text": text, "latency": time.time() - start, "status": "ok", "error": None, "mode": "live"}
        except Exception as exc:
            return {"text": None, "latency": time.time() - start, "status": "error", "error": str(exc), "mode": "live"}


class GeminiRunner(BaseRunner):
    def __init__(self, model_id: str, api_url_env: str = "GEMINI_API_URL", api_key_env: str = "GEMINI_API_KEY", dry_run: bool = False):
        super().__init__(model_id=model_id, dry_run=dry_run)
        api_url_env = api_url_env or "GEMINI_API_URL"
        api_key_env = api_key_env or "GEMINI_API_KEY"
        self.api_url = os.environ.get(api_url_env)
        self.api_key = os.environ.get(api_key_env)
        self.api_url_env = api_url_env
        self.api_key_env = api_key_env

    def _simulate(self, prompt: str, request_id: Optional[str]) -> Dict[str, Any]:
        seed_material = f"{self.model_id}:{request_id or 'default'}:{prompt}".encode("utf-8")
        digest = hashlib.sha256(seed_material).hexdigest()
        latency = 0.03 + (int(digest[:8], 16) % 120) / 1000.0
        numbers = [int(token) for token in re.findall(r"\d+", prompt)]
        guess = str(sum(numbers[:2])) if numbers else "0"
        time.sleep(latency)
        return {
            "text": f"Reasoning: dry-run API response.\nFinal Answer: {guess}",
            "latency": latency,
            "status": "ok",
            "error": None,
            "mode": "dry_run",
        }

    def run(self, prompt: str, timeout: int = 30, request_id: Optional[str] = None) -> Dict[str, Any]:
        if self.dry_run:
            return self._simulate(prompt, request_id)
        if not self.api_url or not self.api_key:
            raise RunnerConfigError(
                f"Missing API config for model '{self.model_id}'. Set '{self.api_url_env}' and '{self.api_key_env}'."
            )
        start = time.time()
        headers = {"Content-Type": "application/json"}
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256}}
        try:
            url = self.api_url
            separator = "&" if "?" in url else "?"
            if "key=" not in url:
                url = f"{url}{separator}key={self.api_key}"
            response = requests.post(url, json=body, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            text = None
            if isinstance(data, dict):
                text = data.get("text") or data.get("output")
                if not text and "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    parts = candidate.get("content", {}).get("parts", [])
                    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
                if not text and "choices" in data and data["choices"]:
                    text = data["choices"][0].get("text") or str(data["choices"][0])
            if not text:
                text = str(data)
            return {"text": text, "latency": time.time() - start, "status": "ok", "error": None, "mode": "live"}
        except Exception as exc:
            return {"text": None, "latency": time.time() - start, "status": "error", "error": str(exc), "mode": "live"}
