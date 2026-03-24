from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatasetConfig:
    name: str
    config_name: str
    split: str
    num_articles: int
    max_article_tokens: int
    seed: int


@dataclass
class ModelConfig:
    model_name: str
    embedding_model: str
    max_new_tokens: int
    temperature: float
    top_p: float
    do_sample: bool
    word_limit: int
    provider: str = "huggingface"
    fallback_model_name: str | None = None


@dataclass
class PromptConfig:
    template: str


@dataclass
class OutputConfig:
    output_dir: str


@dataclass
class BenchmarkConfig:
    dataset: DatasetConfig
    model: ModelConfig
    prompt: PromptConfig
    output: OutputConfig


def load_config(config_path: str | Path) -> BenchmarkConfig:
    config_data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return BenchmarkConfig(
        dataset=DatasetConfig(**config_data["dataset"]),
        model=ModelConfig(**config_data["model"]),
        prompt=PromptConfig(**config_data["prompt"]),
        output=OutputConfig(**config_data["output"]),
    )
