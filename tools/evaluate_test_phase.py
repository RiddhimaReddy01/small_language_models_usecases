from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS = ROOT / "model_runs"
BENCHMARKING_OUT = MODEL_RUNS / "benchmarking" / "phase_reports"
HASH_POLICY = "sha1(sample_id)%100: train<30, val<70, test>=70"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _calc_prf(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    acc = (tp + tn) / max(1, len(y_true))
    return {
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": acc,
    }


def _ece_binary(pred: list[float], obs: list[float], bins: int = 5) -> float:
    if not pred:
        return 0.0
    p = np.asarray(pred, dtype=float)
    y = np.asarray(obs, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(p)
    ece = 0.0
    for i in range(bins):
        left = edges[i]
        right = edges[i + 1]
        if i == bins - 1:
            mask = (p >= left) & (p <= right)
        else:
            mask = (p >= left) & (p < right)
        n = int(mask.sum())
        if n == 0:
            continue
        conf = float(p[mask].mean())
        freq = float(y[mask].mean())
        ece += abs(conf - freq) * (n / total)
    return float(ece)


def _brier(pred: list[float], obs: list[float]) -> float:
    if not pred:
        return 0.0
    p = np.asarray(pred, dtype=float)
    y = np.asarray(obs, dtype=float)
    return float(np.mean((p - y) ** 2))


def _bootstrap_ci(
    samples: list[dict[str, float]],
    metric_fn,
    draws: int = 400,
    alpha: float = 0.10,
) -> tuple[float, float]:
    if not samples:
        return 0.0, 0.0
    rng = np.random.default_rng(42)
    n = len(samples)
    vals = []
    for _ in range(max(100, int(draws))):
        idx = rng.integers(0, n, size=n)
        boot = [samples[int(i)] for i in idx]
        vals.append(float(metric_fn(boot)))
    lo = float(np.quantile(vals, alpha / 2.0))
    hi = float(np.quantile(vals, 1.0 - alpha / 2.0))
    return lo, hi


def _mcnemar_pvalue(y_true: list[int], pred_a: list[int], pred_b: list[int]) -> dict[str, float]:
    """McNemar test (continuity-corrected chi-square approximation)."""
    b = 0  # A wrong, B right
    c = 0  # A right, B wrong
    for t, a, bpred in zip(y_true, pred_a, pred_b):
        a_ok = int(a == t)
        b_ok = int(bpred == t)
        if a_ok == 0 and b_ok == 1:
            b += 1
        elif a_ok == 1 and b_ok == 0:
            c += 1
    if (b + c) == 0:
        return {"b": 0.0, "c": 0.0, "chi2": 0.0, "p_value": 1.0}
    chi2 = ((abs(b - c) - 1.0) ** 2) / float(b + c)
    # Survival fn for chi-square(df=1): erfc(sqrt(x/2))
    p = math.erfc(math.sqrt(max(0.0, chi2) / 2.0))
    return {"b": float(b), "c": float(c), "chi2": float(chi2), "p_value": float(p)}


def _evaluate_rows(
    rows: list[dict[str, Any]],
    cap_threshold: float,
    risk_threshold: float,
    utility_alpha: float,
    utility_beta: float,
    utility_gamma: float,
) -> dict[str, Any]:
    eval_rows: list[dict[str, float]] = []
    for row in rows:
        route = str(row.get("predicted_route_state") or row.get("route_state") or "").strip().upper()
        act_cap = _safe_float(row.get("actual_capability"), 0.0)
        act_risk = _safe_float(row.get("actual_semantic_risk"), 1.0)
        exp_cap = _safe_float(row.get("expected_capability"), 0.5)
        exp_risk = _safe_float(row.get("expected_risk"), 0.5)
        # safe_true = did the SLM actually succeed on this query?
        # Using raw capability (binary 0/1 from the task evaluator) rather than
        # the cap_threshold+risk_threshold gate — that gate was used to select τ*,
        # so gating evaluation with it makes the metric tautological.
        safe_true = act_cap  # 0.0 (failure) or 1.0 (success)
        safe_pred = 1.0 if route == "SLM" else 0.0
        eval_rows.append(
            {
                "safe_true": safe_true,
                "safe_pred": safe_pred,
                "actual_capability": act_cap,
                "actual_risk": act_risk,
                "expected_capability": exp_cap,
                "expected_risk": exp_risk,
                "is_slm": 1.0 if route == "SLM" else 0.0,
                "is_hybrid": 1.0 if route == "HYBRID_ABSTAIN" else 0.0,
            }
        )
    if not eval_rows:
        return {}

    y_true = [int(r["safe_true"]) for r in eval_rows]
    y_pred = [int(r["safe_pred"]) for r in eval_rows]
    prf = _calc_prf(y_true, y_pred)
    pred_always_slm = [1 for _ in y_true]
    pred_always_baseline = [0 for _ in y_true]
    prf_always_slm = _calc_prf(y_true, pred_always_slm)
    prf_always_baseline = _calc_prf(y_true, pred_always_baseline)

    slm_rows = [r for r in eval_rows if r["is_slm"] > 0.5]
    assisted_rows = [r for r in eval_rows if (r["is_slm"] > 0.5 or r["is_hybrid"] > 0.5)]
    n = float(len(eval_rows))
    coverage = len(slm_rows) / n
    assisted_coverage = len(assisted_rows) / n
    selected_cap = float(np.mean([r["actual_capability"] for r in slm_rows])) if slm_rows else 0.0
    selected_risk = float(np.mean([r["actual_risk"] for r in slm_rows])) if slm_rows else 1.0
    utility = utility_alpha * coverage + utility_beta * selected_cap - utility_gamma * selected_risk
    always_slm_cap = float(np.mean([r["actual_capability"] for r in eval_rows])) if eval_rows else 0.0
    always_slm_risk = float(np.mean([r["actual_risk"] for r in eval_rows])) if eval_rows else 1.0
    always_slm_utility = utility_alpha * 1.0 + utility_beta * always_slm_cap - utility_gamma * always_slm_risk
    always_baseline_utility = utility_alpha * 0.0 + utility_beta * 0.0 - utility_gamma * 1.0

    exp_cap = [r["expected_capability"] for r in eval_rows]
    obs_cap = [r["actual_capability"] for r in eval_rows]
    exp_risk = [r["expected_risk"] for r in eval_rows]
    obs_risk = [r["actual_risk"] for r in eval_rows]
    cap_ece = _ece_binary(exp_cap, obs_cap, bins=5)
    cap_brier = _brier(exp_cap, obs_cap)
    risk_ece = _ece_binary(exp_risk, obs_risk, bins=5)
    risk_brier = _brier(exp_risk, obs_risk)

    # Bootstrap uncertainty for the operational metrics.
    def _metric_precision(boot: list[dict[str, float]]) -> float:
        return _calc_prf(
            [int(x["safe_true"]) for x in boot],
            [int(x["safe_pred"]) for x in boot],
        )["precision"]

    def _metric_recall(boot: list[dict[str, float]]) -> float:
        return _calc_prf(
            [int(x["safe_true"]) for x in boot],
            [int(x["safe_pred"]) for x in boot],
        )["recall"]

    def _metric_f1(boot: list[dict[str, float]]) -> float:
        return _calc_prf(
            [int(x["safe_true"]) for x in boot],
            [int(x["safe_pred"]) for x in boot],
        )["f1"]

    def _metric_cov(boot: list[dict[str, float]]) -> float:
        return float(sum(x["is_slm"] for x in boot) / max(1, len(boot)))

    def _metric_acc(boot: list[dict[str, float]]) -> float:
        yt = [int(x["safe_true"]) for x in boot]
        yp = [int(x["safe_pred"]) for x in boot]
        return _calc_prf(yt, yp)["accuracy"]

    def _metric_selected_cap(boot: list[dict[str, float]]) -> float:
        picked = [x["actual_capability"] for x in boot if x["is_slm"] > 0.5]
        return float(np.mean(picked)) if picked else 0.0

    def _metric_risk(boot: list[dict[str, float]]) -> float:
        picked = [x["actual_risk"] for x in boot if x["is_slm"] > 0.5]
        return float(np.mean(picked)) if picked else 1.0

    def _metric_utility(boot: list[dict[str, float]]) -> float:
        cov = float(sum(x["is_slm"] for x in boot) / max(1, len(boot)))
        cap = _metric_selected_cap(boot)
        risk = _metric_risk(boot)
        return float(utility_alpha * cov + utility_beta * cap - utility_gamma * risk)

    samples = list(eval_rows)
    p_lo, p_hi = _bootstrap_ci(samples, _metric_precision)
    r_lo, r_hi = _bootstrap_ci(samples, _metric_recall)
    f_lo, f_hi = _bootstrap_ci(samples, _metric_f1)
    c_lo, c_hi = _bootstrap_ci(samples, _metric_cov)
    a_lo, a_hi = _bootstrap_ci(samples, _metric_acc)
    sc_lo, sc_hi = _bootstrap_ci(samples, _metric_selected_cap)
    sr_lo, sr_hi = _bootstrap_ci(samples, _metric_risk)
    u_lo, u_hi = _bootstrap_ci(samples, _metric_utility)

    return {
        "n_rows": int(len(eval_rows)),
        "routing_quality": prf,
        "baseline_quality": {
            "always_slm": prf_always_slm,
            "always_baseline": prf_always_baseline,
        },
        "significance": {
            "policy_vs_always_slm_mcnemar": _mcnemar_pvalue(y_true, y_pred, pred_always_slm),
            "policy_vs_always_baseline_mcnemar": _mcnemar_pvalue(y_true, y_pred, pred_always_baseline),
        },
        "coverage_slm": float(coverage),
        "coverage_slm_or_hybrid": float(assisted_coverage),
        "selected_capability": float(selected_cap),
        "selected_risk": float(selected_risk),
        "utility": float(utility),
        "baseline_utility": {
            "always_slm": float(always_slm_utility),
            "always_baseline": float(always_baseline_utility),
        },
        "calibration": {
            "capability_ece": float(cap_ece),
            "capability_brier": float(cap_brier),
            "risk_ece": float(risk_ece),
            "risk_brier": float(risk_brier),
        },
        "bootstrap_ci_90": {
            "precision": [float(p_lo), float(p_hi)],
            "recall": [float(r_lo), float(r_hi)],
            "f1": [float(f_lo), float(f_hi)],
            "accuracy": [float(a_lo), float(a_hi)],
            "coverage_slm": [float(c_lo), float(c_hi)],
            "selected_capability": [float(sc_lo), float(sc_hi)],
            "selected_risk": [float(sr_lo), float(sr_hi)],
            "utility": [float(u_lo), float(u_hi)],
        },
    }


def _holm_correct(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down correction. Returns adjusted p-values (same order)."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        corrected = p_values[idx] * (m - rank)
        running_max = max(running_max, corrected)
        adjusted[idx] = min(1.0, running_max)
    return adjusted


def _apply_holm_correction(rows: list[dict[str, Any]]) -> None:
    """Collect all McNemar p-values across rows, apply Holm correction in-place."""
    keys = [
        ("significance", "policy_vs_always_slm_mcnemar", "p_value"),
        ("significance", "policy_vs_always_baseline_mcnemar", "p_value"),
    ]
    # Extract raw p-values per comparison family.
    for outer_key, inner_key, p_key in keys:
        raw: list[float] = []
        locations: list[tuple[int, str, str, str]] = []
        for i, row in enumerate(rows):
            sig = row.get(outer_key, {})
            test = sig.get(inner_key, {}) if isinstance(sig, dict) else {}
            if isinstance(test, dict) and p_key in test:
                raw.append(float(test[p_key]))
                locations.append((i, outer_key, inner_key, p_key))
        if not raw:
            continue
        adjusted = _holm_correct(raw)
        for (i, ok, ik, pk), adj_p in zip(locations, adjusted):
            rows[i][ok][ik]["p_value_holm_adjusted"] = float(adj_p)


def _collect_task_model_rows(task_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    threshold_path = task_dir / "sddf" / "thresholds.json"
    canonical_path = task_dir / "sddf" / "canonical_rows.jsonl"
    payload = json.loads(threshold_path.read_text(encoding="utf-8"))
    rows = _load_jsonl(canonical_path)
    return payload, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate frozen SDDF policy on canonical rows for the current report split.")
    parser.add_argument("--utility-alpha", type=float, default=1.0)
    parser.add_argument("--utility-beta", type=float, default=0.25)
    parser.add_argument("--utility-gamma", type=float, default=1.0)
    parser.add_argument(
        "--output-stem",
        type=str,
        default="test_phase_report",
        help="Output filename stem under model_runs/benchmarking (e.g., val_phase_report or test_phase_report).",
    )
    parser.add_argument(
        "--strict-leakage",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail when frozen-policy leakage guards are violated (default: true).",
    )
    args = parser.parse_args()

    out_rows: list[dict[str, Any]] = []
    by_task_model: dict[str, Any] = {}

    for task_dir in sorted(p for p in MODEL_RUNS.iterdir() if p.is_dir()):
        threshold_path = task_dir / "sddf" / "thresholds.json"
        canonical_path = task_dir / "sddf" / "canonical_rows.jsonl"
        if not threshold_path.exists() or not canonical_path.exists():
            continue
        payload, canonical_rows = _collect_task_model_rows(task_dir)
        task = str(payload.get("task") or task_dir.name)
        cap_threshold = _safe_float(payload.get("policy_capability_threshold"), 0.8)
        risk_threshold = _safe_float(payload.get("policy_risk_threshold"), 0.2)
        report_split = str(payload.get("report_split") or "")

        task_entry = {
            "task": task,
            "report_split": report_split,
            "threshold_method": payload.get("threshold_method"),
            "models": {},
        }

        for model_key, model_payload in (payload.get("thresholds") or {}).items():
            display_name = str(model_payload.get("display_name") or model_key)
            model_rows = [r for r in canonical_rows if str(r.get("model_name") or "") == display_name]
            metrics = _evaluate_rows(
                model_rows,
                cap_threshold=cap_threshold,
                risk_threshold=risk_threshold,
                utility_alpha=float(args.utility_alpha),
                utility_beta=float(args.utility_beta),
                utility_gamma=float(args.utility_gamma),
            )
            if not metrics:
                continue
            threshold_split = str(model_payload.get("threshold_split") or "")
            tau_star = model_payload.get("tau_star_difficulty")
            train_curve_row_count = _safe_int(model_payload.get("train_curve_row_count"), 0)
            val_threshold_row_count = _safe_int(model_payload.get("val_threshold_row_count"), 0)
            matched_query_count = _safe_int(model_payload.get("matched_query_count"), len(model_rows))
            split_contract_ok = bool(train_curve_row_count > 0 and matched_query_count > 0)
            frozen_policy_check = bool(threshold_split == "val")
            leakage_violations: list[str] = []
            if report_split in {"test", "evaluation", "eval"} and not frozen_policy_check:
                leakage_violations.append("threshold_split_must_be_val_for_test")
            if report_split in {"test", "val"} and val_threshold_row_count <= 0:
                leakage_violations.append("missing_val_threshold_rows")
            if train_curve_row_count <= 0:
                leakage_violations.append("missing_train_curve_rows")
            if matched_query_count <= 0:
                leakage_violations.append("missing_report_rows")
            if args.strict_leakage and leakage_violations:
                raise RuntimeError(
                    f"Leakage guard failed for task={task}, model={display_name}: "
                    + ", ".join(leakage_violations)
                )
            pass_gate = bool(
                metrics["selected_risk"] <= risk_threshold
                and metrics["selected_capability"] >= cap_threshold
            )
            item = {
                "task": task,
                "model_key": model_key,
                "display_name": display_name,
                "report_split": report_split,
                "threshold_split": threshold_split,
                "tau_star_difficulty": tau_star,
                "hash_split_policy": HASH_POLICY,
                "train_curve_row_count": train_curve_row_count,
                "val_threshold_row_count": val_threshold_row_count,
                "report_row_count": matched_query_count,
                "split_contract_ok": split_contract_ok,
                "leakage_violations": leakage_violations,
                "capability_threshold": cap_threshold,
                "risk_threshold": risk_threshold,
                "frozen_policy_check": frozen_policy_check,
                "pass_operating_gate": pass_gate,
                **metrics,
            }
            out_rows.append(item)
            task_entry["models"][model_key] = item

        by_task_model[task] = task_entry

    # Holm-Bonferroni correction across all task×model McNemar comparisons.
    # Without correction, 24 uncorrected tests (8 tasks × 3 SLMs) expect ~1.2
    # false positives at α=0.05 by chance alone.
    _apply_holm_correction(out_rows)

    BENCHMARKING_OUT.mkdir(parents=True, exist_ok=True)
    stem = str(args.output_stem or "test_phase_report").strip()
    if not stem:
        stem = "test_phase_report"
    json_path = BENCHMARKING_OUT / f"{stem}.json"
    csv_path = BENCHMARKING_OUT / f"{stem}.csv"
    md_path = BENCHMARKING_OUT / f"{stem}.md"

    json_path.write_text(json.dumps(by_task_model, indent=2), encoding="utf-8")

    flat_rows = out_rows
    split_names = sorted({str(item.get("report_split") or "").strip() for item in flat_rows if isinstance(item, dict)})
    if args.strict_leakage:
        non_empty_splits = [s for s in split_names if s]
        if len(non_empty_splits) > 1:
            raise RuntimeError(
                "Leakage guard failed: mixed report splits found in one phase report: "
                + ", ".join(non_empty_splits)
            )
    phase_label = ", ".join([s for s in split_names if s]) if split_names else "unknown"

    if flat_rows:
        headers = [
            "task",
            "display_name",
            "hash_split_policy",
            "report_split",
            "threshold_split",
            "tau_star_difficulty",
            "split_contract_ok",
            "frozen_policy_check",
            "train_curve_row_count",
            "val_threshold_row_count",
            "report_row_count",
            "leakage_violations",
            "pass_operating_gate",
            "n_rows",
            "coverage_slm",
            "coverage_slm_or_hybrid",
            "selected_capability",
            "selected_risk",
            "utility",
            "precision",
            "precision_ci90_lo",
            "precision_ci90_hi",
            "recall",
            "recall_ci90_lo",
            "recall_ci90_hi",
            "f1",
            "f1_ci90_lo",
            "f1_ci90_hi",
            "accuracy",
            "accuracy_ci90_lo",
            "accuracy_ci90_hi",
            "capability_ece",
            "capability_brier",
            "risk_ece",
            "risk_brier",
            "selected_capability_ci90_lo",
            "selected_capability_ci90_hi",
            "selected_risk_ci90_lo",
            "selected_risk_ci90_hi",
            "utility_ci90_lo",
            "utility_ci90_hi",
            "always_slm_accuracy",
            "always_baseline_accuracy",
            "delta_accuracy_vs_always_slm",
            "delta_accuracy_vs_always_baseline",
            "mcnemar_p_policy_vs_always_slm",
            "mcnemar_p_policy_vs_always_slm_holm",
            "mcnemar_p_policy_vs_always_baseline",
            "mcnemar_p_policy_vs_always_baseline_holm",
            "utility_always_slm",
            "utility_always_baseline",
            "delta_utility_vs_always_slm",
            "delta_utility_vs_always_baseline",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in flat_rows:
                writer.writerow(
                    {
                        "task": row["task"],
                        "display_name": row["display_name"],
                        "hash_split_policy": row["hash_split_policy"],
                        "report_split": row["report_split"],
                        "threshold_split": row["threshold_split"],
                        "tau_star_difficulty": row["tau_star_difficulty"],
                        "split_contract_ok": row["split_contract_ok"],
                        "frozen_policy_check": row["frozen_policy_check"],
                        "train_curve_row_count": row["train_curve_row_count"],
                        "val_threshold_row_count": row["val_threshold_row_count"],
                        "report_row_count": row["report_row_count"],
                        "leakage_violations": ";".join(row["leakage_violations"]),
                        "pass_operating_gate": row["pass_operating_gate"],
                        "n_rows": row["n_rows"],
                        "coverage_slm": row["coverage_slm"],
                        "coverage_slm_or_hybrid": row["coverage_slm_or_hybrid"],
                        "selected_capability": row["selected_capability"],
                        "selected_risk": row["selected_risk"],
                        "utility": row["utility"],
                        "precision": row["routing_quality"]["precision"],
                        "precision_ci90_lo": row["bootstrap_ci_90"]["precision"][0],
                        "precision_ci90_hi": row["bootstrap_ci_90"]["precision"][1],
                        "recall": row["routing_quality"]["recall"],
                        "recall_ci90_lo": row["bootstrap_ci_90"]["recall"][0],
                        "recall_ci90_hi": row["bootstrap_ci_90"]["recall"][1],
                        "f1": row["routing_quality"]["f1"],
                        "f1_ci90_lo": row["bootstrap_ci_90"]["f1"][0],
                        "f1_ci90_hi": row["bootstrap_ci_90"]["f1"][1],
                        "accuracy": row["routing_quality"]["accuracy"],
                        "accuracy_ci90_lo": row["bootstrap_ci_90"]["accuracy"][0],
                        "accuracy_ci90_hi": row["bootstrap_ci_90"]["accuracy"][1],
                        "capability_ece": row["calibration"]["capability_ece"],
                        "capability_brier": row["calibration"]["capability_brier"],
                        "risk_ece": row["calibration"]["risk_ece"],
                        "risk_brier": row["calibration"]["risk_brier"],
                        "selected_capability_ci90_lo": row["bootstrap_ci_90"]["selected_capability"][0],
                        "selected_capability_ci90_hi": row["bootstrap_ci_90"]["selected_capability"][1],
                        "selected_risk_ci90_lo": row["bootstrap_ci_90"]["selected_risk"][0],
                        "selected_risk_ci90_hi": row["bootstrap_ci_90"]["selected_risk"][1],
                        "utility_ci90_lo": row["bootstrap_ci_90"]["utility"][0],
                        "utility_ci90_hi": row["bootstrap_ci_90"]["utility"][1],
                        "always_slm_accuracy": row["baseline_quality"]["always_slm"]["accuracy"],
                        "always_baseline_accuracy": row["baseline_quality"]["always_baseline"]["accuracy"],
                        "delta_accuracy_vs_always_slm": (
                            row["routing_quality"]["accuracy"] - row["baseline_quality"]["always_slm"]["accuracy"]
                        ),
                        "delta_accuracy_vs_always_baseline": (
                            row["routing_quality"]["accuracy"] - row["baseline_quality"]["always_baseline"]["accuracy"]
                        ),
                        "mcnemar_p_policy_vs_always_slm": row["significance"]["policy_vs_always_slm_mcnemar"]["p_value"],
                        "mcnemar_p_policy_vs_always_slm_holm": row["significance"]["policy_vs_always_slm_mcnemar"].get("p_value_holm_adjusted"),
                        "mcnemar_p_policy_vs_always_baseline": row["significance"]["policy_vs_always_baseline_mcnemar"]["p_value"],
                        "mcnemar_p_policy_vs_always_baseline_holm": row["significance"]["policy_vs_always_baseline_mcnemar"].get("p_value_holm_adjusted"),
                        "utility_always_slm": row["baseline_utility"]["always_slm"],
                        "utility_always_baseline": row["baseline_utility"]["always_baseline"],
                        "delta_utility_vs_always_slm": row["utility"] - row["baseline_utility"]["always_slm"],
                        "delta_utility_vs_always_baseline": row["utility"] - row["baseline_utility"]["always_baseline"],
                    }
                )

        lines = [
            f"# {phase_label.title()} Phase Report (Frozen Policy)",
            "",
            "## Leakage Proof",
            "",
            f"- Hash split policy: `{HASH_POLICY}`",
            f"- Strict leakage mode: `{'on' if args.strict_leakage else 'off'}`",
            "",
            "| Task | Model | report_split | threshold_split | train_rows | val_rows | report_rows | Frozen Policy | Split Contract OK | Leakage Violations |",
            "|---|---|---|---|---:|---:|---:|:---:|:---:|---|",
        ]
        for row in flat_rows:
            lines.append(
                f"| {row['task']} | {row['display_name']} | {row['report_split']} | {row['threshold_split']} | "
                f"{row['train_curve_row_count']} | {row['val_threshold_row_count']} | {row['report_row_count']} | "
                f"{'yes' if row['frozen_policy_check'] else 'no'} | {'yes' if row['split_contract_ok'] else 'no'} | "
                f"{';'.join(row['leakage_violations']) if row['leakage_violations'] else 'none'} |"
            )
        lines.extend(
            [
                "",
                "## Primary Statistical Results",
                "",
                "| Task | Model | N | Pass Gate | Precision [90% CI] | Recall [90% CI] | F1 [90% CI] | Acc [90% CI] | p(McNemar vs Always-SLM) | p_holm | dUtility vs Always-SLM |",
                "|---|---|---:|:---:|---|---|---|---|---:|---:|---:|",
            ]
        )
        for row in flat_rows:
            p_raw = row["significance"]["policy_vs_always_slm_mcnemar"]["p_value"]
            p_adj = row["significance"]["policy_vs_always_slm_mcnemar"].get("p_value_holm_adjusted")
            p_adj_txt = f"{p_adj:.4f}" if p_adj is not None else "NA"
            lines.append(
                f"| {row['task']} | {row['display_name']} | {row['n_rows']} | "
                f"{'yes' if row['pass_operating_gate'] else 'no'} | "
                f"{row['routing_quality']['precision']:.3f} [{row['bootstrap_ci_90']['precision'][0]:.3f}, {row['bootstrap_ci_90']['precision'][1]:.3f}] | "
                f"{row['routing_quality']['recall']:.3f} [{row['bootstrap_ci_90']['recall'][0]:.3f}, {row['bootstrap_ci_90']['recall'][1]:.3f}] | "
                f"{row['routing_quality']['f1']:.3f} [{row['bootstrap_ci_90']['f1'][0]:.3f}, {row['bootstrap_ci_90']['f1'][1]:.3f}] | "
                f"{row['routing_quality']['accuracy']:.3f} [{row['bootstrap_ci_90']['accuracy'][0]:.3f}, {row['bootstrap_ci_90']['accuracy'][1]:.3f}] | "
                f"{p_raw:.4f} | "
                f"{p_adj_txt} | "
                f"{(row['utility'] - row['baseline_utility']['always_slm']):.3f} |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        csv_path.write_text("", encoding="utf-8")
        md_path.write_text("# Phase Report (Frozen Policy)\n\nNo rows found.\n", encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {md_path}")
    print(f"Task-model rows: {len(flat_rows)}")


if __name__ == "__main__":
    main()
