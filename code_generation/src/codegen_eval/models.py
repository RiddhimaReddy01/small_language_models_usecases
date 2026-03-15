from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from .prompts import extract_code
from .types import GenerationConfig, GenerationResult, ModelSpec


def _estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))


LLAMA_CONTEXT_PRESETS: dict[str, dict[str, int]] = {
    "fast_cpu": {"n_ctx": 1024, "n_batch": 192, "n_ubatch": 96},
    "small": {"n_ctx": 1536, "n_batch": 224, "n_ubatch": 112},
    "balanced": {"n_ctx": 2048, "n_batch": 256, "n_ubatch": 128},
}


class BaseModelAdapter(ABC):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        self.spec = spec
        self.generation = generation

    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        raise NotImplementedError

    def _effective_max_new_tokens(self, prompt: str) -> int:
        configured_max = max(1, int(self.generation.max_new_tokens))
        minimum = max(1, min(int(self.generation.min_new_tokens), configured_max))
        profile = self.generation.profile.lower().strip()

        if profile == "fast_cpu":
            configured_max = min(configured_max, 128)
            minimum = min(minimum, configured_max)

        if not self.generation.adaptive_max_new_tokens:
            return configured_max

        prompt_tokens = _estimate_token_count(prompt)
        if prompt_tokens <= 75:
            adaptive_target = 64
        elif prompt_tokens <= 120:
            adaptive_target = 80
        elif prompt_tokens <= 170:
            adaptive_target = 96
        else:
            adaptive_target = configured_max

        if profile == "fast_cpu":
            adaptive_target = min(adaptive_target, 96)

        return max(minimum, min(configured_max, adaptive_target))

    def _llama_context_settings(self) -> dict[str, int]:
        preset_name = str(self.spec.extra.get("context_preset", "")).strip().lower()
        settings = dict(LLAMA_CONTEXT_PRESETS.get(preset_name, {}))
        for key in ("n_ctx", "n_batch", "n_ubatch"):
            if key in self.spec.extra:
                settings[key] = int(self.spec.extra[key])
        return settings


class HuggingFaceLocalAdapter(BaseModelAdapter):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        super().__init__(spec, generation)
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - dependency gated
            raise RuntimeError(
                "Local model support requires `transformers`, `torch`, and `accelerate`."
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(spec.model_name)

        model_kwargs = {"device_map": "auto"}
        if spec.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as exc:  # pragma: no cover - dependency gated
                raise RuntimeError("4-bit loading requires bitsandbytes support.") from exc

            model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)

        self._model = AutoModelForCausalLM.from_pretrained(spec.model_name, **model_kwargs)

    def generate(self, prompt: str) -> GenerationResult:
        prompt_text = prompt
        if self.spec.use_chat_template and hasattr(self._tokenizer, "apply_chat_template"):
            prompt_text = self._tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )

        inputs = self._tokenizer(prompt_text, return_tensors="pt")
        if hasattr(self._model, "device"):
            inputs = {key: value.to(self._model.device) for key, value in inputs.items()}

        max_new_tokens = self._effective_max_new_tokens(prompt)
        start = time.perf_counter()
        with self._torch.inference_mode():
            outputs = self._model.generate(
                **inputs,
                do_sample=self.generation.temperature > 0,
                temperature=self.generation.temperature,
                top_p=self.generation.top_p,
                max_new_tokens=max_new_tokens,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        latency = time.perf_counter() - start

        generated_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
        raw_text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
        output_tokens = int(generated_tokens.shape[-1])
        input_tokens = int(inputs["input_ids"].shape[-1])

        return GenerationResult(
            raw_text=raw_text,
            code=extract_code(raw_text),
            latency_seconds=latency,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / latency if latency > 0 else 0.0,
            input_tokens=input_tokens,
            output_cost=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1000.0) * self.spec.input_cost_per_1k_tokens
            + (output_tokens / 1000.0) * self.spec.output_cost_per_1k_tokens
        )


