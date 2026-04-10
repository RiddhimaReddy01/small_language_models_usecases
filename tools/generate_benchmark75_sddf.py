from __future__ import annotations

import argparse
import bisect
import json
import re
import math
import hashlib
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from statistics import NormalDist
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from sddf.difficulty import DIFFICULTY_FEATURES, compute_all_features
from sddf.difficulty_weights import DifficultyWeightLearner

LEGACY_BENCHMARK_ROOT = ROOT / "model_runs" / "benchmark_75"
FLAT_BENCHMARK_ROOT = ROOT / "model_runs"


def _benchmark_root() -> Path:
    if LEGACY_BENCHMARK_ROOT.exists():
        return LEGACY_BENCHMARK_ROOT
    return FLAT_BENCHMARK_ROOT


BENCHMARK_ROOT = _benchmark_root()
CANONICAL_MODELS = [
    "qwen2.5_0.5b",
    "qwen2.5_3b",
    "qwen2.5_7b",
    "llama_llama-3.3-70b-versatile",
]
BASELINE_MODEL = "llama_llama-3.3-70b-versatile"
DISPLAY_NAMES = {
    "qwen2.5_0.5b":                    "qwen2.5:0.5b",
    "qwen2.5_3b":                      "qwen2.5:3b",
    "qwen2.5_7b":                      "qwen2.5:7b",
    "llama_llama-3.3-70b-versatile":   "groq:llama-3.3-70b-versatile",
}
SUPPORTED_TASKS = {
    "classification",
    "maths",
    "information_extraction",
    "instruction_following",
    "retrieval_grounded",
    "summarization",
    "code_generation",
    "text_generation",
}

DEFAULT_WILSON_CONFIDENCE_LEVEL = 0.95
DEFAULT_WILSON_Z = 1.959963985
DEFAULT_CAPABILITY_THRESHOLD = 0.80
DEFAULT_RISK_THRESHOLD = 0.20
DEFAULT_MIN_SAMPLES = 5
DEFAULT_MIN_GROUND_TRUTH_COVERAGE = 0.95


def _z_from_confidence(level: float) -> float:
    bounded = max(0.50, min(0.999, float(level)))
    return NormalDist().inv_cdf(0.5 + bounded / 2.0)


def _beta_credible_interval(
    successes: int,
    n: int,
    level: float = DEFAULT_WILSON_CONFIDENCE_LEVEL,
) -> tuple[float | None, float | None]:
    """Wilson score confidence interval — reliable at small n and extreme proportions.

    Replaces the earlier Gaussian-Beta approximation, which breaks when success
    rate is near 0 or 1 (skewed Beta) — exactly the region that matters for τ*
    certification on small val/test sets.
    """
    if n <= 0:
        return None, None
    s = max(0, min(int(successes), int(n)))
    z = _z_from_confidence(level)
    p_hat = float(s) / float(n)
    z2 = z * z
    n_f = float(n)
    denom = 1.0 + z2 / n_f
    center = (p_hat + z2 / (2.0 * n_f)) / denom
    margin = z * math.sqrt(max(0.0, p_hat * (1.0 - p_hat) / n_f + z2 / (4.0 * n_f * n_f))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


class GeneralizedRoutingFramework:
    """Small local subset used by this report generator."""

    def __init__(
        self,
        capability_threshold: float = DEFAULT_CAPABILITY_THRESHOLD,
        risk_threshold: float = DEFAULT_RISK_THRESHOLD,
        wilson_z: float = DEFAULT_WILSON_Z,
        wilson_confidence_level: float = DEFAULT_WILSON_CONFIDENCE_LEVEL,
    ) -> None:
        self.capability_threshold = capability_threshold
        self.risk_threshold = risk_threshold
        self.wilson_z = wilson_z
        self.wilson_confidence_level = wilson_confidence_level

    def find_threshold(
        self,
        cap_xs: list[float],
        cap_iso: list[float],
        cap_raw: list[float],
        risk_xs: list[float],
        risk_iso: list[float],
        risk_raw: list[float],
        min_k: int = 5,
        grid_points: int = 200,
    ) -> float | None:
        """Find τ* = highest d where k-nearest Wilson CI lower bound on cap(d) ≥ θ_cap
        AND k-nearest Wilson CI upper bound on risk(d) ≤ θ_risk.

        Fully continuous — no bins. Uses the k nearest training queries at each d
        to estimate a local proportion and Wilson CI bound.
        """
        if len(cap_xs) < min_k or len(risk_xs) < min_k:
            return None
        d_min = min(cap_xs[0], risk_xs[0])
        d_max = max(cap_xs[-1], risk_xs[-1])
        if d_max <= d_min:
            return None
        for i in range(grid_points - 1, -1, -1):
            d = d_min + (d_max - d_min) * i / max(1, grid_points - 1)
            _, lower_cap = _local_beta_at(
                d, cap_xs, cap_raw, min_k, self.wilson_confidence_level, upper=False
            )
            _, upper_risk = _local_beta_at(
                d, risk_xs, risk_raw, min_k, self.wilson_confidence_level, upper=True
            )
            if lower_cap >= self.capability_threshold and upper_risk <= self.risk_threshold:
                return d
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row["sample_id"])
        existing = by_sample.get(sample_id)
        if existing is None:
            by_sample[sample_id] = row
            continue
        existing_timestamp = str(existing.get("timestamp") or "")
        row_timestamp = str(row.get("timestamp") or "")
        if row_timestamp >= existing_timestamp:
            by_sample[sample_id] = row
    return list(by_sample.values())


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _strip_example(prompt: str) -> str:
    return re.sub(r"\s*\(Example \d+\)\s*$", "", (prompt or "").strip())


