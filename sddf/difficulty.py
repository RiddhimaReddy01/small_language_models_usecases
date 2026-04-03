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
]

_SPACY_NLP = None
_SPACY_LOAD_FAILED = False


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
                _SPACY_NLP = spacy.load(model_name, disable=["ner", "textcat", "lemmatizer"])
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
        if re.search(pat, t):
            hits += 1
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
    text = str(example.get("question", example.get("prompt", example.get("text", "")))).strip().lower()
    if not text:
        return 0.0
    cues = [
        "who", "when", "where", "which country", "capital", "president", "prime minister",
        "year", "date", "historical", "according to", "latest", "current", "fact", "evidence",
    ]
    score = sum(1.0 for cue in cues if cue in text)
    # Named entities and years raise likely parametric knowledge dependence.
    entity_like = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", str(example.get("prompt", example.get("question", example.get("text", "")))))
    years = re.findall(r"\b(19|20)\d{2}\b", text)
    score += min(2.0, float(len(entity_like)) / 3.0)
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
    return {
        "n_in": compute_n_in(text, mode=rules.get("n_in_mode", "tokens")),
        "entropy": compute_entropy(text, level=rules.get("entropy_level", "token")),
        "reasoning_proxy": compute_reasoning_proxy(example, baseline_stats=rules.get("baseline_stats")),
        "constraint_count": compute_constraint_count(example, rules=rules.get("constraint_rules")),
        "parametric_dependence": compute_parametric_dependence(example),
        "dependency_distance": compute_dependency_distance(example),
    }


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
