from __future__ import annotations

import json
import re
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.routing.framework import GeneralizedRoutingFramework


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "model_runs" / "benchmark_75"
CANONICAL_MODELS = [
    "tinyllama_1.1b",
    "qwen2.5_1.5b",
    "phi3_mini",
    "llama_llama-3.3-70b-versatile",
]
DISPLAY_NAMES = {
    "tinyllama_1.1b": "tinyllama:1.1b",
    "qwen2.5_1.5b": "qwen2.5:1.5b",
    "phi3_mini": "phi3:mini",
    "llama_llama-3.3-70b-versatile": "groq:llama-3.3-70b-versatile",
}
TASK_DIRS = {
    "classification": ROOT / "tasks" / "classification",
    "maths": ROOT / "tasks" / "maths",
    "information_extraction": ROOT / "tasks" / "Information Extraction",
    "instruction_following": ROOT / "tasks" / "instruction_following",
    "retrieval_grounded": ROOT / "tasks" / "Retrieval_grounded",
    "summarization": ROOT / "tasks" / "Summarization",
    "code_generation": ROOT / "tasks" / "code_generation",
    "text_generation": ROOT / "tasks" / "text_generation",
}
REFERENCE_BANK = {
    "classification": {
        "Classify sentiment: 'This movie was amazing!'": {"label": "positive"},
        "Classify sentiment: 'Terrible experience, never again'": {"label": "negative"},
        "Classify sentiment: 'It was okay, nothing special'": {"label": "neutral"},
        "Categorize text: Political or Sports?": {"choices": ["political", "sports"]},
        "Is this email spam or not spam?": {"choices": ["spam", "not spam"]},
    },
    "maths": {
        "Solve: 2x + 5 = 13": {"answer": 4.0},
        "Calculate: (12 + 8) * 3 - 5": {"answer": 55.0},
        "What is the square root of 144?": {"answer": 12.0},
        "Solve: 3x^2 + 2x - 1 = 0": {"answers_text": ["1/3", "-1"]},
        "Calculate: (5! + 3!) / 4": {"answer": 31.5},
    },
    "information_extraction": {
        "Extract person name: 'John Smith works at Microsoft'": {"contains": ["john smith"]},
        "Extract location: 'The meeting is in New York'": {"contains": ["new york"]},
        "Extract date: 'Event scheduled for March 15, 2025'": {"contains": ["march 15, 2025"]},
        "Extract organization: 'Alice is CEO of TechCorp'": {"contains": ["techcorp"]},
        "Extract all entities: 'Bob visited Paris in 2023'": {"contains": ["bob", "paris", "2023"]},
    },
    "instruction_following": {
        "Count to 5 starting from 1": {"sequence": ["1", "2", "3", "4", "5"]},
        "List 3 colors in alphabetical order": {"ordered_contains": ["blue", "green", "red"]},
        "Translate 'hello' to Spanish": {"contains": ["hola"]},
        "Write the alphabet backwards": {"contains": ["zyx"]},
        "List months of the year in order": {"ordered_contains": ["january", "february", "march", "april"]},
    },
    "retrieval_grounded": {
        "Based on context, answer: What year was X invented?": {"requires_context_ack": True},
        "Using the provided text, who is the main character?": {"requires_context_ack": True},
        "From the document, what is the capital of France?": {"contains": ["paris"]},
        "According to the passage, what happened first?": {"requires_context_ack": True},
        "From the context, what is the definition of X?": {"requires_context_ack": True},
    },
    "summarization": {
        "Summarize: The quick brown fox jumps over the lazy dog. The dog was sleeping peacefully.": {"contains": ["fox", "dog"]},
        "Summarize article about climate change in 2-3 sentences": {"contains": ["climate"]},
        "Summarize the key points of quantum mechanics": {"contains": ["quantum"]},
        "Give a brief summary of the Industrial Revolution": {"contains": ["industrial", "revolution"]},
        "Summarize COVID-19 pandemic timeline": {"contains": ["covid", "pandemic"]},
    },
    "code_generation": {
        "Write a function to reverse a string": {"kind": "reverse_string"},
        "Implement bubble sort algorithm": {"kind": "bubble_sort"},
        "Create a function to calculate factorial": {"kind": "factorial"},
        "Write code to parse JSON": {"kind": "parse_json"},
        "Implement binary search": {"kind": "binary_search"},
    },
    "text_generation": {
        "Explain quantum computing in simple terms": {"contains": ["quantum"]},
        "What are the benefits of renewable energy?": {"contains": ["renewable", "energy"]},
        "Describe the process of photosynthesis": {"contains": ["photosynthesis"]},
        "Write a short story about a robot": {"contains": ["robot"]},
        "Explain what machine learning is": {"contains": ["machine learning"]},
    },
}


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
        by_sample.setdefault(sample_id, row)
    return list(by_sample.values())


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _strip_example(prompt: str) -> str:
    return re.sub(r"\s*\(Example \d+\)\s*$", "", (prompt or "").strip())


