from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import math
import hashlib
import sys
from statistics import NormalDist
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    "tinyllama_1.1b",
    "qwen2.5_1.5b",
    "phi3_mini",
    "llama_llama-3.3-70b-versatile",
]
BASELINE_MODEL = "llama_llama-3.3-70b-versatile"
DISPLAY_NAMES = {
    "tinyllama_1.1b": "tinyllama:1.1b",
    "qwen2.5_1.5b": "qwen2.5:1.5b",
    "phi3_mini": "phi3:mini",
    "llama_llama-3.3-70b-versatile": "groq:llama-3.3-70b-versatile",
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

TASK_FAMILY_MAP = {
    "classification": "classification",
    "maths": "reasoning",
    "code_generation": "code",
    "summarization": "summarization",
    "information_extraction": "extraction",
    "retrieval_grounded": "retrieval",
    "instruction_following": "instruction",
    "text_generation": "generation",
}

DEFAULT_WILSON_CONFIDENCE_LEVEL = 0.90
DEFAULT_WILSON_Z = 1.6448536269514722
DEFAULT_CAPABILITY_THRESHOLD = 0.80
DEFAULT_RISK_THRESHOLD = 0.20
DEFAULT_MIN_SAMPLES = 5
DEFAULT_MIN_GROUND_TRUTH_COVERAGE = 0.95


def _z_from_confidence(level: float) -> float:
    bounded = max(0.50, min(0.999, float(level)))
    return NormalDist().inv_cdf(0.5 + bounded / 2.0)


def _wilson_interval(p: float, n: int, z: float = DEFAULT_WILSON_Z) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = max(0.0, min(1.0, float(p)))
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))
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

    def difficulty_to_bin_probabilities(self, difficulty_score: float, num_bins: int = 5) -> dict[int, float]:
        score = max(0.0, min(1.0, float(difficulty_score)))
        position = score * max(1, num_bins - 1)
        lower = int(position)
        upper = min(lower + 1, num_bins - 1)
        frac = position - lower
        probs = {idx: 0.0 for idx in range(num_bins)}
        probs[lower] = 1.0 - frac
        if upper != lower:
            probs[upper] = frac
        return probs

    def compute_expected_capability(
        self,
        difficulty_score: float,
        capability_curve: dict[int, float],
        num_bins: int = 5,
    ) -> float:
        probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)
        return sum(prob * float(capability_curve.get(bin_id, 0.5)) for bin_id, prob in probs.items())

    def compute_expected_risk(
        self,
        difficulty_score: float,
        risk_curve: dict[int, float],
        num_bins: int = 5,
    ) -> float:
        probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)
        return sum(prob * float(risk_curve.get(bin_id, 0.5)) for bin_id, prob in probs.items())

    def detect_tipping_points(
        self,
        capability_curve: dict[int, float],
        risk_curve: dict[int, float],
        num_bins: int = 5,
        capability_counts: dict[int, int] | None = None,
        risk_counts: dict[int, int] | None = None,
        min_samples: int = 5,
    ) -> tuple[int | None, int | None]:
        # Primary thresholding is level+CI (research-safe), not momentum.
        tau_cap: int | None = None
        tau_risk: int | None = None  # None means no risk breach observed.
        risk_breach_bin: int | None = None

        # Walk bins in order; tau_cap only advances while consecutive bins pass.
        # Once a sufficiently-populated bin fails Wilson CI, we stop â€" later bins
        # passing cannot extend the safe region because the routing rule is
        # "route SLM for difficulty <= tau_cap", which would include the failed bin.
        for d in range(num_bins):
            n = int((capability_counts or {}).get(d, 0))
            if n < min_samples:
                break  # sparse bin: cannot certify this range; stop consecutive run
            lower, _ = _wilson_interval(float(capability_curve.get(d, 0.0)), n, z=self.wilson_z)
            if lower is not None and lower >= self.capability_threshold:
                tau_cap = d
            else:
                break  # first failing bin ends the consecutive safe run

        # Conservative risk certification: breach if Wilson upper bound exceeds threshold.
        for d in range(num_bins):
            n = int((risk_counts or {}).get(d, 0))
            if n < min_samples:
                continue
            _lower, upper = _wilson_interval(float(risk_curve.get(d, 0.0)), n, z=self.wilson_z)
            if upper is not None and upper > self.risk_threshold:
                risk_breach_bin = d
                break

        if risk_breach_bin is None:
            tau_risk = None
        elif risk_breach_bin == 0:
            # Immediate breach: no safe SLM region.
            tau_risk = -1
        else:
            tau_risk = risk_breach_bin - 1

        return tau_cap, tau_risk
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


