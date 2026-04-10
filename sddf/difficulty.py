from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import pandas as pd


TASK_DIMENSION_MAP = {
    "classification": "H",
    "summarization": "n_in",
    "retrieval_grounded": "n_in",
    "information_extraction": "|Gamma|",
    "instruction_following": "|Gamma|",
    "text_generation": "|Gamma|",
    "maths": "R_hat",
    "code_generation": "R_hat",
}

DIFFICULTY_FEATURES = [
    "n_in",
    "entropy",
    "reasoning_proxy",
    "constraint_count",
    "parametric_dependence",
    "dependency_distance",
    # Pairwise interaction features — make the routing boundary non-linear in
    # original feature space without changing the simplex learner architecture.
    # Each captures a theoretically motivated AND-like combination:
    "reasoning_x_constraint",   # high reasoning load AND many constraints → compounded failure
    "length_x_entropy",         # long AND lexically varied → harder retrieval/summarization
    "knowledge_x_reasoning",    # factual knowledge gap AND multi-hop → parametric multi-hop failure
    # Task-specific decomposition features (zero for non-matching tasks).
    "classification_ambiguity",
    "classification_negation_density",
    "classification_domain_shift",
    "math_numeric_density",
    "math_symbol_density",
    "math_precision_cues",
    "instruction_format_strictness",
    "instruction_prohibition_count",
    "instruction_step_count",
    "instruction_conflict_cues",
]

_SPACY_NLP = None
_SPACY_LOAD_FAILED = False


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"[A-Za-z0-9_]+", text)


def _count_any(text_lower: str, cues: list[str]) -> int:
    return sum(1 for cue in cues if cue in text_lower)


def _count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _classification_feature_block(text: str) -> dict[str, float]:
    toks = _tokenize(text)
    n = max(1, len(toks))
    text_lower = text.lower()

    contrast = _count_regex(text_lower, r"\b(but|however|although|though|yet|whereas|despite)\b")
    hedges = _count_regex(text_lower, r"\b(maybe|perhaps|possibly|seems|appears|likely|unclear|ambiguous)\b")
    or_count = _count_regex(text_lower, r"\bor\b")
    ambiguity = _clamp01((contrast + hedges + max(0, or_count - 1)) / 8.0)

    neg = _count_regex(text_lower, r"\b(no|not|never|none|without|can't|cannot|won't|isn't|don't|didn't)\b")
    negation_density = _clamp01(neg / max(1.0, n / 6.0))

    years = _count_regex(text, r"\b(19|20)\d{2}\b")
    acronyms = _count_regex(text, r"\b[A-Z]{2,}\b")
    capitals = _count_regex(text, r"\b[A-Z][a-z]{2,}\b")
    domain_shift = _clamp01((years + 0.7 * acronyms + 0.15 * capitals) / 10.0)

    return {
        "classification_ambiguity": ambiguity,
        "classification_negation_density": negation_density,
        "classification_domain_shift": domain_shift,
    }


def _math_feature_block(text: str) -> dict[str, float]:
    toks = _tokenize(text)
    n = max(1, len(toks))
    text_lower = text.lower()

    numeric_tokens = _count_regex(text, r"\b\d+(\.\d+)?\b")
    numeric_density = _clamp01(numeric_tokens / max(1.0, n / 3.0))

    symbol_hits = _count_regex(text, r"[\=\+\-\*/\^%<>]|≤|≥|≠|√|∑|∫")
    symbol_density = _clamp01(symbol_hits / max(1.0, n / 4.0))

    precision_cues = _count_any(
        text_lower,
        [
            "exact",
            "exactly",
            "decimal",
            "nearest",
            "round",
            "significant figure",
            "precision",
            "simplify",
            "fraction",
            "integer",
        ],
    )
    precision = _clamp01(precision_cues / 4.0)

    return {
        "math_numeric_density": numeric_density,
        "math_symbol_density": symbol_density,
        "math_precision_cues": precision,
    }


