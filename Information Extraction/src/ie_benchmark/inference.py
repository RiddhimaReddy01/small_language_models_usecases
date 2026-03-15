from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from ie_benchmark.backends import GeminiBackend, OpenAICompatibleBackend
from ie_benchmark.config import InferenceConfig, ModelConfig
from ie_benchmark.prompting import build_prompt

_THREADS_CONFIGURED = False


@dataclass
class PredictionResult:
    model_name: str
    doc_id: str
    split: str
    raw_output: str
    prediction: dict[str, str]
    schema_valid: bool
    latency_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    peak_memory_mb: float | None
    backend_metadata: dict[str, Any] | None = None


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        candidate = match.group(0).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = candidate
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
            repaired = re.sub(r"([{,]\s*)(company|address|date|total)(\s*:)", r'\1"\2"\3', repaired, flags=re.IGNORECASE)
            repaired = repaired.replace("'", '"')
            repaired = repaired.replace("\n", " ")
            repaired = repaired.replace("\t", " ")
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pairs = re.findall(
                    r'"?(company|address|date|total)"?\s*:\s*(?:"([^"]*)"|([^,}\n]+))',
                    repaired,
                    flags=re.IGNORECASE,
                )
                if pairs:
                    extracted: dict[str, str] = {}
                    for key, quoted, unquoted in pairs:
                        extracted[key.lower()] = (quoted or unquoted or "").strip().strip('"')
                    return extracted

    loose_pairs = re.findall(
        r'(company|address|date|total)\s*[:=-]\s*(.+?)(?=(?:company|address|date|total)\s*[:=-]|$)',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if loose_pairs:
        return {key.lower(): value.strip().strip(",").strip() for key, value in loose_pairs}

    raise json.JSONDecodeError("No JSON object found", cleaned, 0)


def _normalize_prediction(payload: dict[str, Any], target_fields: list[str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for field in target_fields:
        value = payload.get(field, "")
        normalized[field] = "" if value is None else str(value).strip()
    return normalized


class HuggingFaceGenerator:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        global _THREADS_CONFIGURED
        self.model_config = model_config
        self.inference_config = inference_config
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Running the benchmark requires transformers and torch to be installed."
            ) from exc

        self.torch = torch
        if inference_config.torch_threads and not _THREADS_CONFIGURED:
            torch.set_num_threads(inference_config.torch_threads)
            if hasattr(torch, "set_num_interop_threads"):
                try:
                    torch.set_num_interop_threads(max(1, min(4, inference_config.torch_threads)))
                except RuntimeError:
                    pass
            _THREADS_CONFIGURED = True

        self.has_cuda = torch.cuda.is_available()
        requested_device = inference_config.device.lower()
        self.device = "cuda" if requested_device == "auto" and self.has_cuda else requested_device
        if self.device == "auto":
            self.device = "cuda" if self.has_cuda else "cpu"
        if self.device not in {"cpu", "cuda"}:
            raise ValueError(f"Unsupported device: {inference_config.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_config.model_id,
            trust_remote_code=inference_config.trust_remote_code,
        )
        if self.tokenizer.pad_token is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        model_kwargs: dict[str, Any] = {
            "trust_remote_code": inference_config.trust_remote_code,
            "low_cpu_mem_usage": inference_config.low_cpu_mem_usage,
        }
        dtype = getattr(torch, inference_config.compute_dtype, None)
        if dtype is not None and self.device == "cuda":
            model_kwargs["torch_dtype"] = dtype

        if self.device == "cuda":
            model_kwargs["device_map"] = "auto"

        if self.device == "cuda" and inference_config.quantization.lower() in {"4bit", "4-bit"}:
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as exc:
                raise RuntimeError(
                    "4-bit quantization requires a transformers build with BitsAndBytesConfig."
                ) from exc
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=inference_config.double_quantization,
                bnb_4bit_compute_dtype=dtype,
            )

        self.model = AutoModelForCausalLM.from_pretrained(model_config.model_id, **model_kwargs)
        if self.device == "cpu":
            self.model.to("cpu")
        self.model.eval()

    def _tokenize_prompt(self, prompt: str) -> dict[str, Any]:
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                rendered = self.tokenizer.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    add_generation_prompt=True,
                    tokenize=False,
                )
                return self.tokenizer(rendered, return_tensors="pt")
            except Exception:
                pass
        return self.tokenizer(prompt, return_tensors="pt")

    def predict(self, doc_id: str, split: str, text: str, target_fields: list[str]) -> PredictionResult:
        if self.inference_config.max_input_chars:
            text = text[: self.inference_config.max_input_chars]

        prompt = build_prompt(text, target_fields)
        tokenized = self._tokenize_prompt(prompt)
        tokenized = {key: value.to(self.device) for key, value in tokenized.items()}
        peak_memory_mb = None
        if self.has_cuda:
            self.torch.cuda.reset_peak_memory_stats()

        start = time.perf_counter()
        with self.torch.inference_mode():
            generated = self.model.generate(
                **tokenized,
                do_sample=self.inference_config.do_sample,
                temperature=self.inference_config.temperature,
                top_p=self.inference_config.top_p,
                max_new_tokens=self.inference_config.max_new_tokens,
                use_cache=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        latency = time.perf_counter() - start

        new_tokens = generated[0][tokenized["input_ids"].shape[1] :]
        raw_output = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        if self.has_cuda:
            peak_memory_mb = round(self.torch.cuda.max_memory_allocated() / (1024 * 1024), 2)

        schema_valid = True
        try:
            payload = _extract_json_object(raw_output)
            prediction = _normalize_prediction(payload, target_fields)
        except Exception:
            schema_valid = False
            prediction = {field: "" for field in target_fields}

        return PredictionResult(
            model_name=self.model_config.name,
            doc_id=doc_id,
            split=split,
            raw_output=raw_output,
            prediction=prediction,
            schema_valid=schema_valid,
            latency_seconds=latency,
            input_tokens=int(tokenized["input_ids"].shape[1]),
            output_tokens=int(new_tokens.shape[0]),
            peak_memory_mb=peak_memory_mb,
        )


class APIServerGenerator:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        self.model_config = model_config
        self.inference_config = inference_config
        self.backend = OpenAICompatibleBackend(model_config, inference_config)

    def predict(self, doc_id: str, split: str, text: str, target_fields: list[str]) -> PredictionResult:
        if self.inference_config.max_input_chars:
            text = text[: self.inference_config.max_input_chars]

        response = self.backend.predict(text, target_fields)
        schema_valid = True
        try:
            payload = _extract_json_object(response.raw_output)
            prediction = _normalize_prediction(payload, target_fields)
        except Exception:
            schema_valid = False
            prediction = {field: "" for field in target_fields}

        return PredictionResult(
            model_name=self.model_config.name,
            doc_id=doc_id,
            split=split,
            raw_output=response.raw_output,
            prediction=prediction,
            schema_valid=schema_valid,
            latency_seconds=response.latency_seconds,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            peak_memory_mb=response.peak_memory_mb,
            backend_metadata=response.metadata,
        )


def build_generator(model_config: ModelConfig, inference_config: InferenceConfig) -> HuggingFaceGenerator:
    if inference_config.backend == "gemini":
        return GeminiGenerator(model_config, inference_config)
    if inference_config.backend in {"ollama", "openai_compatible"}:
        return APIServerGenerator(model_config, inference_config)
    return HuggingFaceGenerator(model_config, inference_config)


class GeminiGenerator:
    def __init__(self, model_config: ModelConfig, inference_config: InferenceConfig) -> None:
        self.model_config = model_config
        self.inference_config = inference_config
        self.backend = GeminiBackend(model_config, inference_config)

    def predict(self, doc_id: str, split: str, text: str, target_fields: list[str]) -> PredictionResult:
        if self.inference_config.max_input_chars:
            text = text[: self.inference_config.max_input_chars]
        response = self.backend.predict(text, target_fields)
        schema_valid = True
        try:
            payload = _extract_json_object(response.raw_output)
            prediction = _normalize_prediction(payload, target_fields)
        except Exception:
            schema_valid = False
            prediction = {field: "" for field in target_fields}
        return PredictionResult(
            model_name=self.model_config.name,
            doc_id=doc_id,
            split=split,
            raw_output=response.raw_output,
            prediction=prediction,
            schema_valid=schema_valid,
            latency_seconds=response.latency_seconds,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            peak_memory_mb=response.peak_memory_mb,
            backend_metadata=response.metadata,
        )
