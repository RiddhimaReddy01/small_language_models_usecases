from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DatasetConfig:
    name: str
    clean_path: str
    noisy_path: str | None
    target_fields: list[str]


@dataclass
class SamplingConfig:
    sample_size: int
    sampling_method: str
    random_seed: int
    clean_sample_size: int | None = None
    noisy_sample_size: int | None = None


@dataclass
class ModelConfig:
    name: str
    model_id: str
    backend_model: str | None = None


@dataclass
class InferenceConfig:
    device: str
    quantization: str
    double_quantization: bool
    compute_dtype: str
    temperature: float
    do_sample: bool
    top_p: float
    max_new_tokens: int
    backend: str = "huggingface"
    max_input_chars: int | None = None
    torch_threads: int | None = None
    low_cpu_mem_usage: bool = True
    trust_remote_code: bool = False
    api_base: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 120


@dataclass
class EvaluationConfig:
    runs_per_model: int
    required_output_format: str
    date_format: str


@dataclass
class BenchmarkConfig:
    benchmark_name: str
    dataset: DatasetConfig
    sampling: SamplingConfig
    models: list[ModelConfig]
    inference: InferenceConfig
    evaluation: EvaluationConfig
    output_dir: str


def _load_raw_config(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML config requires PyYAML to be installed.") from exc
        return yaml.safe_load(text)
    raise ValueError(f"Unsupported config format: {path.suffix}")


def load_config(config_path: str) -> BenchmarkConfig:
    path = Path(config_path)
    raw = _load_raw_config(path)
    return BenchmarkConfig(
        benchmark_name=raw["benchmark_name"],
        dataset=DatasetConfig(**raw["dataset"]),
        sampling=SamplingConfig(**raw["sampling"]),
        models=[ModelConfig(**item) for item in raw["models"]],
        inference=InferenceConfig(**raw["inference"]),
        evaluation=EvaluationConfig(**raw["evaluation"]),
        output_dir=raw["output_dir"],
    )