def _build_reference_lookup(task: str) -> dict[str, dict[str, Any]]:
    rebin_path = TASK_DIRS[task] / "rebin_results.csv"
    refs: dict[str, dict[str, Any]] = {}
    if not rebin_path.exists():
        return refs
    with rebin_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sample_id = str(row["example_id"])
            prompt = _strip_example(str(row["input_text"]))
            reference = REFERENCE_BANK.get(task, {}).get(prompt, {}).copy()
            if reference:
                reference["prompt"] = prompt
                reference["source_sample_id"] = row.get("sample_id")
                refs[sample_id] = reference
    return refs


def _resolve_reference(task: str, row: dict[str, Any], reference_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sample_id = str(row["sample_id"])
    reference = reference_lookup.get(sample_id)
    if reference:
        return reference
    prompt = _strip_example(str(row.get("prompt", "")))
    fallback = REFERENCE_BANK.get(task, {}).get(prompt, {}).copy()
    if fallback:
        fallback["prompt"] = prompt
    return fallback


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
        ok = any(token in text for token in expected)
        return float(ok), None if ok else "low_relevance"
    return 1.0 if text else 0.0, None if text else "empty_output"


def _code_eval(reference: dict[str, Any], output: str, parsed: dict[str, Any]) -> tuple[float, str | None]:
    text = _norm(output)
    blocks = parsed.get("code_blocks") or []
    has_code = bool(blocks)
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
    return float(has_code), None if has_code else "format_error"


def _textgen_eval(reference: dict[str, Any], output: str, row: dict[str, Any]) -> tuple[float, str | None]:
    text = _norm(output)
    if row.get("status") == "invalid" and row.get("error"):
        return 0.0, "incomplete_output"
    expected = reference.get("contains", [])
    if expected:
        ok = _contains_all(text, expected)
        return float(ok), None if ok else "low_relevance"
    return 1.0 if text else 0.0, None if text else "empty_output"


def _evaluate_row(row: dict[str, Any], reference_lookup: dict[str, dict[str, Any]]) -> tuple[float, float, str | None]:
    task = row["task"]
    sample_id = str(row["sample_id"])
    reference = _resolve_reference(task, row, reference_lookup)
    output = row.get("raw_output", "")
    parsed = row.get("parsed_output") or {}
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
    semantic_failure = 0.0 if capability >= 1.0 and not failure else 1.0
    return capability, semantic_failure, failure


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


def _plot_curve(curves: dict[str, dict[int, float]], title: str, ylabel: str, output_path: Path) -> None:
    plt.figure(figsize=(8, 5))
    all_xs: set[int] = set()
    for model_key, curve in curves.items():
        xs = sorted(curve)
        all_xs.update(xs)
        ys = [curve[x] for x in xs]
        plt.plot(xs, ys, marker="o", linewidth=2, label=DISPLAY_NAMES[model_key])
    plt.xticks(sorted(all_xs) if all_xs else [0, 1, 2, 3, 4])
    plt.ylim(0, 1.05)
    plt.xlabel("Difficulty Bin")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _avg_curve(curve: dict[int, float]) -> float:
    if not curve:
        return 0.0
    return sum(curve.values()) / len(curve)


def _assign_quadrant(capability: float, risk: float, capability_threshold: float, risk_threshold: float) -> str:
    if capability >= capability_threshold and risk <= risk_threshold:
        return "Q1: high capability, low risk"
    if capability >= capability_threshold and risk > risk_threshold:
        return "Q2: high capability, high risk"
    if capability < capability_threshold and risk <= risk_threshold:
        return "Q3: low capability, low risk"
    return "Q4: low capability, high risk"


def _build_empirical_policy(
    capability_curve: dict[int, float],
    risk_curve: dict[int, float],
    counts: dict[int, int],
    capability_threshold: float,
    risk_threshold: float,
    min_samples: int,
) -> dict[str, Any]:
    eligible_bins = [
        bin_id
        for bin_id in sorted(capability_curve)
        if counts.get(bin_id, 0) >= min_samples
        and capability_curve.get(bin_id, 0.0) >= capability_threshold
        and risk_curve.get(bin_id, 1.0) <= risk_threshold
    ]
    if not eligible_bins:
        return {
            "limit_bin": None,
            "limit_difficulty": None,
            "sparse_bins": [bin_id for bin_id, count in sorted(counts.items()) if count < min_samples],
            "route_rule": "Empirical evidence does not show a deployable SLM region; route to BASELINE.",
        }
    limit_bin = max(eligible_bins)
    max_observed_bin = max(capability_curve) if capability_curve else 0
    return {
        "limit_bin": limit_bin,
        "limit_difficulty": limit_bin / max(1, max_observed_bin),
        "sparse_bins": [bin_id for bin_id, count in sorted(counts.items()) if count < min_samples],
        "route_rule": f"Empirically route to SLM when difficulty_bin <= {limit_bin}; otherwise route to BASELINE.",
    }


def _build_routing_policy(
    tau_cap: int | None,
    tau_risk: int | None,
    counts: dict[int, int],
    num_bins: int,
    min_samples: int,
) -> dict[str, Any]:
    risk_gate_pass = tau_risk is None
    capability_gate_pass = tau_cap is not None

    if tau_cap is None:
        return {
            "risk_gate_pass": risk_gate_pass,
            "capability_gate_pass": False,
            "limit_bin": None,
            "limit_difficulty": None,
            "sparse_bins": [bin_id for bin_id, count in sorted(counts.items()) if count < min_samples],
            "route_rule": "Route all queries to BASELINE; SLM never clears the capability gate with Wilson confidence.",
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


def _plot_decision_matrix(
    metrics: dict[str, dict[str, Any]],
    title: str,
    capability_threshold: float,
    risk_threshold: float,
    output_path: Path,
) -> None:
    plt.figure(figsize=(8, 6))
    plt.axvline(capability_threshold, color="darkgreen", linestyle="--", linewidth=1.5)
    plt.axhline(risk_threshold, color="darkred", linestyle="--", linewidth=1.5)
    plt.xlim(0, 1.02)
    plt.ylim(0, 1.02)
    plt.xlabel("Expected Capability")
    plt.ylabel("Expected Risk")
    plt.title(title)
    plt.grid(True, alpha=0.3)

    quadrant_labels = [
        (0.97, 0.04, "Q1"),
        (0.97, 0.96, "Q2"),
        (0.20, 0.04, "Q3"),
        (0.20, 0.96, "Q4"),
    ]
    for x, y, label in quadrant_labels:
        plt.text(x, y, label, fontsize=10, alpha=0.7, ha="center", va="center")

    for model_key, record in metrics.items():
        x = record["avg_expected_capability"]
        y = record["avg_expected_risk"]
        color = "tab:green" if record["confidence_certified_routing_policy"]["capability_gate_pass"] else "tab:orange"
        marker = "o" if record["confidence_certified_routing_policy"]["risk_gate_pass"] else "X"
        plt.scatter([x], [y], s=140, color=color, marker=marker, edgecolor="black", linewidth=0.8)
        plt.annotate(
            f"{DISPLAY_NAMES[model_key]} | {record['confidence_quadrant']}",
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    router = GeneralizedRoutingFramework(capability_threshold=0.80, risk_threshold=0.20)
    task_summaries: dict[str, Any] = {}

    for task_dir in sorted(p for p in BENCHMARK_ROOT.iterdir() if p.is_dir()):
        reference_lookup = _build_reference_lookup(task_dir.name)
        available = {}
        for model_key in CANONICAL_MODELS:
            outputs_path = task_dir / model_key / "outputs.jsonl"
            if outputs_path.exists():
                available[model_key] = _dedupe_rows(_load_jsonl(outputs_path))

        if len(available) < 2:
            continue

        common_ids = None
        for model_key, rows in available.items():
            ids = {str(row["sample_id"]) for row in rows}
            common_ids = ids if common_ids is None else common_ids & ids
        common_ids = common_ids or set()
        observed_bins = sorted(
            {
                int(row["bin"])
                for rows in available.values()
                for row in rows
                if str(row["sample_id"]) in common_ids
            }
        )
        num_bins = (max(observed_bins) + 1) if observed_bins else 5

        task_rows: dict[str, list[dict[str, Any]]] = {}
        capability_curves: dict[str, dict[int, float]] = {}
        risk_curves: dict[str, dict[int, float]] = {}
        expected_capability_curves: dict[str, dict[int, float]] = {}
        expected_risk_curves: dict[str, dict[int, float]] = {}
        thresholds: dict[str, Any] = {}
        decision_metrics: dict[str, dict[str, Any]] = {}

        for model_key, rows in available.items():
            filtered = [row for row in rows if str(row["sample_id"]) in common_ids]
            filtered.sort(key=lambda row: (int(row["bin"]), str(row["sample_id"])))
            task_rows[model_key] = filtered
            capability, risk, counts, failure_counts, failures_by_bin = _curve_for_rows(filtered, reference_lookup)
            expected_capability, expected_risk = _expected_curve(router, capability, risk, observed_bins)
            capability_curves[model_key] = capability
            risk_curves[model_key] = risk
            expected_capability_curves[model_key] = expected_capability
            expected_risk_curves[model_key] = expected_risk
            tau_cap, tau_risk = router.detect_tipping_points(
                capability,
                risk,
                num_bins=num_bins,
                capability_counts=counts,
                risk_counts=counts,
                min_samples=5,
            )
            thresholds[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "matched_query_count": len(filtered),
                "tau_cap_bin": tau_cap,
                "tau_cap_difficulty": None if tau_cap is None else tau_cap / 4.0,
                "tau_risk_bin": tau_risk,
                "tau_risk_difficulty": None if tau_risk is None else tau_risk / 4.0,
                "capability_curve": capability,
                "risk_curve": risk,
                "expected_capability_curve": expected_capability,
                "expected_risk_curve": expected_risk,
                "counts_by_bin": counts,
                "semantic_failure_counts": failure_counts,
                "semantic_failures_by_bin": failures_by_bin,
            }
            avg_expected_capability = _avg_curve(expected_capability)
            avg_expected_risk = _avg_curve(expected_risk)
            confidence_routing_policy = _build_routing_policy(
                tau_cap,
                tau_risk,
                counts,
                num_bins=num_bins,
                min_samples=5,
            )
            empirical_routing_policy = _build_empirical_policy(
                capability,
                risk,
                counts,
                router.capability_threshold,
                router.risk_threshold,
                min_samples=5,
            )
            decision_metrics[model_key] = {
                "display_name": DISPLAY_NAMES[model_key],
                "avg_expected_capability": avg_expected_capability,
                "avg_expected_risk": avg_expected_risk,
                "empirical_quadrant": _assign_quadrant(
                    _avg_curve(capability),
                    _avg_curve(risk),
                    router.capability_threshold,
                    router.risk_threshold,
                ),
                "confidence_quadrant": _assign_quadrant(
                    avg_expected_capability,
                    avg_expected_risk,
                    router.capability_threshold,
                    router.risk_threshold,
                ),
                "empirical_routing_policy": empirical_routing_policy,
                "confidence_certified_routing_policy": confidence_routing_policy,
            }

        sddf_dir = task_dir / "sddf"
        sddf_dir.mkdir(parents=True, exist_ok=True)
        canonical_rows_path = sddf_dir / "canonical_rows.jsonl"
        with canonical_rows_path.open("w", encoding="utf-8") as handle:
            for model_key, rows in task_rows.items():
                for row in rows:
                    capability, semantic_risk, failure_type = _evaluate_row(row, reference_lookup)
                    payload = {
                        "example_id": row["sample_id"],
                        "task": row["task"],
                        "model_name": DISPLAY_NAMES[model_key],
                        "model_family": "LLM" if model_key.startswith("llama_") else "SLM",
                        "difficulty_bin": int(row["bin"]),
                        "difficulty_score": int(row["bin"]) / 4.0,
                        "primary_metric": capability,
                        "valid_output": 1 if row.get("valid", False) else 0,
                        "latency_sec": float(row.get("latency_sec", 0.0) or 0.0),
                        "prediction": row.get("raw_output", ""),
                        "failure_type": failure_type,
                        "semantic_risk": semantic_risk,
                        "input_text": row.get("prompt", ""),
                        "reference": _resolve_reference(row["task"], row, reference_lookup),
                    }
                    handle.write(json.dumps(payload) + "\n")

        _plot_curve(
            expected_capability_curves,
            f"{task_dir.name} Capability Curve",
            "Expected Capability",
            sddf_dir / "capability_curve.png",
        )
        _plot_curve(
            expected_risk_curves,
            f"{task_dir.name} Risk Curve",
            "Expected Risk",
            sddf_dir / "risk_curve.png",
        )
        _plot_curve(
            capability_curves,
            f"{task_dir.name} Empirical Per-Bin Capability",
            "P(task_correct | bin)",
            sddf_dir / "empirical_capability_curve.png",
        )
        _plot_curve(
            risk_curves,
            f"{task_dir.name} Empirical Per-Bin Risk",
            "P(semantic_failure | bin)",
            sddf_dir / "empirical_risk_curve.png",
        )
        _plot_decision_matrix(
            decision_metrics,
            f"{task_dir.name} Capability-Risk Decision Matrix",
            router.capability_threshold,
            router.risk_threshold,
            sddf_dir / "decision_matrix.png",
        )

        summary = {
            "task": task_dir.name,
            "matched_query_count": len(common_ids),
            "models_used": [DISPLAY_NAMES[key] for key in task_rows],
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
