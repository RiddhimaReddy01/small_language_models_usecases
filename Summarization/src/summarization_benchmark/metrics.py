from __future__ import annotations

import re

import torch
from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def extract_keywords(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\b[A-Za-z][A-Za-z0-9'-]{2,}\b", text)
        if token.lower() not in {"the", "and", "for", "that", "with", "from", "this", "were", "have"}
    }


def extract_named_like_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b(?:[A-Z][a-z]+|[0-9][0-9,./:-]*)\b", text))


def compute_hallucination_flag(article: str, summary: str) -> int:
    article_tokens = {token.lower() for token in extract_named_like_tokens(article)}
    summary_tokens = {token.lower() for token in extract_named_like_tokens(summary)}
    return int(len(summary_tokens - article_tokens) > 0)


def compute_information_loss_flag(reference: str, summary: str) -> int:
    reference_keywords = extract_keywords(reference)
    if not reference_keywords:
        return 0
    summary_keywords = extract_keywords(summary)
    retained_ratio = len(reference_keywords & summary_keywords) / len(reference_keywords)
    return int(retained_ratio < 0.5)


class MetricSuite:
    def __init__(self, embedding_model_name: str) -> None:
        self.rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        self.embedder = SentenceTransformer(embedding_model_name)

    def score(self, article: str, reference: str, summary: str, word_limit: int) -> dict:
        rouge_scores = self.rouge.score(reference, summary)
        embeddings = self.embedder.encode([reference, summary], convert_to_tensor=True)
        semantic_similarity = torch.nn.functional.cosine_similarity(
            embeddings[0].unsqueeze(0),
            embeddings[1].unsqueeze(0),
        ).item()

        article_words = word_count(article)
        summary_words = word_count(summary)

        return {
            "article_words": article_words,
            "reference_words": word_count(reference),
            "summary_words": summary_words,
            "rouge_1_f1": rouge_scores["rouge1"].fmeasure,
            "rouge_2_f1": rouge_scores["rouge2"].fmeasure,
            "rouge_l_f1": rouge_scores["rougeL"].fmeasure,
            "semantic_similarity": semantic_similarity,
            "compression_ratio": (summary_words / article_words) if article_words > 0 else 0.0,
            "hallucination_flag": compute_hallucination_flag(article, summary),
            "length_violation_flag": int(summary_words > word_limit),
            "information_loss_flag": compute_information_loss_flag(reference, summary),
        }
