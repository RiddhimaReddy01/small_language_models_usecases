"""
Dataset loading and sampling for Retrieval-Grounded QA.
Supports SQuAD (default) and Natural Questions.
"""

import re
from dataclasses import dataclass
from typing import Optional

from datasets import load_dataset


@dataclass
class QAExample:
    """Single QA example with context, question, and reference answer."""
    id: str
    context: str
    question: str
    answer: str
    dataset: str = "squad"


def _truncate_to_tokens(text: str, max_tokens: int, tokenizer=None) -> str:
    """Truncate text to approximately max_tokens. Uses simple word split if no tokenizer."""
    if tokenizer is not None:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text
        decoded = tokenizer.decode(tokens[:max_tokens], skip_special_tokens=True)
        return decoded.strip()
    # Fallback: ~4 chars per token for English
    words = text.split()
    approx_chars = max_tokens * 4
    if len(text) <= approx_chars:
        return text
    result = ""
    for w in words:
        if len(result) + len(w) + 1 > approx_chars:
            break
        result += (" " if result else "") + w
    return result.strip()


def load_squad(split: str = "validation", max_examples: Optional[int] = 30) -> list[QAExample]:
    """Load SQuAD dataset and return QA examples."""
    ds = load_dataset("rajpurkar/squad", split=split)
    examples = []
    seen = set()
    for i, ex in enumerate(ds):
        if max_examples and len(examples) >= max_examples:
            break
        answers = ex.get("answers", {})
        texts = answers.get("text", [])
        if not texts:
            continue
        answer = texts[0].strip()
        if not answer:
            continue
        # Skip duplicate contexts
        key = (ex["context"][:100], ex["question"])
        if key in seen:
            continue
        seen.add(key)
        examples.append(QAExample(
            id=ex.get("id", str(i)),
            context=ex["context"],
            question=ex["question"],
            answer=answer,
            dataset="squad"
        ))
    return examples


def load_natural_questions(max_examples: Optional[int] = 30) -> list[QAExample]:
    """
    Load Natural Questions. Uses LLukas22/nq-simplified (SQuAD-like, ~138MB).
    Falls back to SQuAD if NQ is unavailable.
    """
    try:
        ds = load_dataset("LLukas22/nq-simplified", split="validation")
        examples = []
        seen = set()
        for i, ex in enumerate(ds):
            if max_examples and len(examples) >= max_examples:
                break
            answers = ex.get("answers", {})
            texts = answers.get("text", [])
            if not texts:
                continue
            answer = texts[0].strip()
            if not answer:
                continue
            key = (ex["context"][:100], ex["question"])
            if key in seen:
                continue
            seen.add(key)
            examples.append(QAExample(
                id=ex.get("id", str(i)),
                context=ex["context"],
                question=ex["question"],
                answer=answer,
                dataset="natural_questions"
            ))
        return examples if examples else load_squad("validation", max_examples)
    except Exception:
        return load_squad("validation", max_examples)


def sample_dataset(
    dataset_name: str = "squad",
    n_questions: int = 30,
    max_context_tokens: int = 300,
    max_answer_tokens: int = 10,
    tokenizer=None,
) -> list[QAExample]:
    """
    Sample dataset with CPU-friendly constraints:
    - n_questions: number of QA pairs
    - max_context_tokens: truncate context to ≤ N tokens
    - max_answer_tokens: filter out examples where reference answer exceeds N tokens
    """
    if dataset_name.lower() in ("nq", "natural_questions", "naturalquestions"):
        raw = load_natural_questions(max_examples=n_questions * 3)  # Over-sample for filtering
    else:
        raw = load_squad("validation", max_examples=n_questions * 3)

    sampled = []
    for ex in raw:
        if len(sampled) >= n_questions:
            break
        # Filter by answer length
        ans_tokens = len(ex.answer.split()) if not tokenizer else len(
            tokenizer.encode(ex.answer, add_special_tokens=False)
        )
        if ans_tokens > max_answer_tokens:
            continue
        # Truncate context
        context = _truncate_to_tokens(ex.context, max_context_tokens, tokenizer)
        sampled.append(QAExample(
            id=ex.id,
            context=context,
            question=ex.question,
            answer=ex.answer,
            dataset=ex.dataset,
        ))
    return sampled[:n_questions]
