from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from ie_benchmark.config import BenchmarkConfig


@dataclass
class Example:
    doc_id: str
    text: str
    fields: dict[str, str]
    split: str


def _read_jsonl(path: Path, split: str) -> list[Example]:
    if not path.exists():
        if split == "noisy":
            return []
        raise FileNotFoundError(f"Dataset file not found: {path}")
    examples: list[Example] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = json.loads(line)
            if "text" not in payload or "fields" not in payload:
                raise ValueError(f"Invalid record at {path}:{line_number}")
            examples.append(
                Example(
                    doc_id=str(payload.get("id", f"{split}_{line_number:05d}")),
                    text=str(payload["text"]),
                    fields={str(k): "" if v is None else str(v) for k, v in payload["fields"].items()},
                    split=str(payload.get("split", split)),
                )
            )
    return examples


def load_and_sample_dataset(config: BenchmarkConfig) -> list[Example]:
    clean_examples = _read_jsonl(Path(config.dataset.clean_path), "clean")
    noisy_examples = _read_jsonl(Path(config.dataset.noisy_path), "noisy") if config.dataset.noisy_path else []
    rng = random.Random(config.sampling.random_seed)

    if clean_examples:
        rng.shuffle(clean_examples)
    if noisy_examples:
        rng.shuffle(noisy_examples)

    if config.sampling.clean_sample_size is not None or config.sampling.noisy_sample_size is not None:
        clean_n = config.sampling.clean_sample_size or 0
        noisy_n = config.sampling.noisy_sample_size or 0
        sampled = clean_examples[:clean_n] + noisy_examples[:noisy_n]
    else:
        combined = clean_examples + noisy_examples
        rng.shuffle(combined)
        sampled = combined[: config.sampling.sample_size]

    if not sampled:
        raise ValueError("No sampled examples were loaded. Check dataset paths and sample sizes.")
    return sampled
