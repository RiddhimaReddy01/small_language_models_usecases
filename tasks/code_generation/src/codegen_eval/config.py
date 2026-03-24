from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .types import EvaluationConfig, GenerationConfig, ModelSpec, RunConfig


def _read_config_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def load_run_config(path: str | Path) -> RunConfig:
    config_path = Path(path)
    raw = _read_config_file(config_path)

    evaluation = EvaluationConfig(**raw.get("evaluation", {}))
    generation = GenerationConfig(**raw.get("generation", {}))
    models = [ModelSpec(**item) for item in raw.get("models", [])]

    if not models:
        raise ValueError("Configuration must include at least one model.")

    return RunConfig(evaluation=evaluation, generation=generation, models=models)