class GeminiAdapter(BaseModelAdapter):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        super().__init__(spec, generation)
        self._sdk_mode = None
        self._client = None
        api_key = os.getenv(spec.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing required API key in environment variable {spec.api_key_env}.")

        try:
            from google import genai

            self._sdk_mode = "genai"
            self._genai = genai
            self._client = genai.Client(api_key=api_key)
        except ImportError:
            try:
                import google.generativeai as legacy_genai

                self._sdk_mode = "legacy"
                legacy_genai.configure(api_key=api_key)
                self._client = legacy_genai.GenerativeModel(spec.model_name)
            except ImportError as exc:  # pragma: no cover - dependency gated
                raise RuntimeError(
                    "Gemini support requires `google-genai` or `google-generativeai`."
                ) from exc

    def generate(self, prompt: str) -> GenerationResult:
        max_new_tokens = self._effective_max_new_tokens(prompt)
        start = time.perf_counter()
        if self._sdk_mode == "genai":
            response = self._client.models.generate_content(
                model=self.spec.model_name,
                contents=prompt,
                config={
                    "temperature": self.generation.temperature,
                    "top_p": self.generation.top_p,
                    "max_output_tokens": max_new_tokens,
                },
            )
            raw_text = response.text or ""
            usage = getattr(response, "usage_metadata", None)
            input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        else:
            response = self._client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.generation.temperature,
                    "top_p": self.generation.top_p,
                    "max_output_tokens": max_new_tokens,
                },
            )
            raw_text = getattr(response, "text", "") or ""
            usage = getattr(response, "usage_metadata", None)
            input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
            output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)

        latency = time.perf_counter() - start
        if output_tokens <= 0:
            output_tokens = _estimate_token_count(raw_text)
        if input_tokens <= 0:
            input_tokens = _estimate_token_count(prompt)

        return GenerationResult(
            raw_text=raw_text,
            code=extract_code(raw_text),
            latency_seconds=latency,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / latency if latency > 0 else 0.0,
            input_tokens=input_tokens,
            output_cost=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1000.0) * self.spec.input_cost_per_1k_tokens
            + (output_tokens / 1000.0) * self.spec.output_cost_per_1k_tokens
        )


class HuggingFaceApiAdapter(BaseModelAdapter):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        super().__init__(spec, generation)
        token_env = spec.api_key_env or "HF_TOKEN"
        token = os.getenv(token_env)
        if not token:
            raise RuntimeError(f"Missing required API key in environment variable {token_env}.")

        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:  # pragma: no cover - dependency gated
            raise RuntimeError("Hugging Face API support requires `huggingface_hub`.") from exc

        self._client = InferenceClient(model=spec.model_name, token=token, provider="auto", timeout=300)

    def generate(self, prompt: str) -> GenerationResult:
        max_new_tokens = self._effective_max_new_tokens(prompt)
        start = time.perf_counter()
        try:
            raw_text = self._client.text_generation(
                prompt,
                model=self.spec.model_name,
                max_new_tokens=max_new_tokens,
                temperature=self.generation.temperature,
                top_p=self.generation.top_p,
                do_sample=self.generation.temperature > 0,
                return_full_text=False,
                seed=self.generation.seed,
                details=False,
            )
        except Exception as text_exc:
            try:
                response = self._client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.spec.model_name,
                    max_tokens=max_new_tokens,
                    temperature=self.generation.temperature,
                    top_p=self.generation.top_p,
                    seed=self.generation.seed,
                )
                raw_text = self._extract_chat_text(response)
            except Exception as chat_exc:
                raise RuntimeError(str(chat_exc) or str(text_exc)) from chat_exc

        latency = time.perf_counter() - start
        raw_text = str(raw_text)
        output_tokens = _estimate_token_count(raw_text)
        input_tokens = _estimate_token_count(prompt)

        return GenerationResult(
            raw_text=raw_text,
            code=extract_code(raw_text),
            latency_seconds=latency,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / latency if latency > 0 else 0.0,
            input_tokens=input_tokens,
            output_cost=self._estimate_cost(input_tokens, output_tokens),
        )

    def _extract_chat_text(self, response: object) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
            return "\n".join(parts)
        return str(content or "")

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1000.0) * self.spec.input_cost_per_1k_tokens
            + (output_tokens / 1000.0) * self.spec.output_cost_per_1k_tokens
        )


class OllamaAdapter(BaseModelAdapter):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        super().__init__(spec, generation)
        self._base_url = str(spec.extra.get("base_url", "http://127.0.0.1:11434")).rstrip("/")

    def generate(self, prompt: str) -> GenerationResult:
        max_new_tokens = self._effective_max_new_tokens(prompt)
        payload = {
            "model": self.spec.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.generation.temperature,
                "top_p": self.generation.top_p,
                "num_predict": max_new_tokens,
                "seed": self.generation.seed,
            },
        }
        start = time.perf_counter()
        response = requests.post(f"{self._base_url}/api/generate", json=payload, timeout=600)
        latency = time.perf_counter() - start
        response.raise_for_status()
        data = response.json()

        raw_text = str(data.get("response", "") or "")
        output_tokens = int(data.get("eval_count") or _estimate_token_count(raw_text))
        input_tokens = int(data.get("prompt_eval_count") or _estimate_token_count(prompt))

        return GenerationResult(
            raw_text=raw_text,
            code=extract_code(raw_text),
            latency_seconds=latency,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / latency if latency > 0 else 0.0,
            input_tokens=input_tokens,
            output_cost=0.0,
        )