def _instruction_feature_block(text: str) -> dict[str, float]:
    toks = _tokenize(text)
    n = max(1, len(toks))
    text_lower = text.lower()

    format_cues = _count_any(
        text_lower,
        [
            "json",
            "yaml",
            "xml",
            "markdown",
            "csv",
            "table",
            "bullet",
            "schema",
            "exact format",
            "output format",
            "valid json",
        ],
    )
    format_strictness = _clamp01(format_cues / 4.0)

    prohibitions = _count_regex(text_lower, r"\b(do not|don't|never|without|avoid|must not|cannot)\b")
    prohibition_count = _clamp01(prohibitions / 3.0)

    step_cues = _count_regex(text_lower, r"\b(first|second|third|step|then|after that|finally|in order)\b")
    instruction_steps = _clamp01(step_cues / max(2.0, n / 12.0))

    conflict_cues = _count_regex(text_lower, r"\b(but|however|except|unless|instead|only if|otherwise)\b")
    conflicts = _clamp01(conflict_cues / 3.0)

    return {
        "instruction_format_strictness": format_strictness,
        "instruction_prohibition_count": prohibition_count,
        "instruction_step_count": instruction_steps,
        "instruction_conflict_cues": conflicts,
    }


def _task_specific_features(task: str, text: str) -> dict[str, float]:
    out = {
        "classification_ambiguity": 0.0,
        "classification_negation_density": 0.0,
        "classification_domain_shift": 0.0,
        "math_numeric_density": 0.0,
        "math_symbol_density": 0.0,
        "math_precision_cues": 0.0,
        "instruction_format_strictness": 0.0,
        "instruction_prohibition_count": 0.0,
        "instruction_step_count": 0.0,
        "instruction_conflict_cues": 0.0,
    }
    if task == "classification":
        out.update(_classification_feature_block(text))
    elif task == "maths":
        out.update(_math_feature_block(text))
    elif task == "instruction_following":
        out.update(_instruction_feature_block(text))
    return out


def _get_spacy_nlp():
    global _SPACY_NLP, _SPACY_LOAD_FAILED
    if _SPACY_NLP is not None:
        return _SPACY_NLP
    if _SPACY_LOAD_FAILED:
        return None
    try:
        import spacy  # type: ignore

        for model_name in ("en_core_web_sm", "en_core_web_md"):
            try:
                # Keep parser (dependency_distance) and ner (parametric_dependence).
                # Only disable components not needed for either feature.
                _SPACY_NLP = spacy.load(model_name, disable=["textcat", "lemmatizer"])
                return _SPACY_NLP
            except Exception:
                continue
    except Exception:
        pass
    _SPACY_LOAD_FAILED = True
    return None


def compute_n_in(text: str, mode: str = "tokens") -> float:
    if not text:
        return 0.0
    if mode == "chars":
        return float(len(text))
    return float(len(str(text).split()))


def compute_entropy(text: str, level: str = "token") -> float:
    if not text:
        return 0.0
    units = str(text).split() if level == "token" else list(str(text))
    if not units:
        return 0.0
    counts = Counter(units)
    total = len(units)
    probs = [count / total for count in counts.values()]
    return float(-sum(prob * math.log2(prob) for prob in probs if prob > 0))