def _build_reference_lookup(task: str) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}

    # Preferred: explicit dataset ground truth keyed by sample_id.
    gt_root = ROOT / "data" / "ground_truth"
    candidates = [
        gt_root / f"{task}.jsonl",
        gt_root / f"{task}.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                sample_id = str(item.get("sample_id") or item.get("example_id") or "")
                if not sample_id:
                    continue
                reference = item.get("reference")
                if isinstance(reference, dict) and reference:
                    refs[sample_id] = reference
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for sample_id, reference in payload.items():
                    if isinstance(reference, dict) and reference:
                        refs[str(sample_id)] = reference
            elif isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    sample_id = str(item.get("sample_id") or item.get("example_id") or "")
                    reference = item.get("reference")
                    if sample_id and isinstance(reference, dict) and reference:
                        refs[sample_id] = reference

    return refs


def _resolve_reference(row: dict[str, Any], reference_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sample_id = str(row["sample_id"])
    reference = reference_lookup.get(sample_id)
    if reference:
        return reference
    return {}


def _contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def _extract_number_candidates(text: str) -> list[float]:
    candidates: list[float] = []
    seen: set[float] = set()
    for match in re.finditer(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", text or ""):
        token = match.group(0)
        try:
            if "/" in token and not token.startswith(("http://", "https://")):
                numerator, denominator = token.split("/", 1)
                value = float(numerator) / float(denominator)
            else:
                value = float(token)
        except ValueError:
            continue
        if value not in seen:
            seen.add(value)
            candidates.append(value)
    return candidates


def _classification_eval(reference: dict[str, Any], output: str) -> tuple[float, str | None]:
    text = _norm(output)
    if "label" in reference:
        label = reference["label"]
        if label == "neutral":
            ok = any(token in text for token in ["neutral", "okay", "slightly positive", "mixed"])
        else:
            ok = label in text
        return float(ok), None if ok else "wrong_label"
    choices = reference.get("choices", [])
    ok = any(choice in text for choice in choices)
    return float(ok), None if ok else "wrong_label"


def _maths_eval(reference: dict[str, Any], output: str, parsed: dict[str, Any]) -> tuple[float, str | None]:
    answer = parsed.get("answer")
    if "answer" in reference:
        expected = reference["answer"]
        candidates = []
        if answer is not None:
            try:
                candidates.append(float(answer))
            except (TypeError, ValueError):
                pass
        candidates.extend(_extract_number_candidates(output))
        ok = any(abs(candidate - expected) < 1e-6 for candidate in candidates)
        return float(ok), None if ok else "arithmetic_error"
    if "answers_text" in reference:
        text = _norm(output)
        ok = all(fragment in text for fragment in reference["answers_text"])
        return float(ok), None if ok else "arithmetic_error"
    return (1.0 if answer is not None else 0.0), None if answer is not None else "arithmetic_error"


def _ie_eval(reference: dict[str, Any], output: str) -> tuple[float, str | None]:
    text = _norm(output)
    expected = reference.get("contains", [])
    if expected:
        ok = _contains_all(text, expected)
        return float(ok), None if ok else "missing_field"
    return 1.0 if text else 0.0, None if text else "missing_field"


def _instruction_eval(reference: dict[str, Any], output: str) -> tuple[float, str | None]:
    text = _norm(output)
    if "sequence" in reference:
        ok = all(token in text for token in reference["sequence"])
        return float(ok), None if ok else "constraint_violation"
    if "ordered_contains" in reference:
        order = reference["ordered_contains"]
        ok = all(token in text for token in order) and all(text.find(order[i]) <= text.find(order[i + 1]) for i in range(len(order) - 1))
        return float(ok), None if ok else "constraint_violation"
    return 1.0 if text else 0.0, None if text else "constraint_violation"


def _retrieval_eval(reference: dict[str, Any], output: str) -> tuple[float, str | None]:
    text = _norm(output)
    if reference.get("contains"):
        ok = _contains_all(text, reference["contains"])
        return float(ok), None if ok else "answer_mismatch"
    ok = reference.get("requires_context_ack") and any(token in text for token in ["provide", "context", "passage", "document", "more information", "clarify"])
    return float(ok), None if ok else "no_answer"


def _summary_eval(reference: dict[str, Any], output: str) -> tuple[float, str | None]:
    text = _norm(output)
    expected = reference.get("contains", [])
    if expected:
        ok = all(token in text for token in expected)
        return float(ok), None if ok else "low_relevance"
    return 1.0 if text else 0.0, None if text else "empty_output"


def _detect_code_in_raw(raw: str) -> bool:
    """Detect code patterns in raw output when parsed_output['code_blocks'] is absent."""
    if not raw:
        return False
    # Markdown fenced code block (``` ... ```)
    if re.search(r"```[\s\S]{10,}```", raw):
        return True
    # Python/JS function definition
    if re.search(r"\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(", raw):
        return True
    # Indented block with return (common pattern even without fences)
    if re.search(r"\breturn\s+\w", raw) and re.search(r"[ \t]{4}", raw):
        return True
    return False


def _code_eval(reference: dict[str, Any], output: str, parsed: dict[str, Any]) -> tuple[float, str | None]:
    text = _norm(output)
    # parsed_output["code_blocks"] is often absent in raw benchmark data;
    # fall back to pattern-matching the raw output string directly.
    blocks = parsed.get("code_blocks") or []
    has_code = bool(blocks) or _detect_code_in_raw(output)
    kind = reference.get("kind")
    if kind == "reverse_string":
        ok = has_code and "reverse" in text and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind == "bubble_sort":
        ok = has_code and "for" in text and "swap" in text
        return float(ok), None if ok else "logic_error"
    if kind == "factorial":
        ok = has_code and "factorial" in text and ("return" in text or "raise" in text)
        return float(ok), None if ok else "logic_error"
    if kind == "parse_json":
        ok = has_code and "json" in text
        return float(ok), None if ok else "format_error"
    if kind == "binary_search":
        ok = has_code and "mid" in text and ("left" in text or "low" in text)
        return float(ok), None if ok else "logic_error"
    # Extended kinds from expanded prompt bank: all require code present.
    if kind in {
        "add_numbers", "string_length", "is_even", "max_two", "celsius_to_f",
        "word_count", "square", "is_empty", "concat_strings", "repeat_string",
    }:
        ok = has_code and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind in {"palindrome", "list_max", "remove_duplicates", "flatten_list",
                "char_freq", "anagram"}:
        ok = has_code and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind in {"stack_class", "bst", "min_heap", "trie", "lru_cache"}:
        ok = has_code and ("class" in text or "def" in text) and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind in {"merge_sorted", "quicksort", "group_by", "primes_to_n", "dot_product",
                "read_csv", "deep_clone", "lcs", "topological_sort"}:
        ok = has_code and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind in {"dijkstra", "retry_decorator", "rate_limiter", "db_pool",
                "event_emitter"}:
        ok = has_code and "return" in text
        return float(ok), None if ok else "logic_error"
    if kind in {"singleton", "async_http", "job_scheduler", "mapreduce",
                "redis_lock", "pipeline", "rolling_stats", "consistent_hashing",
                "crdt", "bloom_filter"}:
        ok = has_code and "return" in text
        return float(ok), None if ok else "logic_error"
    return float(has_code), None if has_code else "format_error"


def _textgen_eval(reference: dict[str, Any], output: str, row: dict[str, Any]) -> tuple[float, str | None]:
    text = _norm(output)
    # Only bail on status=invalid when there is genuinely no usable output.
    # "Output suspiciously long (may be truncated)" is a pipeline flag on
    # otherwise-valid outputs â€" the content should still be evaluated.
    if row.get("status") == "invalid" and not text:
        return 0.0, "incomplete_output"
    expected = reference.get("contains", [])
    if expected:
        ok = _contains_all(text, expected)
        return float(ok), None if ok else "low_relevance"
    return 1.0 if text else 0.0, None if text else "empty_output"


def _evaluate_row(row: dict[str, Any], reference_lookup: dict[str, dict[str, Any]]) -> tuple[float, float, str | None]:
    task = row["task"]
    reference = _resolve_reference(row, reference_lookup)
    output = row.get("raw_output", "")
    parsed = row.get("parsed_output") or {}

    # ── Fast path: use pre-computed score/correct from evaluate_outputs.py ──────
    # evaluate_outputs.py uses task-specific evaluators (ROUGE-1 for summarization,
    # constraint checker for instruction_following, concept coverage for text_generation)
    # that correctly handle the actual reference data format.  The internal evaluators
    # below were written for a different reference schema and return wrong results for
    # at least three tasks (summarization checks "contains" but ref has "summary";
    # text_generation checks "contains" but ref has "required_concepts";
    # instruction_following checks "sequence" but ref has "instruction_ids"/"kwargs").
    # Using the pre-computed field avoids re-evaluation from a broken code path.
    if "score" in row and row.get("status") not in ("invalid",):
        capability = float(bool(row.get("correct", False)))
        failure: str | None = None if capability else (row.get("failure_category") or "quality_failure")
        # Risk still uses the task-specific severity×undetectability table below.
        # Skip to risk calculation by falling through after setting capability/failure.
        # (Jump forward — avoid the full evaluator block.)
        _use_precomputed = True
    else:
        _use_precomputed = False

    if not _use_precomputed:
        if not reference:
            return 0.0, 1.0, "missing_ground_truth"
        if not output.strip():
            failure = row.get("failure_category") or "empty_output"
            return 0.0, 1.0, failure
    if not _use_precomputed:
        if task == "classification":
            capability, failure = _classification_eval(reference, output)
        elif task == "maths":
            capability, failure = _maths_eval(reference, output, parsed)
        elif task == "information_extraction":
            capability, failure = _ie_eval(reference, output)
        elif task == "instruction_following":
            capability, failure = _instruction_eval(reference, output)
        elif task == "retrieval_grounded":
            capability, failure = _retrieval_eval(reference, output)
        elif task == "summarization":
            capability, failure = _summary_eval(reference, output)
        elif task == "code_generation":
            capability, failure = _code_eval(reference, output, parsed)
        elif task == "text_generation":
            capability, failure = _textgen_eval(reference, output, row)
        else:
            capability = 1.0 if row.get("valid", False) else 0.0
            failure = None if capability else row.get("failure_category") or "quality_failure"
    # Task-based risk model.
    #
    # WHY TASK-BASED:
    # Risk = P(error causes harm). A wrong maths answer in an automated pipeline
    # is high severity AND hard to detect. A low-relevance summary is low severity
    # AND easy for a human to spot. Pooling these into one global table conflates
    # very different deployment stakes.
    #
    # FORMULA per row:
    #   risk = severity(task, failure) * undetectability(task, failure)
    #
    # WHERE:
    #   severity       = how bad is this error in deployment for this task
    #   undetectability = how likely is this error to go unnoticed
    #
    # Both are in [0,1]. risk ∈ [0,1].
    # At the curve level: risk(d) = mean(risk_i) for k nearest samples at d.
    # This gives P(harmful error | difficulty = d) — the probability that a
    # randomly drawn query at difficulty d produces a harmful undetected failure.
    #
    # TASK-SPECIFIC TABLES:
    # (severity, undetectability) per failure mode per task.
    # Tasks with automated downstream use (maths, code) get higher severity.
    # Tasks with human review (summarization, text_generation) get lower undetectability.

    TASK_FAILURE_HARM: dict[str, dict[str, tuple[float, float]]] = {
        "classification": {
            # Wrong label fed into downstream pipeline — moderate severity, easy to audit
            "wrong_label":          (0.80, 0.70),
            "format_error":         (0.30, 0.30),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.50, 0.50),
        },
        "maths": {
            # Arithmetic errors in automated systems are catastrophic and silent
            "arithmetic_error":     (0.95, 0.90),
            "answer_mismatch":      (0.90, 0.85),
            "logic_error":          (0.90, 0.85),
            "format_error":         (0.40, 0.40),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.60, 0.60),
        },
        "code_generation": {
            # Buggy code silently fails at runtime — very high undetectability
            "logic_error":          (0.95, 0.95),
            "format_error":         (0.50, 0.40),
            "incomplete_output":    (0.60, 0.50),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.70, 0.70),
        },
        "instruction_following": {
            # Constraint violations may go unnoticed in long outputs
            "constraint_violation": (0.70, 0.75),
            "format_error":         (0.40, 0.45),
            "incomplete_output":    (0.50, 0.50),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.50, 0.55),
        },
        "information_extraction": {
            # Missing or wrong entity — downstream NLP pipeline breaks
            "missing_field":        (0.80, 0.75),
            "answer_mismatch":      (0.80, 0.75),
            "no_answer":            (0.40, 0.30),
            "format_error":         (0.40, 0.40),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.55, 0.55),
        },
        "retrieval_grounded": {
            # Wrong factual answer — user acts on bad info
            "answer_mismatch":      (0.85, 0.80),
            "no_answer":            (0.35, 0.25),
            "low_relevance":        (0.55, 0.60),
            "format_error":         (0.30, 0.30),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.30, 0.30),
            "quality_failure":      (0.55, 0.55),
        },
        "summarization": {
            # Human reads summary — errors are visible, lower undetectability
            "low_relevance":        (0.55, 0.45),
            "incomplete_output":    (0.40, 0.35),
            "quality_failure":      (0.45, 0.40),
            "format_error":         (0.25, 0.25),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.25, 0.25),
        },
        "text_generation": {
            # Creative output — human reviews it, low stakes
            "low_relevance":        (0.45, 0.40),
            "quality_failure":      (0.40, 0.35),
            "incomplete_output":    (0.35, 0.30),
            "format_error":         (0.20, 0.20),
            "empty_output":         (0.10, 0.10),
            "missing_ground_truth": (0.20, 0.20),
        },
    }

    # Default fallback for unknown tasks or unmapped failure modes
    DEFAULT_HARM: dict[str, tuple[float, float]] = {
        "arithmetic_error":     (0.90, 0.80),
        "wrong_label":          (0.80, 0.80),
        "logic_error":          (0.90, 0.85),
        "answer_mismatch":      (0.85, 0.80),
        "low_relevance":        (0.60, 0.70),
        "constraint_violation": (0.70, 0.70),
        "quality_failure":      (0.50, 0.60),
        "format_error":         (0.40, 0.40),
        "missing_field":        (0.45, 0.45),
        "incomplete_output":    (0.40, 0.35),
        "no_answer":            (0.20, 0.20),
        "empty_output":         (0.10, 0.10),
        "timeout_runtime":      (0.10, 0.10),
        "missing_ground_truth": (0.30, 0.30),
    }

    if failure is None:
        semantic_risk = 0.0
    else:
        task_harm = TASK_FAILURE_HARM.get(task, DEFAULT_HARM)
        sev, und = task_harm.get(failure, DEFAULT_HARM.get(failure, (0.60, 0.60)))
        semantic_risk = max(0.0, min(1.0, float(sev) * float(und)))
    return capability, semantic_risk, failure


def _pav_list(values: list[float], decreasing: bool) -> list[float]:
    """Weighted Pool Adjacent Violators isotonic regression on a flat list."""
    if not values:
        return []
    pool: list[list] = []  # [pooled_value, pooled_weight, [indices]]
    for i, v in enumerate(values):
        pool.append([v, 1.0, [i]])
        while len(pool) >= 2:
            a, b = pool[-2], pool[-1]
            violates = (b[0] > a[0]) if decreasing else (b[0] < a[0])
            if not violates:
                break
            merged_w = a[1] + b[1]
            merged_v = (a[0] * a[1] + b[0] * b[1]) / merged_w
            pool.pop()
            pool.pop()
            pool.append([merged_v, merged_w, a[2] + b[2]])
    result = [0.0] * len(values)
    for pooled_v, _, idxs in pool:
        for i in idxs:
            result[i] = pooled_v
    return result


def _kernel_smooth(xs: list[float], ys: list[float]) -> list[float]:
    """Gaussian kernel smoother with Silverman bandwidth.

    Replaces PAV isotonic regression for curve display. Unlike PAV:
    - Does not force monotonicity — U-shaped or plateau failure patterns are
      preserved rather than flattened.
    - The τ* selection pathway (_local_beta_at) operates on raw binary outcomes
      independently, so this only affects stored/displayed curves.
    """
    n = len(xs)
    if n < 3:
        return list(ys)
    xs_arr = np.array(xs, dtype=float)
    ys_arr = np.array(ys, dtype=float)
    std_x = float(np.std(xs_arr)) or 1.0
    bw = max(1e-6, 1.06 * std_x * (n ** -0.2))   # Silverman's rule
    result = np.empty(n, dtype=float)
    for i in range(n):
        w = np.exp(-0.5 * ((xs_arr - xs_arr[i]) / bw) ** 2)
        total_w = float(w.sum())
        result[i] = float((w * ys_arr).sum() / total_w) if total_w > 1e-9 else float(ys_arr.mean())
    return result.tolist()