class LlamaCppAdapter(BaseModelAdapter):
    def __init__(self, spec: ModelSpec, generation: GenerationConfig) -> None:
        super().__init__(spec, generation)
        try:
            from llama_cpp import Llama
        except ImportError as exc:  # pragma: no cover - dependency gated
            raise RuntimeError("`llama-cpp-python` is required for llama.cpp local inference.") from exc

        model_path = str(spec.extra.get("model_path") or spec.model_name).strip()
        if not model_path:
            raise RuntimeError("llama.cpp models require `extra.model_path` or a GGUF file path in `model_name`.")

        resolved_model_path = Path(model_path)
        if not resolved_model_path.exists():
            raise RuntimeError(f"GGUF model file not found: {resolved_model_path}")

        cpu_count = os.cpu_count() or 1
        context_settings = self._llama_context_settings()
        n_threads = int(spec.extra.get("n_threads", max(1, cpu_count - 1)))
        n_threads_batch = int(spec.extra.get("n_threads_batch", n_threads))
        n_ctx = int(context_settings.get("n_ctx", 2048))
        n_batch = int(context_settings.get("n_batch", min(512, n_ctx)))
        n_ubatch = int(context_settings.get("n_ubatch", min(512, n_batch)))
        n_gpu_layers = int(spec.extra.get("n_gpu_layers", 0))
        verbose = bool(spec.extra.get("verbose", False))

        self._stop = [str(item) for item in spec.extra.get("stop", [])]
        self._use_chat_completion = bool(spec.use_chat_template or spec.extra.get("chat_format"))

        llama_kwargs = {
            "model_path": str(resolved_model_path),
            "n_ctx": n_ctx,
            "n_threads": n_threads,
            "n_threads_batch": n_threads_batch,
            "n_batch": n_batch,
            "n_ubatch": n_ubatch,
            "n_gpu_layers": n_gpu_layers,
            "use_mmap": bool(spec.extra.get("use_mmap", True)),
            "use_mlock": bool(spec.extra.get("use_mlock", False)),
            "verbose": verbose,
        }

        if "chat_format" in spec.extra:
            llama_kwargs["chat_format"] = str(spec.extra["chat_format"])
        if "flash_attn" in spec.extra:
            llama_kwargs["flash_attn"] = bool(spec.extra["flash_attn"])

        self._llama = Llama(**llama_kwargs)

    def generate(self, prompt: str) -> GenerationResult:
        max_new_tokens = self._effective_max_new_tokens(prompt)
        start = time.perf_counter()
        if self._use_chat_completion:
            response = self._llama.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.generation.temperature,
                top_p=self.generation.top_p,
                max_tokens=max_new_tokens,
                seed=self.generation.seed,
                stop=self._stop or None,
            )
            raw_text = self._extract_chat_text(response)
            usage = response.get("usage", {})
        else:
            response = self._llama(
                prompt,
                temperature=self.generation.temperature,
                top_p=self.generation.top_p,
                max_tokens=max_new_tokens,
                seed=self.generation.seed,
                stop=self._stop or None,
                echo=False,
            )
            raw_text = self._extract_text_completion(response)
            usage = response.get("usage", {})

        latency = time.perf_counter() - start
        output_tokens = int(usage.get("completion_tokens") or _estimate_token_count(raw_text))
        input_tokens = int(usage.get("prompt_tokens") or _estimate_token_count(prompt))

        return GenerationResult(
            raw_text=raw_text,
            code=extract_code(raw_text),
            latency_seconds=latency,
            output_tokens=output_tokens,
            tokens_per_second=output_tokens / latency if latency > 0 else 0.0,
            input_tokens=input_tokens,
            output_cost=0.0,
        )

    def _extract_text_completion(self, response: dict) -> str:
        choices = response.get("choices", [])
        if not choices:
            return ""
        return str(choices[0].get("text", "") or "")

    def _extract_chat_text(self, response: dict) -> str:
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content or "")


def create_model_adapter(spec: ModelSpec, generation: GenerationConfig) -> BaseModelAdapter:
    kind = spec.kind.lower()
    if kind in {"hf_local", "transformers", "local"}:
        return HuggingFaceLocalAdapter(spec, generation)
    if kind in {"llama_cpp", "llama.cpp", "llamacpp"}:
        return LlamaCppAdapter(spec, generation)
    if kind in {"hf_api", "huggingface_api", "inference_api"}:
        return HuggingFaceApiAdapter(spec, generation)
    if kind in {"ollama"}:
        return OllamaAdapter(spec, generation)
    if kind in {"gemini", "google"}:
        return GeminiAdapter(spec, generation)
    raise ValueError(f"Unsupported model kind: {spec.kind}")
