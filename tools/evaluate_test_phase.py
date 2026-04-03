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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
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


def _ece_binary(pred: list[float], obs: list[float], bins: int = 10) -> float:
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
        safe_true = 1.0 if (act_cap >= cap_threshold and act_risk <= risk_threshold) else 0.0
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
    cap_ece = _ece_binary(exp_cap, obs_cap, bins=10)
    cap_brier = _brier(exp_cap, obs_cap)
    risk_ece = _ece_binary(exp_risk, obs_risk, bins=10)
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

    def _metric_risk(boot: list[dict[str, float]]) -> float:
        picked = [x["actual_risk"] for x in boot if x["is_slm"] > 0.5]
        return float(np.mean(picked)) if picked else 1.0

    samples = list(eval_rows)
    p_lo, p_hi = _bootstrap_ci(samples, _metric_precision)
    r_lo, r_hi = _bootstrap_ci(samples, _metric_recall)
    f_lo, f_hi = _bootstrap_ci(samples, _metric_f1)
    c_lo, c_hi = _bootstrap_ci(samples, _metric_cov)
    sr_lo, sr_hi = _bootstrap_ci(samples, _metric_risk)

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
            "coverage_slm": [float(c_lo), float(c_hi)],
            "selected_risk": [float(sr_lo), float(sr_hi)],
        },
    }


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
                "capability_threshold": cap_threshold,
                "risk_threshold": risk_threshold,
                "frozen_policy_check": bool(threshold_split == "val"),
                "pass_operating_gate": pass_gate,
                **metrics,
            }
            out_rows.append(item)
            task_entry["models"][model_key] = item

        by_task_model[task] = task_entry

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
    phase_label = ", ".join([s for s in split_names if s]) if split_names else "unknown"

    if flat_rows:
        headers = [
            "task",
            "display_name",
            "report_split",
            "threshold_split",
            "tau_star_difficulty",
            "frozen_policy_check",
            "pass_operating_gate",
            "n_rows",
            "coverage_slm",
            "coverage_slm_or_hybrid",
            "selected_capability",
            "selected_risk",
            "utility",
            "precision",
            "recall",
            "f1",
            "accuracy",
            "capability_ece",
            "capability_brier",
            "risk_ece",
            "risk_brier",
            "always_slm_accuracy",
            "always_baseline_accuracy",
            "delta_accuracy_vs_always_slm",
            "delta_accuracy_vs_always_baseline",
            "mcnemar_p_policy_vs_always_slm",
            "mcnemar_p_policy_vs_always_baseline",
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
                        "report_split": row["report_split"],
                        "threshold_split": row["threshold_split"],
                        "tau_star_difficulty": row["tau_star_difficulty"],
                        "frozen_policy_check": row["frozen_policy_check"],
                        "pass_operating_gate": row["pass_operating_gate"],
                        "n_rows": row["n_rows"],
                        "coverage_slm": row["coverage_slm"],
                        "coverage_slm_or_hybrid": row["coverage_slm_or_hybrid"],
                        "selected_capability": row["selected_capability"],
                        "selected_risk": row["selected_risk"],
                        "utility": row["utility"],
                        "precision": row["routing_quality"]["precision"],
                        "recall": row["routing_quality"]["recall"],
                        "f1": row["routing_quality"]["f1"],
                        "accuracy": row["routing_quality"]["accuracy"],
                        "capability_ece": row["calibration"]["capability_ece"],
                        "capability_brier": row["calibration"]["capability_brier"],
                        "risk_ece": row["calibration"]["risk_ece"],
                        "risk_brier": row["calibration"]["risk_brier"],
                        "always_slm_accuracy": row["baseline_quality"]["always_slm"]["accuracy"],
                        "always_baseline_accuracy": row["baseline_quality"]["always_baseline"]["accuracy"],
                        "delta_accuracy_vs_always_slm": (
                            row["routing_quality"]["accuracy"] - row["baseline_quality"]["always_slm"]["accuracy"]
                        ),
                        "delta_accuracy_vs_always_baseline": (
                            row["routing_quality"]["accuracy"] - row["baseline_quality"]["always_baseline"]["accuracy"]
                        ),
                        "mcnemar_p_policy_vs_always_slm": row["significance"]["policy_vs_always_slm_mcnemar"]["p_value"],
                        "mcnemar_p_policy_vs_always_baseline": row["significance"]["policy_vs_always_baseline_mcnemar"]["p_value"],
                        "utility_always_slm": row["baseline_utility"]["always_slm"],
                        "utility_always_baseline": row["baseline_utility"]["always_baseline"],
                        "delta_utility_vs_always_slm": row["utility"] - row["baseline_utility"]["always_slm"],
                        "delta_utility_vs_always_baseline": row["utility"] - row["baseline_utility"]["always_baseline"],
                    }
                )

        lines = [
            f"# {phase_label.title()} Phase Report (Frozen Policy)",
            "",
            "| Task | Model | N | Frozen Policy | Pass Gate | Coverage(SLM) | Capability(SLM) | Risk(SLM) | F1 | Acc | dAcc vs Always-SLM | p(McNemar) | dUtility vs Always-SLM |",
            "|---|---|---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in flat_rows:
            lines.append(
                f"| {row['task']} | {row['display_name']} | {row['n_rows']} | "
                f"{'yes' if row['frozen_policy_check'] else 'no'} | "
                f"{'yes' if row['pass_operating_gate'] else 'no'} | "
                f"{row['coverage_slm']:.3f} | {row['selected_capability']:.3f} | {row['selected_risk']:.3f} | "
                f"{row['routing_quality']['f1']:.3f} | {row['routing_quality']['accuracy']:.3f} | "
                f"{(row['routing_quality']['accuracy'] - row['baseline_quality']['always_slm']['accuracy']):.3f} | "
                f"{row['significance']['policy_vs_always_slm_mcnemar']['p_value']:.4f} | "
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