def _fit_continuous_curves(
    rows: list[dict[str, Any]],
    scores: dict[str, float],
    reference_lookup: dict[str, dict[str, Any]],
) -> tuple[
    tuple[list[float], list[float], list[float]],
    tuple[list[float], list[float], list[float]],
    dict[str, int],
    dict[str, dict[str, tuple[list[float], list[float], list[float]]]],
    dict[str, dict[str, tuple[list[float], list[float], list[float]]]],
]:
    """Fit smoothed capability and risk curves on continuous difficulty scores.

    No bins. Each query contributes one (score, outcome) point. Gaussian kernel
    smoothing (Silverman bandwidth) is used instead of isotonic regression —
    this does not enforce monotonicity, allowing non-monotone failure patterns
    (e.g. U-shaped, plateau) to be visible in stored curves.

    The τ* decision pathway uses _local_beta_at (k-NN CI on raw outcomes)
    independently and is unaffected by this smoothing choice.

    Returns:
        cap_curve:  (xs, cap_smooth, cap_raw)
        risk_curve: (xs, risk_smooth, risk_raw)
        failure_counts: {failure_type: count}
        failure_risk_curves: {
            failure_type: {
                "risk_contribution": (xs, smooth, raw),
                "occurrence": (xs, smooth, raw),
            }
        }
        risk_category_curves: {
            risk_category: {
                "risk_contribution": (xs, smooth, raw),
                "occurrence": (xs, smooth, raw),
            }
        }
    """
    triples: list[tuple[float, float, float, str | None]] = []
    failure_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        sid = str(row["sample_id"])
        d = float(scores.get(sid, 0.5))
        cap, risk, failure = _evaluate_row(row, reference_lookup)
        triples.append((d, float(cap), float(risk), failure))
        if failure:
            failure_counts[failure] += 1
    if not triples:
        return ([], [], []), ([], [], []), dict(failure_counts), {}, {}
    triples.sort(key=lambda t: t[0])
    xs       = [t[0] for t in triples]
    cap_raw  = [t[1] for t in triples]
    risk_raw = [t[2] for t in triples]
    cap_smooth  = _kernel_smooth(xs, cap_raw)
    risk_smooth = _kernel_smooth(xs, risk_raw)
    failure_risk_curves: dict[str, dict[str, tuple[list[float], list[float], list[float]]]] = {}
    for failure_type in sorted(failure_counts):
        occurrence_raw = [1.0 if t[3] == failure_type else 0.0 for t in triples]
        contribution_raw = [t[2] if t[3] == failure_type else 0.0 for t in triples]
        failure_risk_curves[failure_type] = {
            "occurrence": (xs, _kernel_smooth(xs, occurrence_raw), occurrence_raw),
            "risk_contribution": (xs, _kernel_smooth(xs, contribution_raw), contribution_raw),
        }

    def _risk_category(risk_value: float) -> str:
        # Coarse bins for reporting. This is model/task-agnostic and based on semantic risk score.
        if risk_value < 0.15:
            return "low"
        if risk_value < 0.35:
            return "medium"
        if risk_value < 0.60:
            return "high"
        return "critical"

    categories = ("low", "medium", "high", "critical")
    risk_category_curves: dict[str, dict[str, tuple[list[float], list[float], list[float]]]] = {}
    for category in categories:
        occurrence_raw = [1.0 if _risk_category(t[2]) == category else 0.0 for t in triples]
        contribution_raw = [t[2] if _risk_category(t[2]) == category else 0.0 for t in triples]
        risk_category_curves[category] = {
            "occurrence": (xs, _kernel_smooth(xs, occurrence_raw), occurrence_raw),
            "risk_contribution": (xs, _kernel_smooth(xs, contribution_raw), contribution_raw),
        }
    return (xs, cap_smooth, cap_raw), (xs, risk_smooth, risk_raw), dict(failure_counts), failure_risk_curves, risk_category_curves


def _curve_to_dict(xs: list[float], ys: list[float]) -> dict[str, float]:
    return {f"{x:.4f}": round(y, 4) for x, y in zip(xs, ys)}


def _serialize_failure_risk_curves(
    curves: dict[str, dict[str, tuple[list[float], list[float], list[float]]]]
) -> dict[str, dict[str, dict[str, float]]]:
    payload: dict[str, dict[str, dict[str, float]]] = {}
    for failure_type, family_curves in curves.items():
        occ_xs, occ_smooth, occ_raw = family_curves.get("occurrence", ([], [], []))
        rc_xs, rc_smooth, rc_raw = family_curves.get("risk_contribution", ([], [], []))
        payload[failure_type] = {
            "occurrence_curve": _curve_to_dict(occ_xs, occ_smooth),
            "occurrence_curve_raw": _curve_to_dict(occ_xs, occ_raw),
            "risk_contribution_curve": _curve_to_dict(rc_xs, rc_smooth),
            "risk_contribution_curve_raw": _curve_to_dict(rc_xs, rc_raw),
        }
    return payload


def _evaluate_curve(xs: list[float], ys: list[float], d: float) -> float:
    """Evaluate a continuous curve at d via linear interpolation."""
    if not xs:
        return 0.5
    d = float(d)
    if d <= xs[0]:
        return ys[0]
    if d >= xs[-1]:
        return ys[-1]
    idx = bisect.bisect_left(xs, d)
    x0, x1 = xs[idx - 1], xs[idx]
    y0, y1 = ys[idx - 1], ys[idx]
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (d - x0) / (x1 - x0)


def _local_beta_at(
    d: float,
    xs: list[float],
    ys_raw: list[float],
    min_k: int,
    ci_level: float,
    upper: bool = False,
) -> tuple[float, float]:
    """Local proportion and Beta-Binomial CI bound at d using k nearest points.

    Returns (point_estimate, lower_bound) for capability (upper=False)
         or (point_estimate, upper_bound) for risk (upper=True).
    """
    if not xs:
        return (0.5, 1.0) if upper else (0.5, 0.0)
    k = max(1, int(min_k))
    indexed = sorted(range(len(xs)), key=lambda i: abs(xs[i] - d))
    neighbors = indexed[:k]
    n = len(neighbors)
    successes = int(round(sum(ys_raw[i] for i in neighbors)))
    p = float(successes) / float(max(1, n))
    lo, hi = _beta_credible_interval(successes, n, level=ci_level)
    if upper:
        return p, (hi if hi is not None else 1.0)
    return p, (lo if lo is not None else 0.0)


def _bootstrap_tau_ci(
    rows: list[dict[str, Any]],
    reference_lookup: dict[str, dict[str, Any]],
    difficulty_scores: dict[str, float],
    cap_threshold: float,
    risk_threshold: float,
    utility_alpha: float,
    utility_beta: float,
    utility_gamma: float,
    B: int = 200,
    conservative_percentile: float = 10.0,
    seed: int = 42,
) -> dict[str, Any]:
    """Bootstrap CI on τ* — addresses double-dipping and point-estimate fragility.

    Single-shot τ* selection on n_val rows is an optimistic estimate: the best τ*
    over all candidate values will overfit to this particular val sample. Bootstrapping
    gives a distribution of τ* values and lets us use the conservative lower percentile
    as the actual operating threshold.

    Returns:
        tau_median:  50th-percentile τ* across B bootstrap samples
        tau_p10:     10th-percentile (conservative, used as operating threshold)
        tau_p90:     90th-percentile
        tau_ci_width: p90 - p10 (measure of τ* stability)
        n_feasible:  fraction of bootstrap samples that found a feasible τ*
    """
    if not rows:
        return {"tau_median": None, "tau_p10": None, "tau_p90": None, "tau_ci_width": None, "n_feasible": 0.0}
    rng = np.random.default_rng(seed)
    n = len(rows)
    taus: list[float] = []
    for _ in range(max(1, int(B))):
        boot_idx = rng.integers(0, n, size=n)
        boot_rows = [rows[int(i)] for i in boot_idx]
        result = _select_operational_tau(
            boot_rows, reference_lookup, difficulty_scores,
            cap_threshold=cap_threshold, risk_threshold=risk_threshold,
            utility_alpha=utility_alpha, utility_beta=utility_beta, utility_gamma=utility_gamma,
        )
        tau = result.get("tau")
        if tau is not None:
            taus.append(float(tau))
    if not taus:
        return {"tau_median": None, "tau_p10": None, "tau_p90": None, "tau_ci_width": None, "n_feasible": 0.0}
    taus_arr = np.array(taus, dtype=float)
    conservative_p = float(max(1.0, min(50.0, conservative_percentile)))
    p10 = float(np.percentile(taus_arr, conservative_p))
    p50 = float(np.percentile(taus_arr, 50))
    p90 = float(np.percentile(taus_arr, 90))
    return {
        "tau_median": round(p50, 6),
        "tau_p10":    round(p10, 6),   # conservative operating threshold
        "tau_p90":    round(p90, 6),
        "tau_ci_width": round(p90 - p10, 6),
        "n_feasible": round(len(taus) / float(B), 4),
        "bootstrap_draws": int(B),
        "conservative_percentile": round(conservative_p, 3),
    }