def _coerce_example(example: dict[str, Any] | str | None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(example, dict):
        payload = dict(example)
    else:
        payload = {}
        if example is not None:
            payload["text"] = str(example)
    if metadata:
        payload.update(metadata)
    return payload


def compute_constraint_count(example: dict[str, Any] | str, rules: dict[str, Any] | None = None) -> float:
    if not isinstance(example, dict):
        example = {"text": str(example)}

    count = 0
    count += len(example.get("required_fields", []) or [])
    count += len(example.get("format_rules", []) or [])
    count += len(example.get("content_rules", []) or [])
    count += len(example.get("length_rules", []) or [])
    count += len(example.get("ordering_rules", []) or [])

    if rules:
        count += len(rules.get("required_fields", []) or [])
        count += len(rules.get("format_rules", []) or [])
        count += len(rules.get("content_rules", []) or [])
        count += len(rules.get("length_rules", []) or [])
        count += len(rules.get("ordering_rules", []) or [])
    if count == 0:
        text = str(example.get("prompt", example.get("question", example.get("text", ""))))
        count += int(_estimate_constraint_count_from_text(text))
    return float(count)


def _estimate_constraint_count_from_text(text: str) -> int:
    if not text:
        return 0
    t = " " + text.lower() + " "
    patterns = [
        r"\bmust\b",
        r"\bshould\b",
        r"\brequired\b",
        r"\bexactly\b",
        r"\bat least\b",
        r"\bat most\b",
        r"\bno more than\b",
        r"\bno less than\b",
        r"\binclude\b",
        r"\bdo not\b|\bdon't\b|\bwithout\b",
        r"\bonly\b",
        r"\bformat\b|\bjson\b|\bxml\b|\bmarkdown\b|\bcsv\b",
        r"\bbullet\b|\btable\b|\blist\b",
        r"\bword(s)?\b|\bcharacter(s)?\b|\blength\b",
        r"\bcite\b|\bsource\b",
    ]
    hits = 0
    for pat in patterns:
        # Count occurrences, not just presence — "must X, must Y, must Z" → 3.
        hits += len(re.findall(pat, t))
    return hits


def compute_reasoning_proxy(example: dict[str, Any], baseline_stats: dict[str, Any] | None = None) -> float:
    # R(x) = |S_x|, where S_x is supporting facts / reasoning hops.
    # Preferred fields (if present): supporting_facts, reasoning_chain, num_hops.
    supporting = example.get("supporting_facts")
    if isinstance(supporting, list):
        return float(len(supporting))
    reasoning_chain = example.get("reasoning_chain")
    if isinstance(reasoning_chain, list):
        return float(len(reasoning_chain))
    for key in ("num_hops", "reasoning_hops", "num_steps"):
        value = example.get(key)
        if value is not None:
            try:
                return float(max(0.0, float(value)))
            except (TypeError, ValueError):
                pass
    # Query-only fallback: estimate required reasoning hops from compositional cues.
    text = str(example.get("question", example.get("prompt", example.get("text", "")))).strip().lower()
    if text:
        cues = [
            "because", "therefore", "hence", "if", "then", "after", "before",
            "compare", "prove", "derive", "compute", "calculate", "reason",
            "first", "second", "third", "multi-step", "step by step",
        ]
        cue_count = sum(1 for cue in cues if cue in text)
        clause_count = max(1, len(re.split(r"[;,:]|\band\b|\bor\b|\bwhile\b|\bwhich\b|\bthat\b", text)))
        hop_estimate = max(0.0, (0.6 * cue_count) + (0.25 * (clause_count - 1)))
        if hop_estimate > 0:
            return float(hop_estimate)

    # Backward-compatible fallback if no explicit hop annotation is available.
    if baseline_stats:
        return float(max(0.0, baseline_stats.get("default_reasoning_hops", 0.0) or 0.0))
    return 0.0


def compute_parametric_dependence(example: dict[str, Any]) -> float:
    # PD(x) = max(0, yhat_RAG(x) - yhat_param_only(x))
    rag = example.get("yhat_rag", example.get("rag_score"))
    param_only = example.get("yhat_param_only", example.get("param_only_score"))
    if rag is not None and param_only is not None:
        try:
            return float(max(0.0, float(rag) - float(param_only)))
        except (TypeError, ValueError):
            pass
    base = float(max(0.0, float(example.get("parametric_dependence", 0.0) or 0.0)))
    if base > 0.0:
        return base
    # Query-only fallback proxy for knowledge dependence.
    raw_text = str(example.get("prompt", example.get("question", example.get("text", "")))).strip()
    text_lower = raw_text.lower()
    if not text_lower:
        return 0.0
    cues = [
        "who", "when", "where", "which country", "capital", "president", "prime minister",
        "year", "date", "historical", "according to", "latest", "current", "fact", "evidence",
    ]
    score = sum(1.0 for cue in cues if cue in text_lower)
    # Named entity count: prefer spacy NER (precise); fall back to mid-sentence
    # capitalized sequences only — excluding the first word of each sentence to
    # avoid counting sentence-initial capitals as named entities.
    nlp = _get_spacy_nlp()
    if nlp is not None:
        try:
            doc = nlp(raw_text)
            entity_count = len(doc.ents)
        except Exception:
            entity_count = 0
    else:
        entity_count = 0
        for sent in re.split(r"(?<=[.!?])\s+", raw_text):
            words = sent.split()
            # Skip index 0 (sentence-initial word always capitalized in English).
            for word in words[1:]:
                if re.match(r"^[A-Z][a-z]{1,}", word):
                    entity_count += 1
    years = re.findall(r"\b(19|20)\d{2}\b", text_lower)
    score += min(2.0, float(entity_count) / 3.0)
    score += min(1.5, float(len(years)) / 2.0)
    # Scale to [0,1] range.
    return float(min(1.0, score / 6.0))


def compute_dependency_distance(example: dict[str, Any]) -> float:
    # MDD(x) = (1/|A_x|) * sum_{(h,d) in A_x} |pos(h) - pos(d)|
    arcs = example.get("dependency_arcs", example.get("dependency_edges"))
    if not isinstance(arcs, list) or not arcs:
        # Real parser pass (if available).
        text = str(example.get("question", example.get("prompt", example.get("text", "")))).strip()
        if text:
            nlp = _get_spacy_nlp()
            if nlp is not None:
                try:
                    doc = nlp(text)
                    parse_distances: list[float] = []
                    for tok in doc:
                        if tok.i == tok.head.i:
                            continue
                        parse_distances.append(abs(float(tok.i - tok.head.i)))
                    if parse_distances:
                        return float(sum(parse_distances) / len(parse_distances))
                except Exception:
                    pass
            # Fallback proxy when parser model is unavailable.
            toks = text.split()
            if len(toks) < 2:
                return 0.0
            clause_breaks = [
                i for i, tok in enumerate(toks)
                if tok.lower().strip(",;:.") in {"that", "which", "while", "because", "although", "if", "when"}
            ]
            if not clause_breaks:
                return float(max(1.0, len(toks) / 8.0))
            spans = []
            for i in clause_breaks:
                left = i
                right = len(toks) - i - 1
                spans.append(float(max(left, right)))
            return float(sum(spans) / len(spans))
        fallback = float(example.get("dependency_distance", 0.0) or 0.0)
        if fallback > 0.0:
            return fallback
        return 0.0
    distances: list[float] = []
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        head = arc.get("head", arc.get("h"))
        dep = arc.get("dep", arc.get("d"))
        try:
            distances.append(abs(float(head) - float(dep)))
        except (TypeError, ValueError):
            continue
    if not distances:
        fallback = float(example.get("dependency_distance", 0.0) or 0.0)
        if fallback > 0.0:
            return fallback
        # Query-only fallback proxy: approximate long-range dependency via clause span.
        text = str(example.get("question", example.get("prompt", example.get("text", "")))).strip()
        if not text:
            return 0.0
        toks = text.split()
        if len(toks) < 2:
            return 0.0
        clause_breaks = [i for i, tok in enumerate(toks) if tok.lower().strip(",;:.") in {"that", "which", "while", "because", "although", "if", "when"}]
        if not clause_breaks:
            return float(max(1.0, len(toks) / 8.0))
        spans = []
        for i in clause_breaks:
            left = i
            right = len(toks) - i - 1
            spans.append(float(max(left, right)))
        return float(sum(spans) / len(spans))
    return float(sum(distances) / len(distances))


def _dimension_for_task(task: str, rule_config: dict[str, Any] | None = None) -> str:
    task_map = TASK_DIMENSION_MAP.copy()
    if rule_config and rule_config.get("task_dimension_map"):
        task_map.update(rule_config["task_dimension_map"])
    return task_map.get(task, "n_in")


def _score_for_dimension(
    dimension: str,
    example: dict[str, Any],
    text: str,
    rule_config: dict[str, Any] | None = None,
) -> float:
    rules = rule_config or {}
    if dimension == "n_in":
        return compute_n_in(text, mode=rules.get("n_in_mode", "tokens"))
    if dimension == "H":
        return compute_entropy(text, level=rules.get("entropy_level", "token"))
    if dimension == "|Gamma|":
        return compute_constraint_count(example, rules=rules.get("constraint_rules"))
    if dimension == "R_hat":
        return compute_reasoning_proxy(example, baseline_stats=rules.get("baseline_stats"))
    raise ValueError(f"Unsupported difficulty dimension: {dimension}")


def compute_all_features(
    example: dict[str, Any],
    text: str,
    rule_config: dict[str, Any] | None = None,
) -> dict[str, float]:
    rules = rule_config or {}

    # For retrieval_grounded tasks the difficulty depends on the context document
    # (length, entropy), not just the query. If a context field is present, use the
    # combined query+context length and the context entropy as the primary signals.
    task = str(example.get("task", "")).strip().lower()
    context = str(example.get("context", example.get("passage", example.get("document", ""))) or "")
    if task == "retrieval_grounded" and context:
        feature_text = text + " " + context
    else:
        feature_text = text

    n_in         = compute_n_in(feature_text, mode=rules.get("n_in_mode", "tokens"))
    entropy      = compute_entropy(feature_text, level=rules.get("entropy_level", "token"))
    reasoning    = compute_reasoning_proxy(example, baseline_stats=rules.get("baseline_stats"))
    constraints  = compute_constraint_count(example, rules=rules.get("constraint_rules"))
    parametric   = compute_parametric_dependence(example)
    dep_dist     = compute_dependency_distance(example)
    task_specific = _task_specific_features(task, feature_text)

    base = {
        "n_in":                   n_in,
        "entropy":                entropy,
        "reasoning_proxy":        reasoning,
        "constraint_count":       constraints,
        "parametric_dependence":  parametric,
        "dependency_distance":    dep_dist,
        # Interaction features — non-zero only when BOTH component features are elevated.
        "reasoning_x_constraint": reasoning * constraints,
        "length_x_entropy":       n_in * entropy,
        "knowledge_x_reasoning":  parametric * reasoning,
    }
    base.update(task_specific)
    return base


def annotate_dominant_dimension(
    df: pd.DataFrame,
    task: str,
    text_col: str = "input_text",
    prompt_col: str | None = None,
    metadata_col: str | None = None,
    rule_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    dimension = _dimension_for_task(task, rule_config=rule_config)

    def annotate_row(row: pd.Series) -> pd.Series:
        prompt_text = str(row.get(prompt_col, "")) if prompt_col else ""
        body_text = str(row.get(text_col, "")) if text_col in row else ""
        merged_text = " ".join(part for part in [body_text, prompt_text] if part).strip()
        metadata = row.get(metadata_col) if metadata_col else None
        if metadata_col and metadata is not None and not isinstance(metadata, dict):
            metadata = {"metadata": metadata}
        example = _coerce_example(row.to_dict(), metadata=metadata)
        features = compute_all_features(example, merged_text, rule_config=rule_config)
        score = _score_for_dimension(dimension, example, merged_text, rule_config=rule_config)
        row["difficulty_dim"] = dimension
        row["difficulty_score"] = float(score)
        for key, value in features.items():
            row[f"difficulty_feature_{key}"] = float(value)
        return row

    return out.apply(annotate_row, axis=1)


def make_difficulty_bins(
    df: pd.DataFrame,
    score_col: str = "difficulty_score",
    n_bins: int = 5,
    method: str = "quantile",
) -> pd.DataFrame:
    out = df.copy()
    if score_col not in out.columns:
        raise ValueError(f"Missing score column: {score_col}")
    if out[score_col].dropna().empty:
        out["difficulty_bin"] = pd.Series([pd.NA] * len(out), dtype="Int64")
        return out

    if method == "quantile":
        out["difficulty_bin"] = pd.qcut(out[score_col], q=n_bins, labels=False, duplicates="drop")
    elif method == "uniform":
        out["difficulty_bin"] = pd.cut(out[score_col], bins=n_bins, labels=False, include_lowest=True)
    else:
        raise ValueError("method must be 'quantile' or 'uniform'")

    out["difficulty_bin"] = out["difficulty_bin"].astype("Int64")
    return out
