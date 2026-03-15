"""Configuration parsing helpers."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BenchmarkConfig:
    dataset_name: str = "squad"
    dataset_split: str = "validation"
    num_questions: int = 30
    max_context_tokens: int = 300
    max_answer_tokens: int = 10
    models: list[str] = field(
        default_factory=lambda: [
            "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "deepseek-ai/deepseek-coder-1.3b-instruct",
            "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        ]
    )
    temperature: float = 0.0
    top_p: float = 1.0
    max_new_tokens: int = 30
    do_sample: bool = False
    device: str = "cpu"
    output_dir: str = "outputs"
    save_per_model: bool = True


def to_dict(config: BenchmarkConfig) -> dict[str, Any]:
    """Serialize BenchmarkConfig to plain dict."""
    return asdict(config)


def load_config(config_path: str) -> BenchmarkConfig:
    """Load config from YAML or JSON."""
    path = Path(config_path)
    raw: dict[str, Any]
    if path.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    elif path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported config format: {path.suffix}")
    return BenchmarkConfig(**raw)
