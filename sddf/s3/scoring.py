from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Format keywords for output structure scoring
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

# Constraint markers for task complexity
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

# High stakes terms for stakes scoring
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

# Sensitive data terms for data sensitivity scoring
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

# Default S3 dimension weights
DEFAULT_S3_WEIGHTS: dict[str, int] = {
    "TC": 3,
    "OS": 2,
    "SK": 4,
    "DS": 2,
    "LT": 3,
    "VL": 1,
}

_REQ_DIMS: tuple[str, ...] = ("TC", "OS", "SK", "DS", "LT", "VL")


@dataclass(frozen=True)
class S3ScoringInput:
    """Input dataclass for S3 dimension scoring."""
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


def _clip_1_to_5(value: float) -> int:
    """Clip value to [1, 5] range and round."""
    return max(1, min(5, int(round(value))))


def _count_any(text_lower: str, cues: set[str]) -> int:
    """Count occurrences of any cue in text."""
    return sum(1 for cue in cues if cue in text_lower)


def _token_count(text: str) -> int:
    """Count tokens (word-like sequences) in text."""
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


def normalize_weights(weights: dict[str, Any] | None) -> dict[str, int]:
    """
    Validate and normalize S3 dimension weights.
    """
    src = dict(DEFAULT_S3_WEIGHTS if weights is None else weights)
    out: dict[str, int] = {}
    for dim in _REQ_DIMS:
        if dim not in src:
            raise ValueError(f"Missing weight dimension: {dim}")
        val = int(src[dim])
        if val < 1:
            raise ValueError(f"Weight must be >=1 for {dim}, got {val}")
        out[dim] = val
    if out["SK"] < out["TC"]:
        raise ValueError("Invalid weight profile: must satisfy SK >= TC")
    return out


def build_task_scores(task_inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """
    Score all tasks in input mapping.
    """
    out: dict[str, dict[str, int]] = {}
    for task, payload in task_inputs.items():
        cfg = dict(payload)
        cfg.setdefault("task", task)
        cfg.setdefault("prompt", str(payload.get("prompt", task.replace("_", " "))))
        out[task] = score_s3_dimensions(cfg)
    return out


def _default_profile(task_scores: dict[str, dict[str, int]]) -> dict[str, int]:
    """
    Compute mean profile across all tasks.
    """
    if not task_scores:
        return {k: 3 for k in _REQ_DIMS}
    n = float(len(task_scores))
    return {
        dim: int(round(sum(float(scores[dim]) for scores in task_scores.values()) / n))
        for dim in _REQ_DIMS
    }


def build_s3_task_config(
    weights: dict[str, Any] | None,
    task_inputs: dict[str, dict[str, Any]],
    include_default_profile: bool = True,
) -> dict[str, Any]:
    """
    Build S3 configuration with weights and per-task scores.
    """
    w = normalize_weights(weights)
    scores = build_task_scores(task_inputs)
    task_scores: dict[str, Any] = {}
    if include_default_profile:
        task_scores["*"] = _default_profile(scores)
    task_scores.update(scores)
    return {"weights": w, "task_scores": task_scores}