def _build_reference_lookup(task: str, rows: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
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

    # No fallback to prompt-template labels for paper-grade evaluation.
    _ = rows
    return refs


def _resolve_reference(task: str, row: dict[str, Any], reference_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _ = task
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
    reference = _resolve_reference(task, row, reference_lookup)
    output = row.get("raw_output", "")
    parsed = row.get("parsed_output") or {}
    if not reference:
        return 0.0, 1.0, "missing_ground_truth"
    if not output.strip():
        failure = row.get("failure_category") or "empty_output"
        return 0.0, 1.0, failure
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
    # Risk is independent of capability: it measures HOW the model fails, not IF.
    # High-risk = assertive wrong answer the user may not notice and act on.
    # Low-risk  = silent failure (empty, refusal, truncation) — user knows to escalate.
    # A model with high capability can still have high risk if its failure mode is
    # confidently wrong rather than safely abstaining.
    HIGH_RISK_FAILURES = {
        "arithmetic_error",     # wrong number presented as correct
        "wrong_label",          # wrong class stated confidently
        "logic_error",          # plausible but incorrect code
        "answer_mismatch",      # wrong factual answer
        "low_relevance",        # off-topic response presented as answer
        "constraint_violation", # constraint broken without flagging it
    }
    LOW_RISK_FAILURES = {
        "empty_output",
        "incomplete_output",
        "missing_ground_truth",
        "missing_field",
        "no_answer",
        "format_error",
        "quality_failure",
        "timeout_runtime",   # execution timed out — silent, not a wrong answer
    }
    if failure is None:
        semantic_risk = 0.0   # no failure
    elif failure in HIGH_RISK_FAILURES:
        semantic_risk = 1.0   # dangerous failure
    else:
        semantic_risk = 0.0   # safe/silent failure — not a deployment risk
    return capability, semantic_risk, failure


def _curve_for_rows(rows: list[dict[str, Any]], reference_lookup: dict[str, dict[str, Any]]) -> tuple[dict[int, float], dict[int, float], dict[int, int], dict[str, dict[int, int]], dict[str, dict[str, int]]]:
    per_bin_capability: dict[int, list[float]] = defaultdict(list)
    per_bin_risk: dict[int, list[float]] = defaultdict(list)
    per_bin_failures: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        bin_id = int(row["bin"])
        capability, risk, failure = _evaluate_row(row, reference_lookup)
        per_bin_capability[bin_id].append(capability)
        per_bin_risk[bin_id].append(risk)
        if failure:
            per_bin_failures[bin_id][failure] += 1

    capability: dict[int, float] = {}
    risk: dict[int, float] = {}
    counts: dict[int, int] = {}
    failure_counts: dict[str, dict[int, int]] = defaultdict(dict)
    for bin_id in sorted(per_bin_capability):
        vals = per_bin_capability[bin_id]
        risks = per_bin_risk[bin_id]
        counts[bin_id] = len(vals)
        capability[bin_id] = sum(vals) / len(vals) if vals else 0.0
        risk[bin_id] = sum(risks) / len(risks) if risks else 0.0
        for failure_type, count in per_bin_failures[bin_id].items():
            failure_counts[failure_type][bin_id] = count
    return capability, risk, counts, dict(failure_counts), {str(k): dict(v) for k, v in per_bin_failures.items()}


def _plot_task_curve_panels(
    smooth_curves: dict[str, dict[float, float]],
    empirical_curves: dict[str, dict[int, float]],
    counts_by_model: dict[str, dict[int, int]] | None,
    title: str,
    ylabel: str,
    output_path: Path,
    threshold_line: float | None = None,
    threshold_label: str | None = None,
    tau_difficulty: dict[str, float | None] | None = None,
    wilson_z: float = DEFAULT_WILSON_Z,
) -> None:
    models = [m for m in CANONICAL_MODELS if m in smooth_curves or m in empirical_curves]
    if not models:
        return
    n = len(models)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(12, 4.2 * rows), squeeze=False)
    axes_flat = [ax for row_axes in axes for ax in row_axes]

    for idx, model_key in enumerate(models):
        ax = axes_flat[idx]
        smooth = smooth_curves.get(model_key, {})
        empirical = empirical_curves.get(model_key, {})
        counts = {} if not counts_by_model else counts_by_model.get(model_key, {})

        if smooth:
            xs = sorted(float(x) for x in smooth.keys())
            ys = [float(smooth[x]) if x in smooth else float(smooth.get(f"{x:.3f}", 0.0)) for x in xs]
            ax.plot(xs, ys, linewidth=2.0, color="tab:blue", label="smoothed")
        if empirical:
            bins = sorted(int(b) for b in empirical.keys())
            denom = max(1, max(bins))
            ex = [b / denom for b in bins]
            ey = [float(empirical[b]) for b in bins]
            ax.scatter(ex, ey, color="tab:orange", s=35, label="empirical bins", zorder=4)
            lo_err = []
            hi_err = []
            for b, y in zip(bins, ey):
                n = int(counts.get(b, 0))
                lo, hi = _wilson_interval(y, n, z=wilson_z)
                if lo is None or hi is None:
                    lo_err.append(0.0)
                    hi_err.append(0.0)
                else:
                    lo_err.append(max(0.0, y - lo))
                    hi_err.append(max(0.0, hi - y))
            if any((a > 0.0 or b > 0.0) for a, b in zip(lo_err, hi_err)):
                ax.errorbar(
                    ex,
                    ey,
                    yerr=[lo_err, hi_err],
                    fmt="none",
                    ecolor="tab:orange",
                    elinewidth=1.1,
                    capsize=3,
                    alpha=0.8,
                    zorder=3,
                    label="Wilson CI",
                )

        if threshold_line is not None:
            ax.axhline(threshold_line, color="black", linestyle="--", linewidth=1.0, label=threshold_label or "threshold")

        tau = None if not tau_difficulty else tau_difficulty.get(model_key)
        if tau is not None:
            ax.axvline(float(tau), color="crimson", linestyle="--", linewidth=1.2, label=f"tau={tau:.2f}")

        ax.set_xlim(0.0, 1.0)
        ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.grid(True, alpha=0.25)
        ax.set_title(DISPLAY_NAMES.get(model_key, model_key), fontsize=10)
        ax.set_xlabel("Difficulty score")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8, loc="best")

    for ax in axes_flat[n:]:
        ax.axis("off")

    fig.suptitle(title, fontsize=13)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    fig.savefig(output_path, dpi=170)
    plt.close(fig)


