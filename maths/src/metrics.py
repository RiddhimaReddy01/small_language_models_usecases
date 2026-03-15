from fractions import Fraction
from typing import Any, Dict, List, Optional
import re


BOXED_TEXT_RE = re.compile(r"\\boxed\{([^{}]+)\}")
LATEX_FRACTION_RE = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
NUMBER_TOKEN_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:\s*/\s*[-+]?\d[\d,]*)?(?:[eE][-+]?\d+)?%?")
TRAILING_TEXT_RE = re.compile(r"^(.*?)(?:\s+(?:units?|dollars?|dollar|cents?|cm|mm|km|kg|g|hours?|minutes?|seconds?|meters?|items?|people|students?|cars?|books?)\b.*)?$", re.IGNORECASE)


def _strip_wrappers(value: str) -> str:
    cleaned = value.strip()
    for prefix in ["$", "Answer:", "answer:", "Final Answer:", "final answer:"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    boxed = BOXED_TEXT_RE.findall(cleaned)
    if boxed:
        cleaned = boxed[-1].strip()
    cleaned = LATEX_FRACTION_RE.sub(r"\1/\2", cleaned)
    cleaned = cleaned.replace("\\%", "%")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(".")
    return cleaned.strip()


def _extract_numeric_token(text: str) -> Optional[str]:
    if not text:
        return None
    trimmed = TRAILING_TEXT_RE.match(text)
    candidate = trimmed.group(1).strip() if trimmed else text.strip()
    match = NUMBER_TOKEN_RE.search(candidate)
    if match:
        return match.group(0).replace(" ", "")
    return None


def _normalize_numeric(text: str) -> Optional[str]:
    token = _extract_numeric_token(text) or text.strip()
    token = token.replace(",", "").strip()
    if not token:
        return None

    is_percent = token.endswith("%")
    if is_percent:
        token = token[:-1].strip()

    try:
        if "/" in token and all(part.strip("+-").replace(".", "", 1).isdigit() for part in token.split("/", 1)):
            value = float(Fraction(token))
        else:
            value = float(token)
        if is_percent:
            value /= 100.0
        return str(value)
    except Exception:
        return None


def normalize_answer(answer: Any, dataset_name: Optional[str] = None) -> Optional[str]:
    if answer is None:
        return None
    text = _strip_wrappers(str(answer))
    if not text:
        return None
    lower_name = (dataset_name or "").lower()
    if lower_name in {"gsm8k", "svamp", "math", "math_subset"}:
        numeric = _normalize_numeric(text)
        if numeric is not None:
            return numeric
    if len(text) == 1 and text.upper() in {"A", "B", "C", "D", "E"}:
        return text.upper()
    return text.strip().lower()


def is_correct(pred: Any, gold: Any, dataset_name: Optional[str] = None) -> bool:
    norm_pred = normalize_answer(pred, dataset_name)
    norm_gold = normalize_answer(gold, dataset_name)
    if norm_pred is None or norm_gold is None:
        return False
    try:
        return abs(float(norm_pred) - float(norm_gold)) <= 1e-9
    except Exception:
        return norm_pred == norm_gold


def accuracy(records: List[Dict[str, Any]], dataset_name: Optional[str] = None) -> float:
    if not records:
        return 0.0
    correct = 0
    total = 0
    for record in records:
        total += 1
        if is_correct(record.get("prediction"), record.get("gold"), dataset_name):
            correct += 1
    return correct / total if total else 0.0


def agreement(values: List[Any], dataset_name: Optional[str] = None) -> float:
    normalized = [normalize_answer(value, dataset_name) for value in values]
    normalized = [value for value in normalized if value is not None]
    if len(normalized) <= 1:
        return 1.0 if normalized else 0.0
    anchor = normalized[0]
    matches = sum(1 for value in normalized[1:] if value == anchor)
    return matches / (len(normalized) - 1)


def mean_latency(records: List[Dict[str, Any]]) -> float:
    if not records:
        return 0.0
    latencies = [record.get("latency", 0.0) for record in records if record.get("latency") is not None]
    return sum(latencies) / len(latencies) if latencies else 0.0
