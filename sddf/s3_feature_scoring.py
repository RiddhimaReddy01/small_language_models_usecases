from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_FORMAT_KEYWORDS = {
    "json",
    "yaml",
    "xml",
    "csv",
    "table",
    "schema",
    "markdown",
    "bullet",
    "list",
    "columns",
}
_CONSTRAINT_MARKERS = {
    "must",
    "should",
    "exactly",
    "at least",
    "at most",
    "do not",
    "cannot",
    "required",
    "only",
}
_HIGH_STAKES_TERMS = {
    "medical",
    "health",
    "diagnosis",
    "clinical",
    "legal",
    "compliance",
    "financial",
    "fraud",
    "safety",
    "security",
    "critical",
}
_SENSITIVE_TERMS = {
    "ssn",
    "social security",
    "passport",
    "credit card",
    "bank account",
    "patient",
    "hipaa",
    "phi",
    "pii",
    "personal data",
    "gdpr",
}


def _clip_1_to_5(value: float) -> int:
    return max(1, min(5, int(round(value))))


def _count_any(text_lower: str, cues: set[str]) -> int:
    return sum(1 for cue in cues if cue in text_lower)


def _token_count(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+", text))


def score_task_complexity(task: str, prompt: str) -> int:
    """
    TC (1-5): complexity from prompt length, constraints, and symbolic/algorithmic load.
    """
    text = (prompt or "").strip()
    lower = text.lower()
    n_tokens = _token_count(text)
    constraint_hits = _count_any(lower, _CONSTRAINT_MARKERS)
    algorithm_hits = len(re.findall(r"\b(algorithm|proof|optimi[sz]e|derive|complexity|multi-step)\b", lower))
    symbol_hits = len(re.findall(r"[\=\+\-\*/\^%<>]", text))

    raw = (
        1.0
        + min(2.0, n_tokens / 120.0)
        + min(1.0, constraint_hits / 4.0)
        + min(1.0, algorithm_hits / 3.0)
        + min(1.0, symbol_hits / 20.0)
    )

    # Task priors.
    if task in {"maths", "code_generation", "retrieval_grounded"}:
        raw += 0.4
    elif task in {"classification", "summarization"}:
        raw -= 0.2

    return _clip_1_to_5(raw)


def score_output_structure(prompt: str, expected_format: str | None = None) -> int:
    """
    OS (1-5): strictness/structure of expected output format.
    """
    text = (prompt or "") + " " + (expected_format or "")
    lower = text.lower()
    format_hits = _count_any(lower, _FORMAT_KEYWORDS)
    delimiter_hits = len(re.findall(r"[\{\}\[\],:|]", text))
    ordering_hits = len(re.findall(r"\b(first|second|third|step|ordered|sorted)\b", lower))

    raw = 1.0 + min(2.2, format_hits / 2.0) + min(1.0, delimiter_hits / 40.0) + min(1.0, ordering_hits / 3.0)
    return _clip_1_to_5(raw)


def score_stakes(
    task: str,
    prompt: str,
    business_critical: bool = False,
    requires_human_approval: bool = False,
) -> int:
    """
    SK (1-5): consequence severity if wrong. Keep manager override available.
    """
    lower = (prompt or "").lower()
    high_stakes_hits = _count_any(lower, _HIGH_STAKES_TERMS)
    raw = 1.0 + min(2.0, high_stakes_hits / 2.0)

    if task in {"maths", "code_generation"}:
        raw += 0.4
    if business_critical:
        raw += 1.2
    if requires_human_approval:
        raw += 0.6

    return _clip_1_to_5(raw)


def score_data_sensitivity(
    prompt: str,
    data_classification: str = "internal",
    contains_pii: bool = False,
    contains_phi: bool = False,
) -> int:
    """
    DS (1-5): sensitivity from classification + explicit indicators.
    """
    lower = (prompt or "").lower()
    sensitive_hits = _count_any(lower, _SENSITIVE_TERMS)

    class_base = {
        "public": 1.0,
        "internal": 2.0,
        "confidential": 3.2,
        "restricted": 4.2,
    }.get((data_classification or "internal").strip().lower(), 2.0)

    raw = class_base + min(1.0, sensitive_hits / 2.0)
    if contains_pii:
        raw += 0.8
    if contains_phi:
        raw += 1.0
    return _clip_1_to_5(raw)


def score_latency_tolerance(target_p99_ms: int | None = None, real_time: bool = False) -> int:
    """
    LT (1-5): tighter latency tolerance => higher score.
    """
    if target_p99_ms is None:
        return 4 if real_time else 3
    if target_p99_ms <= 300:
        return 5
    if target_p99_ms <= 800:
        return 4
    if target_p99_ms <= 2000:
        return 3
    if target_p99_ms <= 5000:
        return 2
    return 1


def score_volume_load(
    qps: float | None = None,
    daily_requests: int | None = None,
    bursty: bool = False,
) -> int:
    """
    VL (1-5): traffic/scale pressure.
    """
    signal = 0.0
    if qps is not None:
        if qps >= 500:
            signal = max(signal, 5.0)
        elif qps >= 100:
            signal = max(signal, 4.0)
        elif qps >= 20:
            signal = max(signal, 3.0)
        elif qps >= 5:
            signal = max(signal, 2.0)
        else:
            signal = max(signal, 1.0)
    if daily_requests is not None:
        if daily_requests >= 10_000_000:
            signal = max(signal, 5.0)
        elif daily_requests >= 1_000_000:
            signal = max(signal, 4.0)
        elif daily_requests >= 100_000:
            signal = max(signal, 3.0)
        elif daily_requests >= 10_000:
            signal = max(signal, 2.0)
        else:
            signal = max(signal, 1.0)
    if signal == 0.0:
        signal = 2.0
    if bursty:
        signal += 0.6
    return _clip_1_to_5(signal)


@dataclass(frozen=True)
class S3ScoringInput:
    task: str
    prompt: str
    expected_format: str | None = None
    business_critical: bool = False
    requires_human_approval: bool = False
    data_classification: str = "internal"
    contains_pii: bool = False
    contains_phi: bool = False
    target_p99_ms: int | None = None
    real_time: bool = False
    qps: float | None = None
    daily_requests: int | None = None
    bursty: bool = False
    overrides: dict[str, int] | None = None


def score_s3_dimensions(payload: S3ScoringInput | dict[str, Any]) -> dict[str, int]:
    """
    Compute TC/OS/SK/DS/LT/VL from task metadata + optional manager overrides.
    """
    if isinstance(payload, dict):
        cfg = S3ScoringInput(**payload)
    else:
        cfg = payload

    scores = {
        "TC": score_task_complexity(task=cfg.task, prompt=cfg.prompt),
        "OS": score_output_structure(prompt=cfg.prompt, expected_format=cfg.expected_format),
        "SK": score_stakes(
            task=cfg.task,
            prompt=cfg.prompt,
            business_critical=cfg.business_critical,
            requires_human_approval=cfg.requires_human_approval,
        ),
        "DS": score_data_sensitivity(
            prompt=cfg.prompt,
            data_classification=cfg.data_classification,
            contains_pii=cfg.contains_pii,
            contains_phi=cfg.contains_phi,
        ),
        "LT": score_latency_tolerance(target_p99_ms=cfg.target_p99_ms, real_time=cfg.real_time),
        "VL": score_volume_load(qps=cfg.qps, daily_requests=cfg.daily_requests, bursty=cfg.bursty),
    }

    for key, value in (cfg.overrides or {}).items():
        if key in scores:
            scores[key] = _clip_1_to_5(float(value))
    return scores