def _avg_curve(curve: dict[int, float], counts: dict[int, int] | None = None) -> float:
    if not curve:
        return 0.0
    if counts:
        total = sum(counts.get(b, 0) for b in curve)
        if total > 0:
            return sum(float(v) * counts.get(b, 0) for b, v in curve.items()) / total
    return sum(curve.values()) / len(curve)


def _isotonic_decreasing(curve: dict[int, float], counts: dict[int, int]) -> dict[int, float]:
    """Pool Adjacent Violators — enforce monotone decreasing capability curve.

    Capability should decrease as bin index (difficulty) increases.
    Adjacent bins that violate this are merged into a weighted average.
    The raw empirical values are preserved separately for the scatter plot;
    this function only produces the isotonic-regularised version used for
    the smooth line and reported metrics.
    """
    bins = sorted(curve.keys())
    if len(bins) <= 1:
        return dict(curve)
    vals = [float(curve[b]) for b in bins]
    wts = [max(1, int(counts.get(b, 1))) for b in bins]
    # Stack of [pooled_value, pooled_weight, [original_bins]]
    pool: list[list] = []
    for v, w, b in zip(vals, wts, bins):
        pool.append([v, w, [b]])
        # Merge while last entry is GREATER than second-to-last (violates decreasing).
        while len(pool) >= 2 and pool[-1][0] > pool[-2][0]:
            last = pool.pop()
            prev = pool.pop()
            merged_w = prev[1] + last[1]
            merged_v = (prev[0] * prev[1] + last[0] * last[1]) / merged_w
            pool.append([merged_v, merged_w, prev[2] + last[2]])
    result: dict[int, float] = {}
    for pooled_v, _, pooled_bins in pool:
        for b in pooled_bins:
            result[b] = pooled_v
    return result


def _isotonic_increasing(curve: dict[int, float], counts: dict[int, int]) -> dict[int, float]:
    """Pool Adjacent Violators — enforce monotone increasing risk curve."""
    bins = sorted(curve.keys())
    if len(bins) <= 1:
        return dict(curve)
    vals = [float(curve[b]) for b in bins]
    wts = [max(1, int(counts.get(b, 1))) for b in bins]
    pool: list[list] = []
    for v, w, b in zip(vals, wts, bins):
        pool.append([v, w, [b]])
        # Merge while last entry is LESS than second-to-last (violates increasing).
        while len(pool) >= 2 and pool[-1][0] < pool[-2][0]:
            last = pool.pop()
            prev = pool.pop()
            merged_w = prev[1] + last[1]
            merged_v = (prev[0] * prev[1] + last[0] * last[1]) / merged_w
            pool.append([merged_v, merged_w, prev[2] + last[2]])
    result: dict[int, float] = {}
    for pooled_v, _, pooled_bins in pool:
        for b in pooled_bins:
            result[b] = pooled_v
    return result


def _build_routing_policy(
    tau_cap: int | None,
    tau_risk: int | None,
    counts: dict[int, int],
    num_bins: int,
    min_samples: int,
) -> dict[str, Any]:
    risk_gate_pass = tau_risk != -1
    capability_gate_pass = tau_cap is not None

    if tau_cap is None or tau_risk == -1:
        return {
            "risk_gate_pass": risk_gate_pass,
            "capability_gate_pass": capability_gate_pass,
            "limit_bin": None,
            "limit_difficulty": None,
            "sparse_bins": [bin_id for bin_id, count in sorted(counts.items()) if count < min_samples],
            "route_rule": "Route all queries to BASELINE; SLM fails level+CI safety gate.",
        }

    limit_bin = tau_cap if tau_risk is None else min(tau_cap, tau_risk)
    return {
        "risk_gate_pass": risk_gate_pass,
        "capability_gate_pass": capability_gate_pass,
        "limit_bin": limit_bin,
        "limit_difficulty": limit_bin / max(1, (num_bins - 1)),
        "sparse_bins": [bin_id for bin_id, count in sorted(counts.items()) if count < min_samples],
        "route_rule": (
            f"Route to SLM when difficulty_bin <= {limit_bin}; otherwise route to BASELINE."
        ),
    }