def _build_routing_policy(
    limit_difficulty: float | None,
    d_safe: float | None = None,
    d_unsafe: float | None = None,
) -> dict[str, Any]:
    if limit_difficulty is None and d_safe is None:
        return {
            "limit_bin": None,
            "limit_difficulty": None,
            "d_safe": None,
            "d_unsafe": None,
            "route_rule": "Route all queries to BASELINE; no certified SLM region.",
        }
    if d_safe is not None and d_unsafe is not None and float(d_unsafe) > float(d_safe):
        return {
            "limit_bin": None,
            "limit_difficulty": float(limit_difficulty) if limit_difficulty is not None else None,
            "d_safe": float(d_safe),
            "d_unsafe": float(d_unsafe),
            "route_rule": (
                f"SLM if score <= {float(d_safe):.4f}; "
                f"HYBRID_ABSTAIN if {float(d_safe):.4f} < score < {float(d_unsafe):.4f}; "
                f"BASELINE otherwise."
            ),
        }
    if d_safe is not None:
        return {
            "limit_bin": None,
            "limit_difficulty": float(limit_difficulty) if limit_difficulty is not None else float(d_safe),
            "d_safe": float(d_safe),
            "d_unsafe": None,
            "route_rule": (
                f"SLM if score <= {float(d_safe):.4f}; BASELINE otherwise "
                "(no certified hybrid uncertainty band)."
            ),
        }
    return {
        "limit_bin": None,  # no discrete bins; kept for downstream compatibility
        "limit_difficulty": float(limit_difficulty),
        "d_safe": None,
        "d_unsafe": None,
        "route_rule": (
            f"SLM if score <= {limit_difficulty:.4f}; "
            "HYBRID_ABSTAIN within delta band; BASELINE otherwise."
        ),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _stable_split_for_sample(sample_id: str) -> str:
    digest = hashlib.sha1(str(sample_id).encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 30:
        return "train"
    # Keep split contract aligned with inference runner:
    # train = 0-29, val = 30-69, test = 70-99.
    if bucket < 70:
        return "val"
    return "test"


def _split_name_for_row(row: dict[str, Any]) -> str:
    raw = str(row.get("split") or row.get("dataset") or "").strip().lower()
    if raw in {"train", "training"}:
        return "train"
    if raw in {"val", "validation", "dev"}:
        return "val"
    if raw in {"test", "eval", "evaluation"}:
        return "test"
    return _stable_split_for_sample(str(row.get("sample_id", "")))


def _extract_feature_vector(row: dict[str, Any]) -> dict[str, float]:
    prompt = str(row.get("prompt", "") or "")
    return {dim: float(val) for dim, val in compute_all_features(row, prompt).items()}


def _fit_query_family_gmm(
    task_to_rows: dict[str, dict[str, list[dict[str, Any]]]],
    max_clusters: int = 0,
    bic_relax_frac: float = 0.02,
    min_family_fraction: float = 0.05,
    n_iter: int = 100,
) -> dict[str, Any]:
    """Fit a diagonal GMM over train-query feature vectors (task labels unused)."""
    dims = list(DIFFICULTY_FEATURES)
    vectors: list[list[float]] = []
    for _task, model_rows in task_to_rows.items():
        for _model_key, rows in model_rows.items():
            for row in rows:
                if _split_name_for_row(row) != "train":
                    continue
                features = _extract_feature_vector(row)
                vectors.append([float(features.get(dim, 0.0)) for dim in dims])
    if not vectors:
        return {
            "dims": dims,
            "mins": {dim: 0.0 for dim in dims},
            "maxs": {dim: 1.0 for dim in dims},
            "weights": [1.0],
            "means": [[0.5 for _ in dims]],
            "vars_diag": [[1.0 for _ in dims]],
            "k": 1,
            "bic": 0.0,
            "source_split": "train",
        }

    x = np.array(vectors, dtype=float)
    n, d = x.shape
    mins = np.min(x, axis=0)
    maxs = np.max(x, axis=0)
    span = np.where(maxs > mins, maxs - mins, 1.0)
    xn = np.clip((x - mins) / span, 0.0, 1.0)

    def _init_means(data: np.ndarray, k: int) -> np.ndarray:
        order = np.argsort(np.sum(data, axis=1))
        if k == 1:
            return data[[int(order[len(order) // 2])]].copy()
        idxs = [order[int(round(i * (len(order) - 1) / (k - 1)))] for i in range(k)]
        return data[idxs].copy()

    def _fit_diag(data: np.ndarray, k: int, iters: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
        reg = 1e-6
        means = _init_means(data, k)
        vars_diag = np.tile(np.var(data, axis=0) + 1e-2, (k, 1))
        mix = np.full(k, 1.0 / k, dtype=float)
        prev_ll: float | None = None
        resp = np.full((len(data), k), 1.0 / k, dtype=float)

        for _ in range(max(5, int(iters))):
            log_prob = np.empty((len(data), k), dtype=float)
            for c in range(k):
                diff = data - means[c]
                log_det = float(np.sum(np.log(vars_diag[c] + reg)))
                maha = np.sum((diff * diff) / (vars_diag[c] + reg), axis=1)
                log_gauss = -0.5 * (d * math.log(2.0 * math.pi) + log_det + maha)
                log_prob[:, c] = math.log(max(mix[c], reg)) + log_gauss
            row_max = np.max(log_prob, axis=1, keepdims=True)
            stable = log_prob - row_max
            row_logsumexp = row_max + np.log(np.sum(np.exp(stable), axis=1, keepdims=True) + reg)
            resp = np.exp(log_prob - row_logsumexp)
            ll = float(np.sum(row_logsumexp))

            nk = np.sum(resp, axis=0) + reg
            mix = nk / float(len(data))
            means = (resp.T @ data) / nk[:, None]
            for c in range(k):
                diff = data - means[c]
                vars_diag[c] = np.sum(resp[:, c][:, None] * (diff * diff), axis=0) / nk[c]
            vars_diag = np.maximum(vars_diag, reg)

            if prev_ll is not None and abs(ll - prev_ll) <= 1e-6:
                break
            prev_ll = ll

        ll_val = float(prev_ll if prev_ll is not None else -1e12)
        return mix, means, vars_diag, resp, ll_val

    candidates: list[dict[str, Any]] = []
    # If not explicitly provided, learn over an adaptive search range.
    if int(max_clusters) <= 0:
        max_clusters = max(2, min(12, int(round(math.sqrt(max(1, n))))))
    k_max = max(1, min(int(max_clusters), n))
    for k in range(1, k_max + 1):
        mix, means, vars_diag, _resp, ll_val = _fit_diag(xn, k, n_iter)
        n_params = (k - 1) + (k * d) + (k * d)
        bic = -2.0 * ll_val + float(n_params) * math.log(max(1, n))
        candidates.append(
            {
                "dims": dims,
                "mins": {dim: float(mins[i]) for i, dim in enumerate(dims)},
                "maxs": {dim: float(maxs[i]) for i, dim in enumerate(dims)},
                "weights": [float(v) for v in mix.tolist()],
                "means": [[float(v) for v in row] for row in means.tolist()],
                "vars_diag": [[float(v) for v in row] for row in vars_diag.tolist()],
                "k": int(k),
                "k_max_considered": int(k_max),
                "n_train_queries": int(n),
                "bic": float(bic),
                "source_split": "train",
            }
        )
    if not candidates:
        return {
            "dims": dims,
            "mins": {dim: 0.0 for dim in dims},
            "maxs": {dim: 1.0 for dim in dims},
            "weights": [1.0],
            "means": [[0.5 for _ in dims]],
            "vars_diag": [[1.0 for _ in dims]],
            "k": 1,
            "k_max_considered": 1,
            "n_train_queries": 0,
            "bic": 0.0,
            "source_split": "train",
        }

    best_bic = min(float(c["bic"]) for c in candidates)
    tol = max(1e-9, abs(best_bic) * max(0.0, float(bic_relax_frac)))
    eligible = [c for c in candidates if float(c["bic"]) <= (best_bic + tol)]
    selected = sorted(eligible, key=lambda c: (int(c["k"]), float(c["bic"])))[0]

    # Merge tiny families to nearest larger centroid.
    k_sel = int(selected["k"])
    mix = np.array(selected["weights"], dtype=float)
    means = np.array(selected["means"], dtype=float)
    vars_diag = np.array(selected["vars_diag"], dtype=float)
    reg = 1e-6

    log_prob = np.empty((n, k_sel), dtype=float)
    for c in range(k_sel):
        diff = xn - means[c]
        log_det = float(np.sum(np.log(vars_diag[c] + reg)))
        maha = np.sum((diff * diff) / (vars_diag[c] + reg), axis=1)
        log_gauss = -0.5 * (d * math.log(2.0 * math.pi) + log_det + maha)
        log_prob[:, c] = math.log(max(reg, mix[c])) + log_gauss
    labels = np.argmax(log_prob, axis=1)
    counts = np.bincount(labels, minlength=k_sel).astype(float)
    min_count = max(1.0, float(min_family_fraction) * float(n))
    large = [i for i, c in enumerate(counts.tolist()) if c >= min_count]
    if not large:
        large = [int(np.argmax(counts))]
    label_map = {i: i for i in large}
    for i in range(k_sel):
        if i in large:
            continue
        # nearest large component by centroid distance
        nearest = min(large, key=lambda j: float(np.sum((means[i] - means[j]) ** 2)))
        label_map[i] = nearest
    remapped = np.array([label_map[int(l)] for l in labels], dtype=int)
    uniq = sorted(set(remapped.tolist()))
    remap2 = {old: idx for idx, old in enumerate(uniq)}
    final_labels = np.array([remap2[int(v)] for v in remapped], dtype=int)
    k_final = len(uniq)

    # Recompute mixture params from reassigned labels.
    means_final = np.zeros((k_final, d), dtype=float)
    vars_final = np.zeros((k_final, d), dtype=float)
    weights_final = np.zeros(k_final, dtype=float)
    for c in range(k_final):
        pts = xn[final_labels == c]
        if len(pts) == 0:
            means_final[c] = np.mean(xn, axis=0)
            vars_final[c] = np.var(xn, axis=0) + 1e-3
            weights_final[c] = 1.0 / k_final
            continue
        means_final[c] = np.mean(pts, axis=0)
        vars_final[c] = np.var(pts, axis=0) + 1e-6
        weights_final[c] = float(len(pts)) / float(n)

    return {
        "dims": dims,
        "mins": selected["mins"],
        "maxs": selected["maxs"],
        "weights": [float(v) for v in weights_final.tolist()],
        "means": [[float(v) for v in row] for row in means_final.tolist()],
        "vars_diag": [[float(v) for v in row] for row in vars_final.tolist()],
        "k": int(k_final),
        "k_selected_before_merge": int(selected["k"]),
        "k_max_considered": int(k_max),
        "n_train_queries": int(n),
        "bic": float(selected["bic"]),
        "bic_best": float(best_bic),
        "bic_tolerance": float(tol),
        "bic_relax_frac": float(bic_relax_frac),
        "min_family_fraction": float(min_family_fraction),
        "source_split": "train",
    }

def _predict_query_family(features: dict[str, float], gmm_model: dict[str, Any]) -> str:
    dims = list(gmm_model.get("dims") or DIFFICULTY_FEATURES)
    mins = gmm_model.get("mins", {})
    maxs = gmm_model.get("maxs", {})
    mix = [float(v) for v in (gmm_model.get("weights") or [1.0])]
    means = gmm_model.get("means") or [[0.5 for _ in dims]]
    vars_diag = gmm_model.get("vars_diag") or [[1.0 for _ in dims]]
    reg = 1e-6

    x = []
    for dim in dims:
        lo = float(mins.get(dim, 0.0))
        hi = float(maxs.get(dim, 1.0))
        val = float(features.get(dim, 0.0))
        if hi <= lo:
            x.append(0.0)
        else:
            x.append(max(0.0, min(1.0, (val - lo) / (hi - lo))))
    xv = np.array(x, dtype=float)
    d = len(dims)
    logps: list[float] = []
    for c in range(len(means)):
        mu = np.array(means[c], dtype=float)
        var = np.maximum(np.array(vars_diag[c], dtype=float), reg)
        diff = xv - mu
        log_det = float(np.sum(np.log(var)))
        maha = float(np.sum((diff * diff) / var))
        log_gauss = -0.5 * (d * math.log(2.0 * math.pi) + log_det + maha)
        logps.append(math.log(max(reg, mix[c] if c < len(mix) else reg)) + log_gauss)
    idx = int(np.argmax(np.array(logps, dtype=float)))
    return f"cluster_{idx}"


def _learn_family_difficulty_models(
    task_to_rows: dict[str, dict[str, list[dict[str, Any]]]],
    reference_lookup_by_task: dict[str, dict[str, dict[str, Any]]],
    query_family_gmm: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Learn difficulty weights per latent query-family using train semantic failure."""
    pooled: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task, model_rows in task_to_rows.items():
        refs = reference_lookup_by_task.get(task, {})
        for model_key, rows in model_rows.items():
            if model_key == BASELINE_MODEL:
                continue
            for row in rows:
                if _split_name_for_row(row) != "train":
                    continue
                _cap, semantic_risk, _failure = _evaluate_row(row, refs)
                features = _extract_feature_vector(row)
                family = _predict_query_family(features, query_family_gmm)
                features["target"] = float(semantic_risk)
                pooled[family].append(features)

    learned: dict[str, dict[str, Any]] = {}
    for family, samples in pooled.items():
        learner = DifficultyWeightLearner()
        learned[family] = learner.fit(samples)
    return learned


def _score_with_family_model(
    row: dict[str, Any],
    slm_model: dict[str, Any] | None,
) -> float:
    """Score a row using a per-SLM learned weight model."""
    if not slm_model:
        return 0.0
    weights = slm_model.get("weights", {})
    norm_stats = slm_model.get("norm_stats", {})
    features = _extract_feature_vector(row)
    score = 0.0
    for dim in DIFFICULTY_FEATURES:
        val = float(features.get(dim, 0.0))
        # Norm stats now use percentile keys (p05/p95); fall back to min/max for
        # backwards compatibility with old artifacts.
        bounds = norm_stats.get(dim, {})
        lo = float(bounds.get("p05", bounds.get("min", 0.0)))
        hi = float(bounds.get("p95", bounds.get("max", 1.0)))
        if hi <= lo:
            norm_val = 0.0
        else:
            norm_val = max(0.0, min(1.0, (val - lo) / (hi - lo)))
        score += float(weights.get(dim, 0.0)) * norm_val
    return max(0.0, min(1.0, float(score)))


def _calibrate_abstention_delta(
    rows: list[dict[str, Any]],
    reference_lookup: dict[str, dict[str, Any]],
    difficulty_scores: dict[str, float],
    limit_difficulty: float | None,
    risk_threshold: float,
    cap_threshold: float,
    max_delta: float,
    grid_step: float,
) -> dict[str, Any]:
    if limit_difficulty is None:
        return {
            "delta": 0.0,
            "selected_coverage": 0.0,
            "selected_capability": 0.0,
            "selected_risk": 1.0,
            "selected_abstention_rate": 1.0,
        }

    candidates: list[float] = []
    step = max(0.001, float(grid_step))
    d = 0.0
    while d <= max(0.0, float(max_delta)) + 1e-9:
        candidates.append(round(d, 6))
        d += step

    best: dict[str, Any] | None = None
    fallback: dict[str, Any] | None = None
    total = max(1, len(rows))
    for delta in candidates:
        slm_rows = []
        abstain = 0
        for row in rows:
            sample_id = str(row["sample_id"])
            score = float(difficulty_scores.get(sample_id, 0.5))
            if score <= (limit_difficulty - delta):
                slm_rows.append(row)
            elif score < (limit_difficulty + delta):
                abstain += 1
        if slm_rows:
            cap_vals = []
            risk_vals = []
            for row in slm_rows:
                cap, risk, _ = _evaluate_row(row, reference_lookup)
                cap_vals.append(float(cap))
                risk_vals.append(float(risk))
            cap = sum(cap_vals) / len(cap_vals)
            risk = sum(risk_vals) / len(risk_vals)
        else:
            cap = 0.0
            risk = 1.0
        coverage = len(slm_rows) / total
        abstain_rate = abstain / total
        candidate = {
            "delta": delta,
            "selected_coverage": coverage,
            "selected_capability": cap,
            "selected_risk": risk,
            "selected_abstention_rate": abstain_rate,
        }
        if fallback is None or risk < fallback["selected_risk"] or (
            risk == fallback["selected_risk"] and coverage > fallback["selected_coverage"]
        ):
            fallback = candidate
        if risk <= risk_threshold and cap >= cap_threshold:
            if best is None or coverage > best["selected_coverage"]:
                best = candidate

    return best or fallback or {
        "delta": 0.0,
        "selected_coverage": 0.0,
        "selected_capability": 0.0,
        "selected_risk": 1.0,
        "selected_abstention_rate": 1.0,
    }


def _select_operational_tau(
    rows: list[dict[str, Any]],
    reference_lookup: dict[str, dict[str, Any]],
    difficulty_scores: dict[str, float],
    cap_threshold: float,
    risk_threshold: float,
    utility_alpha: float = 1.0,
    utility_beta: float = 0.25,
    utility_gamma: float = 1.0,
) -> dict[str, Any]:
    """Choose tau by constrained utility on validation rows."""
    if not rows:
        return {
            "tau": None,
            "coverage": 0.0,
            "selected_capability": 0.0,
            "selected_risk": 1.0,
            "utility": -1e9,
            "feasible": False,
            "candidates": [],
        }
    points: list[tuple[float, float, float]] = []
    for row in rows:
        sid = str(row["sample_id"])
        score = float(difficulty_scores.get(sid, 0.5))
        cap, risk, _ = _evaluate_row(row, reference_lookup)
        points.append((score, float(cap), float(risk)))
    points.sort(key=lambda t: t[0])
    if not points:
        return {
            "tau": None,
            "coverage": 0.0,
            "selected_capability": 0.0,
            "selected_risk": 1.0,
            "utility": -1e9,
            "feasible": False,
            "candidates": [],
        }

    candidates = sorted(set(score for score, _c, _r in points))
    total = float(len(points))

    # Global baselines for relative utility normalization.
    # always_slm: route everything to SLM (coverage=1, cap/risk = population average).
    # always_baseline: route everything to baseline (coverage=0, no SLM risk).
    pop_cap = sum(c for _, c, _ in points) / total
    pop_risk = sum(r for _, _, r in points) / total
    always_slm_utility_raw = float(utility_alpha) * 1.0 + float(utility_beta) * pop_cap - float(utility_gamma) * pop_risk
    always_baseline_utility_raw = float(utility_alpha) * 0.0 + float(utility_beta) * 0.0 - float(utility_gamma) * 0.0

    # Normalize utility to [0,1] relative to the [always_baseline, always_slm] range
    # so that coverage, capability, and risk contribute at the same effective scale.
    # U_rel = (U_raw - U_baseline) / max(eps, U_slm - U_baseline)
    u_range = max(1e-9, always_slm_utility_raw - always_baseline_utility_raw)

    best: dict[str, Any] | None = None
    best_feasible_utility: float = -1e9
    # τ* stability: collect all feasible taus within 5% of maximum utility.
    candidate_rows: list[dict[str, Any]] = []
    for tau in candidates:
        selected = [(c, r) for s, c, r in points if s <= tau]
        if not selected:
            continue
        cov = len(selected) / total
        cap = sum(c for c, _ in selected) / len(selected)
        risk = sum(r for _, r in selected) / len(selected)
        meets_gates = cap >= cap_threshold and risk <= risk_threshold
        # Avoid degenerate "routing" policies that are effectively always-SLM.
        coverage_ok = cov <= 0.80
        feasible = meets_gates and coverage_ok
        raw_u = float(utility_alpha) * cov + float(utility_beta) * cap - float(utility_gamma) * risk
        utility = (raw_u - always_baseline_utility_raw) / u_range  # relative, [0,1]-ish
        item = {
            "tau": float(tau),
            "coverage": float(cov),
            "selected_capability": float(cap),
            "selected_risk": float(risk),
            "utility": float(utility),
            "utility_raw": float(raw_u),
            "meets_gates": bool(meets_gates),
            "coverage_ok": bool(coverage_ok),
            "feasible": bool(feasible),
        }
        candidate_rows.append(item)
        if not feasible:
            continue
        if utility > best_feasible_utility:
            best_feasible_utility = utility
            best = item

    # τ* stability range: all feasible taus with utility within 5% of max.
    stability_threshold = best_feasible_utility - 0.05
    stable_taus = [c["tau"] for c in candidate_rows if c["feasible"] and c["utility"] >= stability_threshold]
    tau_stability_range = [float(min(stable_taus)), float(max(stable_taus))] if stable_taus else None

    if best is not None:
        best_out = dict(best)
        best_out["tau_stability_range"] = tau_stability_range
        best_out["candidates"] = [dict(c) for c in candidate_rows]
        return best_out
    return {
        "tau": None,
        "coverage": 0.0,
        "selected_capability": 0.0,
        "selected_risk": 1.0,
        "utility": -1e9,
        "utility_raw": -1e9,
        "tau_stability_range": None,
        "feasible": False,
        "candidates": [dict(c) for c in candidate_rows],
    }


def _build_margin_calibrator(
    rows: list[dict[str, Any]],
    reference_lookup: dict[str, dict[str, Any]],
    difficulty_scores: dict[str, float],
    limit_difficulty: float | None,
    num_buckets: int = 5,
) -> dict[str, Any]:
    if limit_difficulty is None or not rows:
        return {"buckets": [], "global_failure_rate": 1.0}
    samples = []
    for row in rows:
        sid = str(row["sample_id"])
        score = float(difficulty_scores.get(sid, 0.5))
        margin = abs(score - float(limit_difficulty))
        _cap, risk, _f = _evaluate_row(row, reference_lookup)
        samples.append((margin, float(risk)))
    if not samples:
        return {"buckets": [], "global_failure_rate": 1.0}
    samples.sort(key=lambda item: item[0])
    n = len(samples)
    k = max(1, int(num_buckets))
    buckets = []
    for b in range(k):
        lo = int(b * n / k)
        hi = int((b + 1) * n / k)
        if hi <= lo:
            continue
        chunk = samples[lo:hi]
        max_margin = max(m for m, _ in chunk)
        failure_rate = sum(r for _, r in chunk) / len(chunk)
        buckets.append({"max_margin": float(max_margin), "failure_rate": float(failure_rate)})
    global_rate = sum(r for _, r in samples) / len(samples)
    return {"buckets": buckets, "global_failure_rate": float(global_rate)}


def _estimate_certified_band(
    rows: list[dict[str, Any]],
    reference_lookup: dict[str, dict[str, Any]],
    difficulty_scores: dict[str, float],
    cap_threshold: float,
    risk_threshold: float,
    min_k: int,
    ci_level: float,
) -> dict[str, Any]:
    """Estimate certified safe and unsafe boundaries on validation.

    d_safe:  highest difficulty where cap lower bound >= threshold and risk upper bound <= threshold.
    d_unsafe: first difficulty above d_safe where certification fails.
    """
    triples: list[tuple[float, float, float]] = []
    for row in rows:
        sid = str(row["sample_id"])
        d = float(difficulty_scores.get(sid, 0.5))
        cap, risk, _ = _evaluate_row(row, reference_lookup)
        triples.append((d, float(cap), float(risk)))
    if len(triples) < max(2, int(min_k)):
        return {
            "d_safe": None,
            "d_unsafe": None,
            "certified_points": [],
            "certified_safe_fraction": 0.0,
        }
    triples.sort(key=lambda t: t[0])
    xs = [t[0] for t in triples]
    cap_raw = [t[1] for t in triples]
    risk_raw = [t[2] for t in triples]
    candidates = sorted(set(xs))
    cert_rows: list[dict[str, Any]] = []
    for d in candidates:
        _, cap_lo = _local_beta_at(d, xs, cap_raw, min_k, ci_level, upper=False)
        _, risk_hi = _local_beta_at(d, xs, risk_raw, min_k, ci_level, upper=True)
        safe = bool(cap_lo >= cap_threshold and risk_hi <= risk_threshold)
        cert_rows.append(
            {
                "d": float(d),
                "capability_lower_ci": float(cap_lo),
                "risk_upper_ci": float(risk_hi),
                "certified_safe": safe,
            }
        )
    safe_ds = [r["d"] for r in cert_rows if r["certified_safe"]]
    if not safe_ds:
        return {
            "d_safe": None,
            "d_unsafe": candidates[0] if candidates else None,
            "certified_points": cert_rows,
            "certified_safe_fraction": 0.0,
        }
    d_safe = max(float(d) for d in safe_ds)
    d_unsafe: float | None = None
    for row in cert_rows:
        d = float(row["d"])
        if d > d_safe and not bool(row["certified_safe"]):
            d_unsafe = d
            break
    if d_unsafe is None:
        # If we never observed failure after safe region, keep hybrid empty by default.
        d_unsafe = d_safe
    return {
        "d_safe": float(d_safe),
        "d_unsafe": float(d_unsafe),
        "certified_points": cert_rows,
        "certified_safe_fraction": float(len(safe_ds) / max(1, len(cert_rows))),
    }


def _tau_uncertainty_band(
    rows: list[dict[str, Any]],
    difficulty_scores: dict[str, float],
    tau: float | None,
    min_k: int,
) -> tuple[float | None, float | None]:
    """Fallback hybrid band around tau using local difficulty density."""
    if tau is None or not rows:
        return None, None
    t = float(tau)
    dists: list[float] = []
    for row in rows:
        sid = str(row.get("sample_id"))
        d = float(difficulty_scores.get(sid, 0.5))
        dists.append(abs(d - t))
    if not dists:
        return None, None
    dists.sort()
    k = max(3, min(int(min_k), len(dists)))
    width = float(dists[k - 1])
    width = max(0.01, min(0.20, width))
    lo = max(0.0, t - width)
    hi = min(1.0, t + width)
    if hi <= lo:
        return None, None
    return float(lo), float(hi)


def _calibrated_confidence_from_margin(margin: float, calibrator: dict[str, Any]) -> float:
    buckets = calibrator.get("buckets") or []
    if not buckets:
        return max(0.0, 1.0 - float(calibrator.get("global_failure_rate", 1.0)))
    m = float(margin)
    for bucket in buckets:
        if m <= float(bucket.get("max_margin", 0.0)):
            return max(0.0, 1.0 - float(bucket.get("failure_rate", 1.0)))
    return max(0.0, 1.0 - float(buckets[-1].get("failure_rate", 1.0)))


def _route_state(
    score: float,
    limit: float | None,
    delta: float,
    d_safe: float | None = None,
    d_unsafe: float | None = None,
) -> str:
    if d_safe is not None and d_unsafe is not None and float(d_unsafe) > float(d_safe):
        if score <= float(d_safe):
            return "SLM"
        if score < float(d_unsafe):
            return "HYBRID_ABSTAIN"
        return "BASELINE"
    if d_safe is not None:
        return "SLM" if score <= float(d_safe) else "BASELINE"
    if limit is None:
        return "BASELINE"
    if score <= (limit - delta):
        return "SLM"
    if score < (limit + delta):
        return "HYBRID_ABSTAIN"
    return "BASELINE"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SDDF curves, thresholds, and routing artifacts.")
    parser.add_argument("--cap-threshold", type=float, default=DEFAULT_CAPABILITY_THRESHOLD)
    parser.add_argument("--risk-threshold", type=float, default=DEFAULT_RISK_THRESHOLD)
    parser.add_argument("--ci-level", type=float, default=DEFAULT_WILSON_CONFIDENCE_LEVEL)
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    parser.add_argument(
        "--val-count-per-task",
        type=int,
        default=0,
        help="If >0, force exactly this many sample_ids per task into val split (shared across models).",
    )
    parser.add_argument(
        "--train-min-count",
        type=int,
        default=30,
        help="Minimum train sample_ids per task when val-count override is enabled.",
    )
    parser.add_argument("--min-ground-truth-coverage", type=float, default=DEFAULT_MIN_GROUND_TRUTH_COVERAGE)
    parser.add_argument(
        "--max-families",
        type=int,
        default=0,
        help="Max latent query families for GMM search. 0=auto via sqrt(n_train), capped at 12.",
    )
    parser.add_argument(
        "--bic-relax-frac",
        type=float,
        default=0.02,
        help="Pick the smallest K whose BIC is within this fraction of the best |BIC|.",
    )
    parser.add_argument(
        "--min-family-fraction",
        type=float,
        default=0.05,
        help="Minimum train-share per family; smaller families are merged to nearest centroid.",
    )
    parser.add_argument("--utility-alpha", type=float, default=1.0, help="Utility weight for SLM coverage.")
    parser.add_argument("--utility-beta", type=float, default=0.25, help="Utility weight for capability quality.")
    parser.add_argument("--utility-gamma", type=float, default=1.0, help="Utility penalty weight for risk.")
    parser.add_argument(
        "--task-utility-coeffs",
        type=Path,
        default=None,
        help="Optional JSON mapping task -> {alpha,beta,gamma}. Overrides global utility coefficients per task.",
    )
    parser.add_argument("--report-split", type=str, default="test", help="Split being evaluated (default: test).")
    parser.add_argument(
        "--weights-source-split",
        type=str,
        default=None,
        help="Required when --difficulty-weights is set. Must be train/val/train+val (never test).",
    )
    parser.add_argument(
        "--difficulty-weights",
        type=Path,
        default=None,
        help="Optional JSON with feature weights. Enables weighted difficulty scoring for canonical rows.",
    )
    parser.add_argument(
        "--abstain-max-delta",
        type=float,
        default=0.35,
        help="Maximum abstention half-band width around routing cutoff during validation calibration.",
    )
    parser.add_argument(
        "--abstain-grid-step",
        type=float,
        default=0.01,
        help="Grid step for validation calibration of abstention half-band width.",
    )
    parser.add_argument(
        "--tau-bootstrap-draws",
        type=int,
        default=200,
        help="Bootstrap draws for tau stability CI (default: 200).",
    )
    parser.add_argument(
        "--tau-conservative-percentile",
        type=float,
        default=10.0,
        help="Conservative percentile used for operating tau from bootstrap (default: 10).",
    )
    parser.add_argument(
        "--task-thresholds",
        type=Path,
        default=None,
        help=(
            "JSON file with per-task cap/risk thresholds. "
            "Keys are task names, values are {cap, risk}. "
            "Overrides --cap-threshold and --risk-threshold for matching tasks."
        ),
    )
    return parser.parse_args()


def _load_difficulty_weights(path: Path | None) -> dict[str, float] | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Difficulty weights file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    weights: dict[str, float] = {}
    for feature in DIFFICULTY_FEATURES:
        raw = payload.get(feature, payload.get(f"difficulty_feature_{feature}", 0.0))
        try:
            weights[feature] = float(raw)
        except (TypeError, ValueError):
            weights[feature] = 0.0
    return weights


def _load_task_utility_coeffs(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Task utility coeffs file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    if not isinstance(payload, dict):
        return out
    raw_tasks = payload.get("tasks", payload)
    if not isinstance(raw_tasks, dict):
        return out
    for task, cfg in raw_tasks.items():
        if not isinstance(cfg, dict):
            continue
        try:
            a = float(cfg.get("alpha", cfg.get("utility_alpha", 1.0)))
            b = float(cfg.get("beta", cfg.get("utility_beta", 0.25)))
            g = float(cfg.get("gamma", cfg.get("utility_gamma", 1.0)))
        except (TypeError, ValueError):
            continue
        out[str(task)] = {"alpha": a, "beta": b, "gamma": g}
    return out


def _validate_split_contract(
    difficulty_weights: dict[str, float] | None,
    weights_source_split: str | None,
    report_split: str,
) -> tuple[str, str]:
    report = (report_split or "").strip().lower()
    if report not in {"train", "val", "test", "eval", "evaluation"}:
        raise ValueError(f"Unsupported --report-split '{report_split}'. Use train/val/test.")
    if report in {"eval", "evaluation"}:
        report = "test"

    if difficulty_weights is None:
        return report, "none"

    if not weights_source_split:
        raise ValueError(
            "--weights-source-split is required when --difficulty-weights is provided "
            "(must be train, val, or train+val; never test)."
        )

    src = weights_source_split.strip().lower().replace(" ", "")
    if src in {"eval", "evaluation"}:
        src = "test"
    allowed = {"train", "val", "train+val", "trainval"}
    if src not in allowed:
        raise ValueError(f"Invalid --weights-source-split '{weights_source_split}'.")
    if src in {"test"}:
        raise ValueError("Data leakage guard: weights cannot be sourced from test/evaluation split.")
    return report, ("train+val" if src == "trainval" else src)


def _weighted_difficulty_scores(rows: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, float]:
    raw_scores: dict[str, float] = {}
    for row in rows:
        sample_id = str(row["sample_id"])
        prompt = str(row.get("prompt", "") or "")
        features = compute_all_features(row, prompt)
        raw_scores[sample_id] = sum(weights.get(dim, 0.0) * float(features.get(dim, 0.0)) for dim in DIFFICULTY_FEATURES)
    if not raw_scores:
        return raw_scores
    lo = min(raw_scores.values())
    hi = max(raw_scores.values())
    if hi <= lo:
        return {sample_id: 0.5 for sample_id in raw_scores}
    return {sample_id: (value - lo) / (hi - lo) for sample_id, value in raw_scores.items()}


def _build_task_split_override(
    sample_ids: set[str],
    val_count: int,
    train_min_count: int,
) -> dict[str, str]:
    ids = sorted(sample_ids, key=lambda sid: hashlib.sha1(str(sid).encode("utf-8")).hexdigest())
    n = len(ids)
    if n == 0:
        return {}
    max_val = max(0, n - 2)
    val_n = min(max(0, int(val_count)), max_val)
    remaining = n - val_n
    if remaining <= 1:
        train_n = max(1, remaining)
    else:
        train_n = max(int(train_min_count), int(round(remaining * 0.6)))
        train_n = min(train_n, remaining - 1)
        train_n = max(1, train_n)
    split_map: dict[str, str] = {}
    for sid in ids[:val_n]:
        split_map[sid] = "val"
    for sid in ids[val_n:val_n + train_n]:
        split_map[sid] = "train"
    for sid in ids[val_n + train_n:]:
        split_map[sid] = "test"
    return split_map


def _fit_weight_model(
    task_name: str,
    model_key: str,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Module-level worker — must be top-level for ProcessPoolExecutor pickling."""
    return DifficultyWeightLearner().fit(samples)


def main() -> None:
    args = _parse_args()
    min_samples = max(1, int(args.min_samples))
    ci_level = max(0.50, min(0.999, float(args.ci_level)))
    wilson_z = _z_from_confidence(ci_level)
    min_ground_truth_coverage = max(0.0, min(1.0, float(args.min_ground_truth_coverage)))
    difficulty_weights = _load_difficulty_weights(args.difficulty_weights)
    task_utility_coeffs = _load_task_utility_coeffs(args.task_utility_coeffs)
    report_split, weights_source_split = _validate_split_contract(
        difficulty_weights,
        args.weights_source_split,
        args.report_split,
    )
    # Load per-task cap/risk thresholds (overrides global defaults per task)
    task_threshold_map: dict[str, dict[str, float]] = {}
    if args.task_thresholds and Path(args.task_thresholds).exists():
        raw_tt = json.loads(Path(args.task_thresholds).read_text(encoding="utf-8"))
        for tname, tcfg in raw_tt.items():
            if tname.startswith("_"):
                continue
            if isinstance(tcfg, dict):
                task_threshold_map[tname] = {
                    "cap":  float(tcfg.get("cap",  args.cap_threshold)),
                    "risk": float(tcfg.get("risk", args.risk_threshold)),
                }

    def _router_for(task_name: str) -> GeneralizedRoutingFramework:
        tcfg = task_threshold_map.get(task_name, {})
        return GeneralizedRoutingFramework(
            capability_threshold=tcfg.get("cap",  float(args.cap_threshold)),
            risk_threshold=      tcfg.get("risk", float(args.risk_threshold)),
            wilson_z=wilson_z,
            wilson_confidence_level=ci_level,
        )

    # Default router (used when no per-task override exists)
    router = _router_for("")
    task_summaries: dict[str, Any] = {}

    # First pass: collect task/model rows and references once.
    task_available_rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
    reference_lookup_by_task: dict[str, dict[str, dict[str, Any]]] = {}
    task_dirs = sorted(p for p in BENCHMARK_ROOT.iterdir() if p.is_dir() and p.name in SUPPORTED_TASKS)
    for task_dir in task_dirs:
        available = {}
        for model_key in CANONICAL_MODELS:
            model_dir = task_dir / model_key
            rows: list[dict[str, Any]] = []
            # Load split-specific files first (new pipeline)
            for split_name in ("train", "val", "test"):
                p = model_dir / f"outputs_{split_name}.jsonl"
                if p.exists():
                    rows.extend(_load_jsonl(p))
            # Fall back to legacy single file
            if not rows:
                legacy = model_dir / "outputs.jsonl"
                if legacy.exists():
                    rows = _load_jsonl(legacy)
            if rows:
                available[model_key] = _dedupe_rows(rows)
        if len(available) < 2 or BASELINE_MODEL not in available:
            continue
        task_available_rows[task_dir.name] = available
        reference_lookup_by_task[task_dir.name] = _build_reference_lookup(task_dir.name)

    # Optional deterministic split override to increase validation sample size.
    if int(args.val_count_per_task) > 0:
        for task_name, available_rows in task_available_rows.items():
            shared_ids: set[str] | None = None
            for _model_key, rows in available_rows.items():
                ids = {str(r.get("sample_id", "")) for r in rows if str(r.get("sample_id", "")).strip()}
                shared_ids = ids if shared_ids is None else (shared_ids & ids)
            shared_ids = shared_ids or set()
            split_override = _build_task_split_override(
                shared_ids,
                val_count=int(args.val_count_per_task),
                train_min_count=int(args.train_min_count),
            )
            for _model_key, rows in available_rows.items():
                for row in rows:
                    sid = str(row.get("sample_id", ""))
                    if sid in split_override:
                        row["split"] = split_override[sid]

    # Use existing tasks as families and learn one weight model per task-family.
    # Training target = max(0, baseline_cap - slm_cap): 1 when SLM fails but baseline
    # succeeds (route to baseline), 0 when SLM matches baseline (SLM is fine).
    # This is the true routing signal — not the hand-crafted sev×und product.

    # Build (task, model_key, samples) tuples — one fit job per SLM per task.
    fit_jobs: list[tuple[str, str, list[dict[str, Any]]]] = []
    for task_name, model_rows in task_available_rows.items():
        refs = reference_lookup_by_task.get(task_name, {})
        baseline_cap_by_sid: dict[str, float] = {}
        if BASELINE_MODEL in model_rows:
            for row in model_rows[BASELINE_MODEL]:
                if _split_name_for_row(row) != "train":
                    continue
                sid = str(row.get("sample_id", ""))
                if sid not in refs:
                    continue
                cap, _risk, _failure = _evaluate_row(row, refs)
                baseline_cap_by_sid[sid] = float(cap)

        for model_key, rows in model_rows.items():
            if model_key == BASELINE_MODEL:
                continue
            samples: list[dict[str, Any]] = []
            for row in rows:
                if _split_name_for_row(row) != "train":
                    continue
                sid = str(row.get("sample_id", ""))
                if sid not in refs:
                    continue
                slm_cap, _risk, _failure = _evaluate_row(row, refs)
                baseline_cap = baseline_cap_by_sid.get(sid, 1.0)
                # Binary routing signal: 1 = "should route to LLM" (SLM failed, LLM succeeded)
                #                        0 = "SLM is fine" (SLM succeeded, or both failed)
                # Continuous difference conflated partial failures with complete failures.
                # Binary signal is the correct decision-theoretic target for a routing classifier.
                routing_target = 1.0 if (float(slm_cap) < 0.5 and float(baseline_cap) >= 0.5) else 0.0
                sample = _extract_feature_vector(row)
                sample["target"] = routing_target
                samples.append(sample)
            if samples:
                fit_jobs.append((task_name, model_key, samples))

    # Fit all jobs concurrently across CPU cores.
    task_family_weight_models: dict[str, dict[str, Any]] = {}
    n_workers = min(len(fit_jobs), 8)
    print(f"[SDDF] Fitting {len(fit_jobs)} weight models with {n_workers} workers...")
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {
            pool.submit(_fit_weight_model, task_name, model_key, samples): (task_name, model_key)
            for task_name, model_key, samples in fit_jobs
        }
        for fut in as_completed(futures):
            task_name, model_key = futures[fut]
            try:
                result = fut.result()
                task_family_weight_models.setdefault(task_name, {})[model_key] = result
                print(f"[SDDF]   fit done: {task_name}/{model_key}")
            except Exception as exc:
                print(f"[SDDF]   fit FAILED {task_name}/{model_key}: {exc}")

    weights_out = BENCHMARK_ROOT / "difficulty_weights" / "family_weights_learned.json"
    _write_json(
        weights_out,
        {
            "source_split": "train",
            "model_type": "task_per_slm_difficulty_weights",
            "families": task_family_weight_models,
            "features": list(DIFFICULTY_FEATURES),
        },
    )

    for task_dir in task_dirs:
        if task_dir.name not in task_available_rows:
            continue
        available = task_available_rows[task_dir.name]
        reference_lookup = reference_lookup_by_task.get(task_dir.name, {})
        utility_cfg = task_utility_coeffs.get(task_dir.name, {})
        task_utility_alpha = float(utility_cfg.get("alpha", args.utility_alpha))
        task_utility_beta = float(utility_cfg.get("beta", args.utility_beta))
        task_utility_gamma = float(utility_cfg.get("gamma", args.utility_gamma))
        # Per-task router with task-specific cap/risk thresholds
        router = _router_for(task_dir.name)

        baseline_ids = {str(row["sample_id"]) for row in available[BASELINE_MODEL]}
        all_model_common_ids = baseline_ids.copy()
        per_model_common_ids: dict[str, set[str]] = {}
        for model_key, rows in available.items():
            model_ids = {str(row["sample_id"]) for row in rows}
            per_model_common_ids[model_key] = model_ids & baseline_ids
            all_model_common_ids &= model_ids

        task_rows: dict[str, list[dict[str, Any]]] = {}
        cap_curves_by_model: dict[str, tuple[list[float], list[float], list[float]]] = {}
        risk_curves_by_model: dict[str, tuple[list[float], list[float], list[float]]] = {}
        thresholds: dict[str, Any] = {}
        decision_metrics: dict[str, dict[str, Any]] = {}
        difficulty_scores_by_model: dict[str, dict[str, float]] = {}
        ground_truth_coverage_by_model: dict[str, dict[str, float]] = {}

        for model_key, rows in available.items():
            model_common_ids = per_model_common_ids[model_key]
            filtered_all = [
                row
                for row in rows
                if str(row["sample_id"]) in model_common_ids and str(row["sample_id"]) in reference_lookup
            ]
            if not filtered_all:
                continue

            # Split-aware partitioning with deterministic fallback.
            report_rows = [row for row in filtered_all if _split_name_for_row(row) == report_split]
            if not report_rows:
                raise RuntimeError(
                    f"No rows found for report_split='{report_split}' "
                    f"(task={task_dir.name}, model={model_key}). "
                    "Refusing to fall back to mixed splits because that would "
                    "invalidate phase-specific train/val/test claims."
                )
            val_rows_raw   = [row for row in filtered_all if _split_name_for_row(row) == "val"]
            train_rows_raw = [row for row in filtered_all if _split_name_for_row(row) == "train"]

            # Difficulty score: per-SLM learned weights -> explicit weights -> uniform fallback.
            # task_family_weight_models[task][model_key] = slm-specific learned model.
            task_slm_models = task_family_weight_models.get(task_dir.name, {})
            slm_model = task_slm_models.get(model_key)
            if slm_model:
                difficulty_scores_by_model[model_key] = {
                    str(row["sample_id"]): _score_with_family_model(row, slm_model) for row in filtered_all
                }
                difficulty_source = "learned_per_slm_weighted_features"
                weights_used = slm_model.get("weights", {})
                dominant_family = f"{task_dir.name}/{model_key}"
            elif difficulty_weights:
                difficulty_scores_by_model[model_key] = _weighted_difficulty_scores(filtered_all, difficulty_weights)
                difficulty_source = "weighted_features"
                weights_used = difficulty_weights
                dominant_family = "external_weights"
            else:
                uniform_w = {dim: 1.0 / len(DIFFICULTY_FEATURES) for dim in DIFFICULTY_FEATURES}
                difficulty_scores_by_model[model_key] = _weighted_difficulty_scores(filtered_all, uniform_w)
                difficulty_source = "uniform_feature_weights_fallback"
                weights_used = uniform_w
                dominant_family = "uniform"

            scores_map = difficulty_scores_by_model[model_key]

            task_rows[model_key] = report_rows
            gt_matched = sum(1 for row in report_rows if _resolve_reference(row, reference_lookup))
            gt_total = len(report_rows)
            ground_truth_coverage = (gt_matched / gt_total) if gt_total else 0.0
            ground_truth_coverage_by_model[model_key] = {
                "matched_ground_truth_count": gt_matched,
                "total_evaluated_count": gt_total,
                "ground_truth_coverage": ground_truth_coverage,
            }
            if ground_truth_coverage < min_ground_truth_coverage:
                raise RuntimeError(
                    f"Ground-truth coverage below threshold for task={task_dir.name}, model={model_key}: "
                    f"{ground_truth_coverage:.3f} < {min_ground_truth_coverage:.3f}. "
                    "Provide independent ground-truth files under data/ground_truth/<task>.jsonl or .json."
                )

            # TASK+MODEL local fit on train rows.
            if not train_rows_raw:
                raise RuntimeError(
                    f"No train rows for task={task_dir.name}, model={model_key}. "
                    "Refusing to fall back to test rows for curve fitting — "
                    "that would leak evaluation data into the model. "
                    "Check that --report-split is 'test' and that the split thresholds "
                    "in _stable_split_for_sample assign at least some rows to 'train'."
                )
            curve_source = train_rows_raw
            (
                cap_curve,
                risk_curve,
                failure_counts,
                train_failure_risk_curves,
                train_risk_category_curves,
            ) = _fit_continuous_curves(
                curve_source, scores_map, reference_lookup
            )
            cap_xs, cap_iso, cap_raw_vals = cap_curve
            risk_xs, risk_iso, risk_raw_vals = risk_curve

            # VAL: fit val curves independently, check calibration against train, find τ*.
            val_calibration_check: dict[str, Any] = {}
            if val_rows_raw and len(val_rows_raw) >= min_samples:
                (
                    val_cap_curve,
                    val_risk_curve,
                    _,
                    val_failure_risk_curves,
                    val_risk_category_curves,
                ) = _fit_continuous_curves(
                    val_rows_raw, scores_map, reference_lookup
                )
                val_xs, val_cap_iso, val_cap_raw = val_cap_curve
                _,      val_risk_iso, val_risk_raw = val_risk_curve
                val_has_support = len(val_xs) >= min_samples
                if val_has_support and cap_xs:
                    # Sample ~10 evenly-spaced val scores and compare train vs val predictions.
                    check_xs = val_xs[::max(1, len(val_xs) // 10)]
                    for x in check_xs:
                        val_calibration_check[f"{x:.3f}"] = {
                            "train_capability": round(_evaluate_curve(cap_xs,  cap_iso,  x), 4),
                            "val_capability":   round(_evaluate_curve(val_xs,  val_cap_iso, x), 4),
                            "capability_error": round(abs(_evaluate_curve(cap_xs, cap_iso, x) - _evaluate_curve(val_xs, val_cap_iso, x)), 4),
                            "train_risk":  round(_evaluate_curve(risk_xs, risk_iso, x), 4),
                            "val_risk":    round(_evaluate_curve(val_xs,  val_risk_iso, x), 4),
                            "risk_error":  round(abs(_evaluate_curve(risk_xs, risk_iso, x) - _evaluate_curve(val_xs, val_risk_iso, x)), 4),
                        }
            else:
                val_has_support = False
                val_xs, val_cap_iso, val_cap_raw   = cap_xs,  cap_iso,  cap_raw_vals
                val_risk_iso, val_risk_raw           = risk_iso, risk_raw_vals
                val_failure_risk_curves = train_failure_risk_curves
                val_risk_category_curves = train_risk_category_curves

            # Plot and downstream expectations use validation curves when available.
            if val_has_support:
                plot_cap_xs, plot_cap_iso, plot_cap_raw = val_xs, val_cap_iso, val_cap_raw
                plot_risk_xs, plot_risk_iso, plot_risk_raw = val_xs, val_risk_iso, val_risk_raw
                plot_failure_risk_curves = val_failure_risk_curves
                plot_risk_category_curves = val_risk_category_curves
                curve_source_level = "val"
            else:
                plot_cap_xs, plot_cap_iso, plot_cap_raw = cap_xs, cap_iso, cap_raw_vals
                plot_risk_xs, plot_risk_iso, plot_risk_raw = risk_xs, risk_iso, risk_raw_vals
                plot_failure_risk_curves = train_failure_risk_curves
                plot_risk_category_curves = train_risk_category_curves
                curve_source_level = "train_fallback"

            cap_curves_by_model[model_key] = (plot_cap_xs, plot_cap_iso, plot_cap_raw)
            risk_curves_by_model[model_key] = (plot_risk_xs, plot_risk_iso, plot_risk_raw)

            # τ* SELECTION: use val rows to scan for feasible threshold, but evaluate
            # the LOCAL PROBABILITY ESTIMATE using TRAIN curve points (cap_xs, cap_raw_vals).
            # This separates (1) where the threshold lives (val) from (2) the probability
            # model used to certify it (train), preventing double-dipping.
            # Fallback: if no val rows, use train rows for both (reported as train_fallback).
            threshold_split_used = "val" if val_has_support else "train_fallback"
            threshold_rows = val_rows_raw if val_has_support else train_rows_raw
            # Curve rows for local k-NN estimation always come from TRAIN — never val.
            # This is the key anti-double-dipping fix: val rows select the threshold,
            # train rows supply the probability model evaluated at that threshold.
            curve_rows_for_tau = train_rows_raw if train_rows_raw else threshold_rows
            # k proportional to curve-source size: ~10% of rows, bounded [min_samples, 30].
            # This keeps CI estimation tied to the data that certifies the operating region.
            adaptive_min_k = max(min_samples, min(30, len(curve_rows_for_tau) // 10))
            tau_choice = _select_operational_tau(
                threshold_rows,
                reference_lookup,
                scores_map,
                cap_threshold=router.capability_threshold,
                risk_threshold=router.risk_threshold,
                utility_alpha=task_utility_alpha,
                utility_beta=task_utility_beta,
                utility_gamma=task_utility_gamma,
            )
            # Bootstrap τ* CI on val rows — addresses point-estimate variance.
            # Combined with train-curve evaluation above, this provides both
            # bias correction (train/val separation) and variance correction (bootstrap).
            # Use the 10th-percentile (conservative) as the actual operating threshold.
            tau_bootstrap = _bootstrap_tau_ci(
                threshold_rows,
                reference_lookup,
                scores_map,
                cap_threshold=router.capability_threshold,
                risk_threshold=router.risk_threshold,
                utility_alpha=task_utility_alpha,
                utility_beta=task_utility_beta,
                utility_gamma=task_utility_gamma,
                B=max(50, int(args.tau_bootstrap_draws)),
                conservative_percentile=float(args.tau_conservative_percentile),
            )
            # If bootstrap gives a valid conservative estimate, prefer it over point τ*.
            tau_point = tau_choice.get("tau")
            tau_conservative = tau_bootstrap.get("tau_p10")
            limit_difficulty = tau_conservative if tau_conservative is not None else tau_point
            certified_band = _estimate_certified_band(
                curve_rows_for_tau,
                reference_lookup,
                scores_map,
                cap_threshold=router.capability_threshold,
                risk_threshold=router.risk_threshold,
                min_k=adaptive_min_k,
                ci_level=router.wilson_confidence_level,
            )
            d_safe = certified_band.get("d_safe")
            d_unsafe = certified_band.get("d_unsafe")
            band_source = "certified"
            if (
                (d_safe is None)
                or (d_unsafe is None)
                or not (float(d_unsafe) > float(d_safe))
            ):
                fb_safe, fb_unsafe = _tau_uncertainty_band(
                    threshold_rows,
                    scores_map,
                    limit_difficulty,
                    min_k=min_samples,
                )
                if fb_safe is not None and fb_unsafe is not None and float(fb_unsafe) > float(fb_safe):
                    d_safe, d_unsafe = fb_safe, fb_unsafe
                    band_source = "tau_uncertainty_fallback"

            confidence_routing_policy = _build_routing_policy(
                limit_difficulty,
                d_safe=d_safe,
                d_unsafe=d_unsafe,
            )
            confidence_routing_policy["threshold_source"] = (
                "continuous_knn_beta" if limit_difficulty is not None
                else "continuous_knn_beta_no_safe_region"
            )
            abstention = _calibrate_abstention_delta(
                threshold_rows, reference_lookup, scores_map, limit_difficulty,
                router.risk_threshold, router.capability_threshold,
                max_delta=float(args.abstain_max_delta),
                grid_step=float(args.abstain_grid_step),
            )
            policy_half_width = float(abstention["delta"])
            if d_safe is not None and d_unsafe is not None and float(d_unsafe) > float(d_safe):
                policy_half_width = float(float(d_unsafe) - float(d_safe)) / 2.0
            confidence_routing_policy["abstention_band_half_width"] = policy_half_width
            confidence_routing_policy["route_rule_with_abstention"] = str(confidence_routing_policy.get("route_rule") or "")
            margin_calibrator = _build_margin_calibrator(
                threshold_rows, reference_lookup, scores_map, limit_difficulty,
            )
            confidence_routing_policy["margin_confidence_calibration"] = margin_calibrator
            confidence_routing_policy["certified_band"] = certified_band
            confidence_routing_policy["hybrid_band_source"] = band_source

            avg_cap  = sum(plot_cap_iso)  / len(plot_cap_iso)  if plot_cap_iso  else 0.0
            avg_risk = sum(plot_risk_iso) / len(plot_risk_iso) if plot_risk_iso else 0.0

            thresholds[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "matched_query_count": len(report_rows),
                "train_curve_row_count": len(curve_source),
                "val_threshold_row_count": len(val_rows_raw),
                "wilson_confidence_level": router.wilson_confidence_level,
                "tau_star_difficulty": limit_difficulty,
                "capability_curve": _curve_to_dict(plot_cap_xs, plot_cap_iso),
                "capability_curve_raw": _curve_to_dict(plot_cap_xs, plot_cap_raw),
                "risk_curve": _curve_to_dict(plot_risk_xs, plot_risk_iso),
                "risk_curve_raw": _curve_to_dict(plot_risk_xs, plot_risk_raw),
                "train_capability_curve": _curve_to_dict(cap_xs, cap_iso),
                "train_risk_curve": _curve_to_dict(risk_xs, risk_iso),
                "val_capability_curve": _curve_to_dict(val_xs, val_cap_iso),
                "val_risk_curve": _curve_to_dict(val_xs, val_risk_iso),
                "risk_curves_by_failure_type": _serialize_failure_risk_curves(plot_failure_risk_curves),
                "train_risk_curves_by_failure_type": _serialize_failure_risk_curves(train_failure_risk_curves),
                "val_risk_curves_by_failure_type": _serialize_failure_risk_curves(val_failure_risk_curves),
                "risk_curves_by_category": _serialize_failure_risk_curves(plot_risk_category_curves),
                "train_risk_curves_by_category": _serialize_failure_risk_curves(train_risk_category_curves),
                "val_risk_curves_by_category": _serialize_failure_risk_curves(val_risk_category_curves),
                "semantic_failure_counts": failure_counts,
                "difficulty_score_source": difficulty_source,
                "difficulty_weights_used": weights_used,
                "difficulty_family": dominant_family,
                "curve_fit_level": f"task_model_local_{curve_source_level}",
                "report_split": report_split,
                "curve_source_split": "train" if train_rows_raw else "report_fallback",
                "threshold_split": threshold_split_used,
                "val_calibration_check": val_calibration_check,
                "weights_source_split": weights_source_split,
                "threshold_method": "continuous_kernel_knn_beta_bootstrap",
                "abstention_calibration": abstention,
                "tau_utility_selection": tau_choice,
                "tau_bootstrap_ci": tau_bootstrap,
                "tau_bootstrap_draws": int(max(50, int(args.tau_bootstrap_draws))),
                "tau_conservative_percentile": float(args.tau_conservative_percentile),
                "task_utility_coefficients": {
                    "alpha": task_utility_alpha,
                    "beta": task_utility_beta,
                    "gamma": task_utility_gamma,
                },
                "d_safe": d_safe,
                "d_unsafe": d_unsafe,
                "hybrid_band_source": band_source,
                "hybrid_band_width": (
                    float(d_unsafe) - float(d_safe)
                    if d_safe is not None and d_unsafe is not None and float(d_unsafe) > float(d_safe)
                    else 0.0
                ),
                **ground_truth_coverage_by_model[model_key],
            }

            decision_metrics[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "avg_capability": avg_cap,
                "avg_risk": avg_risk,
                "avg_expected_risk": avg_risk,          # kept for plot compatibility
                "tau_star_difficulty": limit_difficulty,
                "tau_cap_difficulty": limit_difficulty,  # kept for plot compatibility
                "risk_safety_score": 1.0 - float(limit_difficulty or 1.0),
                "tau_quadrant": (
                    "Baseline-first"           if limit_difficulty is None
                    else "Broad SLM Safe"      if limit_difficulty >= 0.5 and avg_risk <= router.risk_threshold
                    else "Capable but risk-limited" if limit_difficulty >= 0.5
                    else "Narrow SLM Safe"     if avg_risk <= router.risk_threshold
                    else "Baseline-first"
                ),
                "confidence_certified_routing_policy": confidence_routing_policy,
            }

        sddf_dir = task_dir / "sddf"
        sddf_dir.mkdir(parents=True, exist_ok=True)
        canonical_rows_path = sddf_dir / "canonical_rows.jsonl"
        with canonical_rows_path.open("w", encoding="utf-8") as handle:
            for model_key, rows in task_rows.items():
                policy = decision_metrics.get(model_key, {}).get("confidence_certified_routing_policy", {})
                limit_difficulty = policy.get("limit_difficulty")
                delta = float(policy.get("abstention_band_half_width", 0.0) or 0.0)
                d_safe = policy.get("d_safe")
                d_unsafe = policy.get("d_unsafe")
                margin_calibrator = policy.get("margin_confidence_calibration", {})
                c_curve = cap_curves_by_model.get(model_key, ([], [], []))
                r_curve = risk_curves_by_model.get(model_key, ([], [], []))
                c_xs, c_iso, c_raw = c_curve
                r_xs, r_iso, r_raw = r_curve
                for row in rows:
                    # --- PROSPECTIVE: routing decision from difficulty score alone ---
                    score = float(difficulty_scores_by_model.get(model_key, {}).get(str(row["sample_id"]), 0.5))
                    row_features = _extract_feature_vector(row)
                    query_family = task_dir.name
                    predicted_route_state = _route_state(
                        score,
                        limit_difficulty,
                        delta,
                        d_safe=d_safe,
                        d_unsafe=d_unsafe,
                    )
                    # Evaluate continuous curves at this score.
                    e_cap  = _evaluate_curve(c_xs, c_iso, score) if c_xs else 0.5
                    e_risk = _evaluate_curve(r_xs, r_iso, score) if r_xs else 0.5
                    # Local Wilson CI at this score using k nearest training points.
                    _, e_cap_lower  = _local_beta_at(
                        score, c_xs, c_raw, min_samples, router.wilson_confidence_level, upper=False
                    )
                    _, e_risk_upper = _local_beta_at(
                        score, r_xs, r_raw, min_samples, router.wilson_confidence_level, upper=True
                    )
                    if limit_difficulty is None:
                        uncertainty = 1.0
                        confidence = 0.0
                    else:
                        uncertainty = abs(score - float(limit_difficulty))
                        confidence = _calibrated_confidence_from_margin(uncertainty, margin_calibrator)

                    # --- RETROSPECTIVE: actual outcome after model has run ---
                    actual_capability, actual_semantic_risk, failure_type = _evaluate_row(row, reference_lookup)
                    if predicted_route_state == "BASELINE":
                        routing_correct: bool | None = None
                    else:
                        routing_correct = actual_capability >= router.capability_threshold

                    # HYBRID_ABSTAIN operational policy:
                    # Queries in the uncertainty band [d_safe, d_unsafe] are routed
                    # to BASELINE by default (same as BASELINE state) but flagged with
                    # route_confidence_level="uncertain" for downstream handling
                    # (e.g., human review, ensemble, reranking).
                    # "high"      → score ≤ d_safe    → SLM certified safe
                    # "uncertain" → d_safe < score < d_unsafe → HYBRID_ABSTAIN → BASELINE + flag
                    # "none"      → score ≥ d_unsafe or no cert → BASELINE
                    if d_safe is not None and score <= float(d_safe):
                        route_confidence_level = "high"
                    elif d_safe is not None and d_unsafe is not None and score < float(d_unsafe):
                        route_confidence_level = "uncertain"
                    else:
                        route_confidence_level = "none"
                    abstain_fallback = (
                        "BASELINE"
                        if predicted_route_state in ("BASELINE", "HYBRID_ABSTAIN")
                        else "SLM"
                    )

                    payload = {
                        "example_id": row["sample_id"],
                        "task": row["task"],
                        "model_name": DISPLAY_NAMES[model_key],
                        "model_family": "LLM" if model_key.startswith("llama_") else "SLM",
                        "difficulty_score": round(score, 4),
                        "query_family": query_family,
                        "difficulty_features": {k: round(float(v), 6) for k, v in row_features.items()},
                        # prospective fields
                        "predicted_route_state": predicted_route_state,
                        "route_confidence_level": route_confidence_level,
                        "abstain_fallback": abstain_fallback,
                        "expected_capability": round(e_cap, 4),
                        "expected_capability_lower_ci": round(e_cap_lower, 4),
                        "expected_risk": round(e_risk, 4),
                        "expected_risk_upper_ci": round(e_risk_upper, 4),
                        "routing_uncertainty": round(uncertainty, 4),
                        "routing_confidence": round(confidence, 4),
                        # retrospective fields
                        "actual_capability": actual_capability,
                        "actual_semantic_risk": actual_semantic_risk,
                        "failure_type": failure_type,
                        "routing_correct": routing_correct,
                        # raw output
                        "valid_output": 1 if row.get("valid", False) else 0,
                        "latency_sec": float(row.get("latency_sec", 0.0) or 0.0),
                        "prediction": row.get("raw_output", ""),
                        "input_text": row.get("prompt", ""),
                        "reference": _resolve_reference(row, reference_lookup),
                        # legacy aliases
                        "primary_metric": actual_capability,
                        "semantic_risk": actual_semantic_risk,
                        "route_state": predicted_route_state,
                    }
                    handle.write(json.dumps(payload) + "\n")

        summary = {
            "task": task_dir.name,
            "wilson_confidence_level": router.wilson_confidence_level,
            "wilson_z": router.wilson_z,
            "policy_capability_threshold": router.capability_threshold,
            "policy_risk_threshold": router.risk_threshold,
            "min_samples": min_samples,
            "min_ground_truth_coverage": min_ground_truth_coverage,
            "threshold_method": "continuous_isotonic_knn_beta",
            "report_split": report_split,
            "weights_source_split": weights_source_split,
            "query_family_model": "task_as_family",
            "abstain_max_delta": float(args.abstain_max_delta),
            "abstain_grid_step": float(args.abstain_grid_step),
            "tau_bootstrap_draws": int(max(50, int(args.tau_bootstrap_draws))),
            "tau_conservative_percentile": float(args.tau_conservative_percentile),
            "task_utility_coefficients": {
                "alpha": task_utility_alpha,
                "beta": task_utility_beta,
                "gamma": task_utility_gamma,
            },
            "ground_truth_coverage_by_model": ground_truth_coverage_by_model,
            "difficulty_score_source": "learned_task_family_weighted_features",
            "matched_query_count": len(baseline_ids),
            "baseline_query_count": len(baseline_ids),
            "common_query_count_across_all_models": len(all_model_common_ids),
            "models_used": [DISPLAY_NAMES[key] for key in task_rows],
            "model_matched_query_counts": {
                DISPLAY_NAMES[key]: len(per_model_common_ids[key]) for key in task_rows
            },
            "thresholds": thresholds,
            "decision_matrix": decision_metrics,
        }
        _write_json(sddf_dir / "thresholds.json", summary)
        _write_json(sddf_dir / "routing_policy.json", summary)
        task_summaries[task_dir.name] = summary

    _write_json(BENCHMARK_ROOT / "sddf_summary.json", task_summaries)
    print(f"Generated SDDF curves and thresholds for {len(task_summaries)} tasks.")


if __name__ == "__main__":
    main()

