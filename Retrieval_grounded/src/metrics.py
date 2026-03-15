"""
Evaluation metrics for Retrieval-Grounded QA.
Implements capability, reliability, and operational metrics.
"""

import re
from typing import List, Optional

try:
    from transformers import AutoTokenizer
except ImportError:
    AutoTokenizer = None


def exact_match(prediction: str, reference: str) -> bool:
    """Check if prediction exactly matches reference (normalized)."""
    return normalize_answer(prediction) == normalize_answer(reference)


def normalize_answer(s: str) -> str:
    """Lowercase, remove articles, punctuation, extra whitespace."""
    s = s.lower().strip()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = " ".join(s.split())
    return s


def token_f1(prediction: str, reference: str) -> float:
    """Token-level F1 between prediction and reference."""
    pred_tokens = normalize_answer(prediction).split()
    ref_tokens = normalize_answer(reference).split()

    if not pred_tokens or not ref_tokens:
        return 1.0 if pred_tokens == ref_tokens else 0.0

    common = set(pred_tokens) & set(ref_tokens)

    if not common:
        return 0.0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def compute_em(predictions: List[str], references: List[str]) -> float:
    """Exact Match: percentage of predictions exactly matching reference."""
    if not predictions:
        return 0.0
    correct = sum(1 for p, r in zip(predictions, references) if exact_match(p, r))
    return 100.0 * correct / len(predictions)


def compute_f1(predictions: List[str], references: List[str]) -> float:
    """Average token F1 across all question-answer pairs."""
    if not predictions:
        return 0.0
    f1s = [token_f1(p, r) for p, r in zip(predictions, references)]
    return 100.0 * sum(f1s) / len(f1s)


def is_answer_in_context(answer: str, context: str) -> bool:
    """Check if answer span appears within the context (case-insensitive)."""
    if not answer or not context:
        return False
    ans_norm = normalize_answer(answer)
    ctx_norm = normalize_answer(context)
    return ans_norm in ctx_norm


def compute_context_utilization_rate(
    predictions: List[str], contexts: List[str]
) -> float:
    """Percentage of answers that appear within the provided context."""
    if not predictions:
        return 0.0
    grounded = sum(
        1 for p, c in zip(predictions, contexts) if is_answer_in_context(p, c)
    )
    return 100.0 * grounded / len(predictions)


def compute_answer_length_accuracy(
    predictions: List[str], max_tokens: int = 10, tokenizer=None
) -> float:
    """Percentage of answers within the allowed token length."""
    if not predictions:
        return 0.0

    def token_count(s: str) -> int:
        if tokenizer is not None:
            return len(tokenizer.encode(s, add_special_tokens=False))
        return len(s.split())

    within_limit = sum(1 for p in predictions if token_count(p.strip()) <= max_tokens)
    return 100.0 * within_limit / len(predictions)


def is_hallucinated(prediction: str, context: str) -> bool:
    """Answer not present in context -> hallucination."""
    if not prediction or not prediction.strip():
        return False
    return not is_answer_in_context(prediction, context)


def compute_hallucination_rate(
    predictions: List[str], contexts: List[str]
) -> float:
    """Percentage of answers not grounded in context."""
    if not predictions:
        return 0.0
    hallucinated = sum(
        1 for p, c in zip(predictions, contexts) if is_hallucinated(p, c)
    )
    return 100.0 * hallucinated / len(predictions)


def is_unsupported(prediction: str, context: str) -> bool:
    """Claim not supported by context (same as hallucination for this task)."""
    return is_hallucinated(prediction, context)


def compute_unsupported_answer_rate(
    predictions: List[str], contexts: List[str]
) -> float:
    """Percentage of answers unsupported by context."""
    return compute_hallucination_rate(predictions, contexts)


def is_partial_answer(prediction: str, reference: str) -> bool:
    """Prediction overlaps with reference but is incomplete (partial match)."""
    pred_norm = normalize_answer(prediction)
    ref_norm = normalize_answer(reference)
    if pred_norm == ref_norm:
        return False
    if not pred_norm or not ref_norm:
        return False
    if pred_norm in ref_norm:
        return True
    f1 = token_f1(prediction, reference)
    return 0 < f1 < 1.0


def compute_partial_answer_rate(
    predictions: List[str], references: List[str]
) -> float:
    """Percentage of answers that are partial/incomplete."""
    if not predictions:
        return 0.0
    partial = sum(
        1 for p, r in zip(predictions, references)
        if is_partial_answer(p, r)
    )
    return 100.0 * partial / len(predictions)


def compute_all_metrics(
    predictions: List[str],
    references: List[str],
    contexts: List[str],
    max_answer_tokens: int = 10,
    tokenizer=None,
) -> dict:
    """Compute all capability, reliability, and operational metrics."""
    if tokenizer is None and AutoTokenizer is not None:
        try:
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        except Exception:
            tokenizer = None

    return {
        "em": compute_em(predictions, references),
        "f1": compute_f1(predictions, references),
        "context_utilization_rate": compute_context_utilization_rate(
            predictions, contexts
        ),
        "answer_length_accuracy": compute_answer_length_accuracy(
            predictions, max_answer_tokens, tokenizer
        ),
        "hallucination_rate": compute_hallucination_rate(predictions, contexts),
        "unsupported_answer_rate": compute_unsupported_answer_rate(
            predictions, contexts
        ),
        "partial_answer_rate": compute_partial_answer_rate(predictions, references),
    }


def add_operational_metrics(
    results: dict,
    latencies_ms: List[float],
    output_tokens: List[int],
    input_tokens: List[int],
    memory_mb: Optional[float] = None,
) -> dict:
    """Add operational metrics to results dict."""
    n = len(latencies_ms)
    if n > 0:
        results["latency_ms"] = sum(latencies_ms) / n
        results["latency_p50_ms"] = sorted(latencies_ms)[n // 2]
        results["latency_p95_ms"] = sorted(latencies_ms)[int(0.95 * n)] if n >= 20 else latencies_ms[-1]
    if output_tokens and sum(output_tokens) > 0:
        total_time_sec = sum(latencies_ms) / 1000.0
        results["tokens_per_sec"] = sum(output_tokens) / total_time_sec if total_time_sec > 0 else 0
        results["output_tokens_total"] = sum(output_tokens)
    if input_tokens:
        results["input_tokens_avg"] = sum(input_tokens) / len(input_tokens)
    if memory_mb is not None:
        results["memory_mb"] = memory_mb
    return results