def _plot_decision_matrix_tau(
    metrics: dict[str, dict[str, Any]],
    title: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(8, 6))
    risk_threshold = 0.2  # matches router.risk_threshold
    y_divider = 1.0 - risk_threshold  # 0.8

    plt.axvline(0.5, color="darkgreen", linestyle="--", linewidth=1.3, alpha=0.7)
    plt.axhline(y_divider, color="darkred", linestyle="--", linewidth=1.3, alpha=0.7)
    plt.xlim(-0.02, 1.02)
    plt.ylim(-0.02, 1.02)
    plt.xlabel("Certified capability reach (tau_cap_difficulty)")
    plt.ylabel("Risk safety (1 \u2212 avg_expected_risk)")
    plt.title(title)
    plt.grid(True, alpha=0.3)

    # Label positions: centred inside each quadrant region
    # x divider at 0.5, y divider at 0.8
    quadrant_labels = [
        (0.75, 0.90, "Broad SLM Safe"),
        (0.75, 0.40, "Capable but risk-limited"),
        (0.25, 0.90, "Narrow SLM Safe"),
        (0.25, 0.40, "Baseline-first"),
    ]
    for x, y, label in quadrant_labels:
        plt.text(x, y, label, fontsize=10, alpha=0.7, ha="center", va="center")

    for model_key, record in metrics.items():
        x = float(record.get("tau_cap_difficulty") or 0.0)
        y = 1.0 - float(record.get("avg_expected_risk") or 0.0)
        color = "tab:green" if record["confidence_certified_routing_policy"].get("limit_bin") is not None else "tab:orange"
        marker = "o"
        plt.scatter([x], [y], s=140, color=color, marker=marker, edgecolor="black", linewidth=0.8)
        plt.annotate(
            f"{DISPLAY_NAMES[model_key]} | limit={record['confidence_certified_routing_policy'].get('limit_bin')}",
            (x, y),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=9,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _expected_curve(
    router: GeneralizedRoutingFramework,
    capability: dict[int, float],
    risk: dict[int, float],
    observed_bins: list[int],
) -> tuple[dict[int, float], dict[int, float]]:
    expected_capability: dict[int, float] = {}
    expected_risk: dict[int, float] = {}
    if not observed_bins:
        return expected_capability, expected_risk
    num_bins = max(observed_bins) + 1
    for d in observed_bins:
        difficulty_mid = d / max(1, (num_bins - 1))
        expected_capability[d] = router.compute_expected_capability(difficulty_mid, capability, num_bins)
        expected_risk[d] = router.compute_expected_risk(difficulty_mid, risk, num_bins)
    return expected_capability, expected_risk


def _moving_average(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    w = max(1, int(window))
    if w == 1:
        return list(values)
    radius = w // 2
    out: list[float] = []
    for idx in range(len(values)):
        lo = max(0, idx - radius)
        hi = min(len(values), idx + radius + 1)
        chunk = values[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def _expected_curve_smooth(
    router: GeneralizedRoutingFramework,
    capability: dict[int, float],
    risk: dict[int, float],
    num_bins: int,
    grid_points: int = 41,
    smooth_window: int = 5,
) -> tuple[dict[float, float], dict[float, float]]:
    if num_bins <= 0:
        return {}, {}
    points = max(5, int(grid_points))
    xs = [idx / (points - 1) for idx in range(points)]
    cap_vals = [router.compute_expected_capability(x, capability, num_bins) for x in xs]
    risk_vals = [router.compute_expected_risk(x, risk, num_bins) for x in xs]
    cap_smoothed = _moving_average(cap_vals, smooth_window)
    risk_smoothed = _moving_average(risk_vals, smooth_window)
    return (
        {float(x): float(y) for x, y in zip(xs, cap_smoothed)},
        {float(x): float(y) for x, y in zip(xs, risk_smoothed)},
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _task_family(task: str) -> str:
    return TASK_FAMILY_MAP.get(task, "general")


def _stable_split_for_sample(sample_id: str) -> str:
    digest = hashlib.sha1(str(sample_id).encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
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


def _learn_family_difficulty_models(
    task_to_rows: dict[str, dict[str, list[dict[str, Any]]]],
    reference_lookup_by_task: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    pooled: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task, model_rows in task_to_rows.items():
        family = _task_family(task)
        refs = reference_lookup_by_task.get(task, {})
        for model_key, rows in model_rows.items():
            if model_key == BASELINE_MODEL:
                continue
            for row in rows:
                if _split_name_for_row(row) != "train":
                    continue
                _cap, semantic_risk, _failure = _evaluate_row(row, refs)
                features = _extract_feature_vector(row)
                features["target"] = float(semantic_risk)
                pooled[family].append(features)

    learned: dict[str, dict[str, Any]] = {}
    for family, samples in pooled.items():
        learner = DifficultyWeightLearner()
        learned[family] = learner.fit(samples)
    return learned


def _score_with_family_model(
    row: dict[str, Any],
    family_model: dict[str, Any] | None,
) -> float:
    if not family_model:
        return 0.0
    weights = family_model.get("weights", {})
    norm_stats = family_model.get("norm_stats", {})
    features = _extract_feature_vector(row)
    score = 0.0
    for dim in DIFFICULTY_FEATURES:
        val = float(features.get(dim, 0.0))
        bounds = norm_stats.get(dim, {"min": 0.0, "max": 1.0})
        lo = float(bounds.get("min", 0.0))
        hi = float(bounds.get("max", 1.0))
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


def _calibrated_confidence_from_margin(margin: float, calibrator: dict[str, Any]) -> float:
    buckets = calibrator.get("buckets") or []
    if not buckets:
        return max(0.0, 1.0 - float(calibrator.get("global_failure_rate", 1.0)))
    m = float(margin)
    for bucket in buckets:
        if m <= float(bucket.get("max_margin", 0.0)):
            return max(0.0, 1.0 - float(bucket.get("failure_rate", 1.0)))
    return max(0.0, 1.0 - float(buckets[-1].get("failure_rate", 1.0)))


def _route_state(score: float, limit: float | None, delta: float) -> str:
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
    parser.add_argument("--min-ground-truth-coverage", type=float, default=DEFAULT_MIN_GROUND_TRUTH_COVERAGE)
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
        "--learn-family-weights",
        action="store_true",
        help="Learn task-family-specific difficulty weights from train split semantic failures.",
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


def main() -> None:
    args = _parse_args()
    min_samples = max(1, int(args.min_samples))
    ci_level = max(0.50, min(0.999, float(args.ci_level)))
    wilson_z = _z_from_confidence(ci_level)
    min_ground_truth_coverage = max(0.0, min(1.0, float(args.min_ground_truth_coverage)))
    difficulty_weights = _load_difficulty_weights(args.difficulty_weights)
    report_split, weights_source_split = _validate_split_contract(
        difficulty_weights,
        args.weights_source_split,
        args.report_split,
    )
    router = GeneralizedRoutingFramework(
        capability_threshold=float(args.cap_threshold),
        risk_threshold=float(args.risk_threshold),
        wilson_z=wilson_z,
        wilson_confidence_level=ci_level,
    )
    task_summaries: dict[str, Any] = {}

    # First pass: collect task/model rows and references once.
    task_available_rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
    reference_lookup_by_task: dict[str, dict[str, dict[str, Any]]] = {}
    task_dirs = sorted(p for p in BENCHMARK_ROOT.iterdir() if p.is_dir() and p.name in SUPPORTED_TASKS)
    for task_dir in task_dirs:
        available = {}
        for model_key in CANONICAL_MODELS:
            outputs_path = task_dir / model_key / "outputs.jsonl"
            if outputs_path.exists():
                available[model_key] = _dedupe_rows(_load_jsonl(outputs_path))
        if len(available) < 2 or BASELINE_MODEL not in available:
            continue
        task_available_rows[task_dir.name] = available
        all_rows_for_task = [row for rows in available.values() for row in rows]
        reference_lookup_by_task[task_dir.name] = _build_reference_lookup(task_dir.name, rows=all_rows_for_task)

    # Difficulty scoring mode:
    # 1) explicit provided scalar weights, or
    # 2) learned task-family weights from train split.
    family_weight_models: dict[str, dict[str, Any]] = {}
    if args.learn_family_weights:
        family_weight_models = _learn_family_difficulty_models(task_available_rows, reference_lookup_by_task)
        weights_out = BENCHMARK_ROOT / "difficulty_weights" / "family_weights_learned.json"
        _write_json(
            weights_out,
            {
                "source_split": "train",
                "families": family_weight_models,
                "features": list(DIFFICULTY_FEATURES),
            },
        )

    for task_dir in task_dirs:
        if task_dir.name not in task_available_rows:
            continue
        available = task_available_rows[task_dir.name]
        reference_lookup = reference_lookup_by_task.get(task_dir.name, {})

        baseline_ids = {str(row["sample_id"]) for row in available[BASELINE_MODEL]}
        all_model_common_ids = baseline_ids.copy()
        per_model_common_ids: dict[str, set[str]] = {}
        for model_key, rows in available.items():
            model_ids = {str(row["sample_id"]) for row in rows}
            per_model_common_ids[model_key] = model_ids & baseline_ids
            all_model_common_ids &= model_ids

        task_rows: dict[str, list[dict[str, Any]]] = {}
        capability_curves_level: dict[str, dict[int, float]] = {}
        risk_curves_level: dict[str, dict[int, float]] = {}
        capability_counts_by_model: dict[str, dict[int, int]] = {}
        risk_counts_by_model: dict[str, dict[int, int]] = {}
        expected_capability_curves_level: dict[str, dict[int, float]] = {}
        expected_risk_curves_level: dict[str, dict[int, float]] = {}
        expected_capability_curves_smooth: dict[str, dict[float, float]] = {}
        expected_risk_curves_smooth: dict[str, dict[float, float]] = {}
        thresholds: dict[str, Any] = {}
        decision_metrics: dict[str, dict[str, Any]] = {}
        difficulty_scores_by_model: dict[str, dict[str, float]] = {}
        num_bins_by_model: dict[str, int] = {}
        tau_cap_by_model: dict[str, int | None] = {}
        tau_risk_by_model: dict[str, int | None] = {}
        tau_cap_difficulty_by_model: dict[str, float | None] = {}
        tau_risk_difficulty_by_model: dict[str, float | None] = {}
        ground_truth_coverage_by_model: dict[str, dict[str, float]] = {}

        task_family = _task_family(task_dir.name)
        family_model = family_weight_models.get(task_family) if args.learn_family_weights else None
        num_difficulty_bins = 5


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
            report_rows_raw = [row for row in filtered_all if _split_name_for_row(row) == report_split]
            if not report_rows_raw:
                report_rows_raw = list(filtered_all)
            val_rows_raw = [row for row in filtered_all if _split_name_for_row(row) == "val"]
            train_rows_raw = [row for row in filtered_all if _split_name_for_row(row) == "train"]
            calib_rows_raw = train_rows_raw + val_rows_raw if (train_rows_raw or val_rows_raw) else list(report_rows_raw)

            # Difficulty score for unseen-task routing.
            if family_model:
                difficulty_scores_by_model[model_key] = {
                    str(row["sample_id"]): _score_with_family_model(row, family_model) for row in filtered_all
                }
                difficulty_source = "learned_family_weighted_features"
                weights_used = family_model.get("weights", {})
            elif difficulty_weights:
                difficulty_scores_by_model[model_key] = _weighted_difficulty_scores(filtered_all, difficulty_weights)
                difficulty_source = "weighted_features"
                weights_used = difficulty_weights
            else:
                raw_max_bin = max([0] + [int(row.get("bin", 0) or 0) for row in filtered_all])
                denom = max(1, raw_max_bin)
                difficulty_scores_by_model[model_key] = {
                    str(row["sample_id"]): int(row["bin"]) / denom for row in filtered_all
                }
                difficulty_source = "normalized_difficulty_bin"
                weights_used = {}

            # Leakage-safe binning from the same difficulty score used for runtime routing:
            # fit bins on calibration split scores (train+val), apply to report split.
            calib_ids = [
                str(row["sample_id"])
                for row in calib_rows_raw
                if str(row["sample_id"]) in difficulty_scores_by_model[model_key]
            ]
            calib_ids_sorted = sorted(
                calib_ids,
                key=lambda sid: (float(difficulty_scores_by_model[model_key].get(sid, 0.5)), sid),
            )
            n_calib = len(calib_ids_sorted)
            calib_bin_by_id: dict[str, int] = (
                {
                    sid: min(num_difficulty_bins - 1, int(rank * num_difficulty_bins / n_calib))
                    for rank, sid in enumerate(calib_ids_sorted)
                }
                if n_calib >= num_difficulty_bins
                else {sid: 0 for sid in calib_ids_sorted}
            )
            calib_scores_sorted = [float(difficulty_scores_by_model[model_key].get(sid, 0.5)) for sid in calib_ids_sorted]

            def _score_to_bin(score: float) -> int:
                rank = bisect.bisect_left(calib_scores_sorted, float(score))
                return min(num_difficulty_bins - 1, int(rank * num_difficulty_bins / max(1, n_calib)))

            def _assign_bins(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
                projected: list[dict[str, Any]] = []
                for raw in raw_rows:
                    row = dict(raw)
                    sid = str(row["sample_id"])
                    score = float(difficulty_scores_by_model[model_key].get(sid, 0.5))
                    row["bin"] = calib_bin_by_id.get(sid, _score_to_bin(score))
                    projected.append(row)
                projected.sort(key=lambda r: (int(r["bin"]), str(r["sample_id"])))
                return projected

            report_rows = _assign_bins(report_rows_raw)
            calib_rows = _assign_bins(calib_rows_raw)

            observed_bins = sorted({int(row["bin"]) for row in report_rows})
            observed_bins_cal = sorted({int(row["bin"]) for row in calib_rows})
            max_bin = max([0] + observed_bins + observed_bins_cal)
            num_bins = max_bin + 1
            num_bins_by_model[model_key] = num_bins

            task_rows[model_key] = report_rows
            gt_matched = sum(1 for row in report_rows if _resolve_reference(task_dir.name, row, reference_lookup))
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

            capability_raw, risk_raw, counts, failure_counts, failures_by_bin = _curve_for_rows(report_rows, reference_lookup)
            # Apply isotonic regression to enforce monotone curves.
            # capability must decrease with difficulty; risk must increase.
            # Raw empirical values are kept for the scatter-plot dots;
            # isotonic values are used for the smooth line and reported metrics.
            capability = _isotonic_decreasing(capability_raw, counts)
            risk = _isotonic_increasing(risk_raw, counts)
            expected_capability, expected_risk = _expected_curve(router, capability, risk, observed_bins)
            capability_curves_level[model_key] = capability_raw   # scatter dots: raw
            risk_curves_level[model_key] = risk_raw               # scatter dots: raw
            capability_counts_by_model[model_key] = dict(counts)
            risk_counts_by_model[model_key] = dict(counts)
            expected_capability_curves_level[model_key] = expected_capability
            expected_risk_curves_level[model_key] = expected_risk
            smooth_cap, smooth_risk = _expected_curve_smooth(
                router, capability, risk, num_bins=num_bins, grid_points=41, smooth_window=5
            )
            expected_capability_curves_smooth[model_key] = smooth_cap
            expected_risk_curves_smooth[model_key] = smooth_risk

            # Calibrate thresholds on validation split (fallback to report split when val absent).
            capability_cal_raw, risk_cal_raw, counts_cal, _fc_cal, _fb_cal = _curve_for_rows(calib_rows, reference_lookup)
            calib_has_support = any(int(n) >= min_samples for n in counts_cal.values())
            if not calib_has_support:
                capability_cal_raw, risk_cal_raw, counts_cal = capability_raw, risk_raw, counts
            capability_cal = _isotonic_decreasing(capability_cal_raw, counts_cal)
            risk_cal = _isotonic_increasing(risk_cal_raw, counts_cal)
            tau_cap, tau_risk = router.detect_tipping_points(
                capability_cal,
                risk_cal,
                num_bins=num_bins,
                capability_counts=counts_cal,
                risk_counts=counts_cal,
                min_samples=min_samples,
            )

            tau_cap_by_model[model_key] = tau_cap
            tau_risk_by_model[model_key] = tau_risk
            tau_cap_difficulty_by_model[model_key] = None if tau_cap is None else (tau_cap / max(1, (num_bins - 1)))
            if tau_risk is None or tau_risk < 0:
                tau_risk_difficulty_by_model[model_key] = None
            else:
                tau_risk_difficulty_by_model[model_key] = tau_risk / max(1, (num_bins - 1))

            confidence_routing_policy = _build_routing_policy(
                tau_cap,
                tau_risk,
                counts_cal,
                num_bins=num_bins,
                min_samples=min_samples,
            )
            limit_difficulty = confidence_routing_policy.get("limit_difficulty")
            abstention = _calibrate_abstention_delta(
                calib_rows,
                reference_lookup,
                difficulty_scores_by_model[model_key],
                limit_difficulty,
                router.risk_threshold,
                router.capability_threshold,
                max_delta=float(args.abstain_max_delta),
                grid_step=float(args.abstain_grid_step),
            )
            confidence_routing_policy["abstention_band_half_width"] = float(abstention["delta"])
            confidence_routing_policy["route_rule_with_abstention"] = (
                "SLM if score <= limit-delta; HYBRID_ABSTAIN if limit-delta < score < limit+delta; "
                "BASELINE otherwise."
                if limit_difficulty is not None
                else "Route all queries to BASELINE; no certified SLM region."
            )
            margin_calibrator = _build_margin_calibrator(
                calib_rows,
                reference_lookup,
                difficulty_scores_by_model[model_key],
                limit_difficulty,
            )
            confidence_routing_policy["margin_confidence_calibration"] = margin_calibrator

            thresholds[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "matched_query_count": len(report_rows),
                "calibration_row_count": len(calib_rows),
                "wilson_confidence_level": router.wilson_confidence_level,
                "tau_cap_bin": tau_cap,
                "tau_cap_difficulty": tau_cap_difficulty_by_model[model_key],
                "tau_risk_bin": tau_risk,
                "tau_risk_difficulty": tau_risk_difficulty_by_model[model_key],
                "capability_curve": capability,          # isotonic-regularised
                "capability_curve_raw": capability_raw,  # raw empirical
                "risk_curve": risk,                      # isotonic-regularised
                "risk_curve_raw": risk_raw,              # raw empirical
                "expected_capability_curve": expected_capability,
                "expected_risk_curve": expected_risk,
                "expected_capability_curve_smooth": {f"{k:.3f}": v for k, v in smooth_cap.items()},
                "expected_risk_curve_smooth": {f"{k:.3f}": v for k, v in smooth_risk.items()},
                "counts_by_bin": counts,
                "semantic_failure_counts": failure_counts,
                "semantic_failures_by_bin": failures_by_bin,
                "difficulty_score_source": difficulty_source,
                "difficulty_weights_used": weights_used,
                "difficulty_family": task_family,
                "report_split": report_split,
                "calibration_split": ("train+val" if (train_rows_raw or val_rows_raw) else report_split),
                "calibration_fallback_to_report": bool(not calib_has_support),
                "weights_source_split": weights_source_split,
                "threshold_method": "level_ci_tau",
                "abstention_calibration": abstention,
                "margin_confidence_calibration": margin_calibrator,
                **ground_truth_coverage_by_model[model_key],
            }

            avg_expected_capability = _avg_curve(expected_capability, counts)
            avg_expected_risk = _avg_curve(expected_risk, counts)
            decision_metrics[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "avg_expected_capability": avg_expected_capability,
                "avg_expected_risk": avg_expected_risk,
                "tau_cap_bin": tau_cap,
                "tau_risk_bin": tau_risk,
                "tau_cap_difficulty": tau_cap_difficulty_by_model[model_key],
                "tau_risk_difficulty": tau_risk_difficulty_by_model[model_key],
                "risk_safety_score": (
                    0.0
                    if tau_risk == -1
                    else (1.0 if tau_risk is None else (1.0 - float(tau_risk_difficulty_by_model[model_key] or 0.0)))
                ),
                "tau_quadrant": (
                    # X-axis: certified capability reach (tau_cap_difficulty >= 0.5 = "broad").
                    # Y-axis: avg_expected_risk <= risk_threshold = "safe".
                    # Uses same axes as the decision-matrix plot so the label matches the
                    # dot's visual quadrant.
                    # limit_bin=None means no bin certified -> always Baseline-first.
                    "Baseline-first"                if confidence_routing_policy["limit_bin"] is None
                    else "Broad SLM Safe"           if float(tau_cap_difficulty_by_model[model_key] or 0.0) >= 0.5 and avg_expected_risk <= router.risk_threshold
                    else "Capable but risk-limited" if float(tau_cap_difficulty_by_model[model_key] or 0.0) >= 0.5
                    else "Narrow SLM Safe"          if avg_expected_risk <= router.risk_threshold
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
                margin_calibrator = policy.get("margin_confidence_calibration", {})
                for row in rows:
                    capability, semantic_risk, failure_type = _evaluate_row(row, reference_lookup)
                    score = float(
                        difficulty_scores_by_model.get(model_key, {}).get(
                            str(row["sample_id"]),
                            int(row["bin"]) / max(1, (num_bins_by_model.get(model_key, 5) - 1)),
                        )
                    )
                    route_state = _route_state(score, limit_difficulty, delta)
                    if limit_difficulty is None:
                        uncertainty = 1.0
                        confidence = 0.0
                    else:
                        uncertainty = abs(score - float(limit_difficulty))
                        confidence = _calibrated_confidence_from_margin(uncertainty, margin_calibrator)
                    payload = {
                        "example_id": row["sample_id"],
                        "task": row["task"],
                        "model_name": DISPLAY_NAMES[model_key],
                        "model_family": "LLM" if model_key.startswith("llama_") else "SLM",
                        "difficulty_bin": int(row["bin"]),
                        "difficulty_score": score,
                        "primary_metric": capability,
                        "valid_output": 1 if row.get("valid", False) else 0,
                        "latency_sec": float(row.get("latency_sec", 0.0) or 0.0),
                        "prediction": row.get("raw_output", ""),
                        "failure_type": failure_type,
                        "semantic_risk": semantic_risk,
                        "route_state": route_state,
                        "routing_uncertainty": uncertainty,
                        "routing_confidence": confidence,
                        "input_text": row.get("prompt", ""),
                        "reference": _resolve_reference(row["task"], row, reference_lookup),
                    }
                    handle.write(json.dumps(payload) + "\n")

        _plot_task_curve_panels(
            expected_capability_curves_smooth,
            capability_curves_level,
            capability_counts_by_model,
            f"{task_dir.name} Capability (smoothed + empirical)",
            "Capability",
            sddf_dir / "capability_curve.png",
            threshold_line=router.capability_threshold,
            threshold_label=f"cap threshold ({router.capability_threshold:.2f})",
            tau_difficulty=tau_cap_difficulty_by_model,
            wilson_z=router.wilson_z,
        )
        _plot_task_curve_panels(
            expected_risk_curves_smooth,
            risk_curves_level,
            risk_counts_by_model,
            f"{task_dir.name} Risk (smoothed + empirical)",
            "Risk",
            sddf_dir / "risk_curve.png",
            threshold_line=router.risk_threshold,
            threshold_label=f"risk threshold ({router.risk_threshold:.2f})",
            tau_difficulty=tau_risk_difficulty_by_model,
            wilson_z=router.wilson_z,
        )
        _plot_decision_matrix_tau(
            decision_metrics,
            f"{task_dir.name} Tau-Based Decision Matrix",
            sddf_dir / "decision_matrix.png",
        )

        summary = {
            "task": task_dir.name,
            "wilson_confidence_level": router.wilson_confidence_level,
            "wilson_z": router.wilson_z,
            "policy_capability_threshold": router.capability_threshold,
            "policy_risk_threshold": router.risk_threshold,
            "min_samples_per_bin": min_samples,
            "min_ground_truth_coverage": min_ground_truth_coverage,
            "threshold_method": "level_ci_tau",
            "report_split": report_split,
            "weights_source_split": weights_source_split,
            "learn_family_weights": bool(args.learn_family_weights),
            "task_family": task_family,
            "abstain_max_delta": float(args.abstain_max_delta),
            "abstain_grid_step": float(args.abstain_grid_step),
            "ground_truth_coverage_by_model": ground_truth_coverage_by_model,
            "difficulty_score_source": (
                "learned_family_weighted_features"
                if args.learn_family_weights
                else ("weighted_features" if difficulty_weights else "normalized_difficulty_bin")
            ),
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

