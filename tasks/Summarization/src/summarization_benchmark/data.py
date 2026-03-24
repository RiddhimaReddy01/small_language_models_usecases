from __future__ import annotations

import re

from datasets import load_dataset

from summarization_benchmark.config import DatasetConfig


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def estimate_text_tokens(text: str) -> int:
    # A simple token estimate for API-backed models when no local tokenizer is available.
    return max(1, len(re.findall(r"\S+", text)))


def load_and_filter_samples(dataset_config: DatasetConfig, tokenizer) -> list[dict]:
    dataset = load_dataset(
        dataset_config.name,
        dataset_config.config_name,
        split=dataset_config.split,
    )
    filtered_samples: list[dict] = []

    for row in dataset.shuffle(seed=dataset_config.seed):
        article = normalize_text(row["article"])
        reference = normalize_text(row["highlights"])
        input_tokens = (
            len(tokenizer(article, truncation=False)["input_ids"])
            if tokenizer is not None
            else estimate_text_tokens(article)
        )

        if input_tokens <= dataset_config.max_article_tokens:
            filtered_samples.append(
                {
                    "id": str(row.get("id", len(filtered_samples))),
                    "article": article,
                    "reference": reference,
                    "input_tokens": input_tokens,
                }
            )

        if len(filtered_samples) >= dataset_config.num_articles:
            return filtered_samples

    raise ValueError(
        f"Only found {len(filtered_samples)} samples with <= {dataset_config.max_article_tokens} tokens. "
        "Increase the limit or reduce num_articles."
    )
