"""
SDDF Audit: Capability & Risk Curves with Thresholds.

Reads model output files (outputs_{split}.jsonl), uses evaluate_outputs.py
`correct` field for capability, and the SDDF internal risk model for risk.
Difficulty is scored from raw features using per-SLM learned weights from
family_weights_learned.json (falls back to uniform).

Output: model_runs/sddf_audit_curves.png
        model_runs/sddf_audit_report.json

Usage:
    python tools/plot_sddf_audit.py
    python tools/plot_sddf_audit.py --split train
    python tools/plot_sddf_audit.py --split val
    python tools/plot_sddf_audit.py --split train val
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.difficulty import DIFFICULTY_FEATURES, compute_all_features

RUNS_DIR   = ROOT / "model_runs"
WEIGHTS_F  = RUNS_DIR / "difficulty_weights" / "family_weights_learned.json"
THRESH_F   = ROOT / "task_thresholds.json"

TASKS  = ["classification", "maths", "code_generation", "instruction_following",
          "information_extraction", "retrieval_grounded", "summarization", "text_generation"]
SLMS   = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]
BASELINE = "llama_llama-3.3-70b-versatile"

SLM_COLORS  = {"qwen2.5_0.5b": "#e74c3c", "qwen2.5_3b": "#e67e22", "qwen2.5_7b": "#2ecc71"}
SLM_LABELS  = {"qwen2.5_0.5b": "Qwen 0.5B", "qwen2.5_3b": "Qwen 3B", "qwen2.5_7b": "Qwen 7B"}

# Default task thresholds (cap, risk)
DEFAULT_THRESHOLDS = {
    "classification":         (0.85, 0.15),
    "maths":                  (0.70, 0.30),
    "code_generation":        (0.65, 0.35),
    "instruction_following":  (0.75, 0.25),
    "information_extraction": (0.80, 0.20),
    "retrieval_grounded":     (0.80, 0.20),
    "summarization":          (0.70, 0.30),
    "text_generation":        (0.75, 0.25),
}


# ─────────────────────────────────────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def _load_task_thresholds() -> dict[str, tuple[float, float]]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if THRESH_F.exists():
        raw = json.loads(THRESH_F.read_text(encoding="utf-8"))
        for task, cfg in raw.items():
            if isinstance(cfg, dict):
                thresholds[task] = (float(cfg.get("cap", 0.80)), float(cfg.get("risk", 0.20)))
    return thresholds


def _load_learned_weights() -> dict[str, dict[str, dict]]:
    """Returns {task: {model: {weights, norm_stats}}}"""
    if not WEIGHTS_F.exists():
        return {}
    raw = json.loads(WEIGHTS_F.read_text(encoding="utf-8"))
    return raw.get("families", {})


# ─────────────────────────────────────────────────────────────────────────────
# Difficulty scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_row(row: dict, weights: dict, norm_stats: dict) -> float:
    prompt = str(row.get("prompt", "") or "")
    features = compute_all_features(row, prompt)
    score = 0.0
    for dim in DIFFICULTY_FEATURES:
        val = float(features.get(dim, 0.0))
        bounds = norm_stats.get(dim, {})
        lo = float(bounds.get("p05", bounds.get("min", 0.0)))
        hi = float(bounds.get("p95", bounds.get("max", 1.0)))
        norm_val = max(0.0, min(1.0, (val - lo) / (hi - lo))) if hi > lo else 0.0
        score += float(weights.get(dim, 0.0)) * norm_val
    return max(0.0, min(1.0, score))


def _uniform_score(rows: list[dict]) -> dict[str, float]:
    uni = {dim: 1.0 / len(DIFFICULTY_FEATURES) for dim in DIFFICULTY_FEATURES}
    raw = {}
    for row in rows:
        prompt = str(row.get("prompt", "") or "")
        features = compute_all_features(row, prompt)
        raw[str(row["sample_id"])] = sum(
            uni.get(dim, 0.0) * float(features.get(dim, 0.0))
            for dim in DIFFICULTY_FEATURES
        )
    if not raw:
        return raw
    lo, hi = min(raw.values()), max(raw.values())
    if hi <= lo:
        return {k: 0.5 for k in raw}
    return {k: (v - lo) / (hi - lo) for k, v in raw.items()}


def _learned_scores(rows: list[dict], model: dict) -> dict[str, float]:
    weights = model.get("weights", {})
    norm_stats = model.get("norm_stats", {})
    raw = {}
    for row in rows:
        raw[str(row["sample_id"])] = _score_row(row, weights, norm_stats)
    if not raw:
        return raw
    lo, hi = min(raw.values()), max(raw.values())
    if hi <= lo:
        return {k: 0.5 for k in raw}
    return {k: (v - lo) / (hi - lo) for k, v in raw.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Risk model (SDDF internal — severity × undetectability per task)
# ─────────────────────────────────────────────────────────────────────────────

TASK_RISK: dict[str, dict[str, float]] = {
    "classification":         {"correct": 0.0, "incorrect": 0.56},
    "maths":                  {"correct": 0.0, "incorrect": 0.855},
    "code_generation":        {"correct": 0.0, "incorrect": 0.9025},
    "instruction_following":  {"correct": 0.0, "incorrect": 0.525},
    "information_extraction": {"correct": 0.0, "incorrect": 0.60},
    "retrieval_grounded":     {"correct": 0.0, "incorrect": 0.68},
    "summarization":          {"correct": 0.0, "incorrect": 0.2475},
    "text_generation":        {"correct": 0.0, "incorrect": 0.18},
}


def _row_risk(task: str, correct: bool) -> float:
    risk_table = TASK_RISK.get(task, {"correct": 0.0, "incorrect": 0.50})
    return risk_table["correct"] if correct else risk_table["incorrect"]


# ─────────────────────────────────────────────────────────────────────────────
# Curve smoothing — Gaussian kernel (Silverman bandwidth)
# ─────────────────────────────────────────────────────────────────────────────

def _kernel_smooth(xs: list[float], ys: list[float]) -> list[float]:
    n = len(xs)
    if n < 3:
        return list(ys)
    xa = np.array(xs, dtype=float)
    ya = np.array(ys, dtype=float)
    std_x = float(np.std(xa)) or 1.0
    bw = max(1e-6, 1.06 * std_x * (n ** -0.2))
    out = np.empty(n, dtype=float)
    for i in range(n):
        w = np.exp(-0.5 * ((xa - xa[i]) / bw) ** 2)
        tw = float(w.sum())
        out[i] = float((w * ya).sum() / tw) if tw > 1e-9 else float(ya.mean())
    return out.tolist()


def _local_proportion(xs: list[float], ys: list[float], d: float, k: int = 15) -> float:
    """k-NN local proportion at d."""
    if not xs:
        return 0.5
    indexed = sorted(range(len(xs)), key=lambda i: abs(xs[i] - d))
    neighbors = indexed[:min(k, len(xs))]
    return sum(ys[i] for i in neighbors) / len(neighbors)


def _find_tau(xs: list[float], cap_raw: list[float], risk_raw: list[float],
              cap_threshold: float, risk_threshold: float, k: int = 15) -> float | None:
    """Find highest d where local cap >= cap_threshold AND local risk <= risk_threshold."""
    candidates = sorted(set(xs), reverse=True)
    for d in candidates:
        cap = _local_proportion(xs, cap_raw, d, k)
        risk = _local_proportion(xs, risk_raw, d, k)
        if cap >= cap_threshold and risk <= risk_threshold:
            return d
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Data loading per task/model/split
# ─────────────────────────────────────────────────────────────────────────────

def load_rows(task: str, model: str, splits: list[str]) -> list[dict]:
    rows = []
    for split in splits:
        p = RUNS_DIR / task / model / f"outputs_{split}.jsonl"
        if p.exists():
            rows.extend(_load_jsonl(p))
    # dedupe by sample_id (latest timestamp wins)
    by_id: dict[str, dict] = {}
    for row in rows:
        sid = str(row.get("sample_id", ""))
        existing = by_id.get(sid)
        if existing is None or str(row.get("timestamp", "")) >= str(existing.get("timestamp", "")):
            by_id[sid] = row
    return list(by_id.values())


# ─────────────────────────────────────────────────────────────────────────────
# Routing signal analysis
# ─────────────────────────────────────────────────────────────────────────────

def routing_signal_stats(task: str, splits: list[str]) -> dict[str, dict]:
    """Binary routing signal: SLM incorrect AND baseline correct."""
    base_rows = {str(r["sample_id"]): r for r in load_rows(task, BASELINE, splits)}
    stats = {}
    for slm in SLMS:
        slm_rows = {str(r["sample_id"]): r for r in load_rows(task, slm, splits)}
        common = set(base_rows) & set(slm_rows)
        n_signal = 0
        for sid in common:
            slm_correct = bool(slm_rows[sid].get("correct", False))
            base_correct = bool(base_rows[sid].get("correct", False))
            if not slm_correct and base_correct:
                n_signal += 1
        stats[slm] = {
            "n_common": len(common),
            "n_signal": n_signal,
            "signal_rate": n_signal / len(common) if common else 0.0,
        }
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Build curve data per task/model
# ─────────────────────────────────────────────────────────────────────────────

def build_curves(task: str, slm: str, splits: list[str],
                 learned_weights: dict) -> dict | None:
    rows = load_rows(task, slm, splits)
    # Only rows that are scored
    rows = [r for r in rows if "correct" in r and "score" in r]
    if len(rows) < 5:
        return None

    # Difficulty scoring: learned → uniform fallback
    task_models = learned_weights.get(task, {})
    slm_model = task_models.get(slm)
    if slm_model:
        scores_map = _learned_scores(rows, slm_model)
        weight_source = "learned"
        weights_used = slm_model.get("weights", {})
    else:
        scores_map = _uniform_score(rows)
        weight_source = "uniform"
        weights_used = {dim: 1.0 / len(DIFFICULTY_FEATURES) for dim in DIFFICULTY_FEATURES}

    # Build (difficulty, correct, risk) triples
    triples = []
    for row in rows:
        sid = str(row["sample_id"])
        d = float(scores_map.get(sid, 0.5))
        correct = bool(row.get("correct", False))
        risk = _row_risk(task, correct)
        triples.append((d, float(correct), risk))
    triples.sort(key=lambda t: t[0])

    xs       = [t[0] for t in triples]
    cap_raw  = [t[1] for t in triples]
    risk_raw = [t[2] for t in triples]
    cap_smooth  = _kernel_smooth(xs, cap_raw)
    risk_smooth = _kernel_smooth(xs, risk_raw)

    overall_cap  = sum(cap_raw) / len(cap_raw)
    overall_risk = sum(risk_raw) / len(risk_raw)

    return {
        "xs": xs,
        "cap_raw": cap_raw,
        "cap_smooth": cap_smooth,
        "risk_raw": risk_raw,
        "risk_smooth": risk_smooth,
        "overall_cap": overall_cap,
        "overall_risk": overall_risk,
        "n_rows": len(rows),
        "weight_source": weight_source,
        "weights_used": weights_used,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Plot
# ─────────────────────────────────────────────────────────────────────────────

def plot_curves(splits: list[str]) -> None:
    thresholds   = _load_task_thresholds()
    learned_weights = _load_learned_weights()

    n_tasks = len(TASKS)
    fig, axes = plt.subplots(n_tasks, 2, figsize=(16, n_tasks * 3.2))
    fig.suptitle(
        f"SDDF Audit — Capability & Risk Curves\n(splits: {', '.join(splits)})",
        fontsize=14, fontweight="bold", y=1.002,
    )

    report: dict = {}

    for row_i, task in enumerate(TASKS):
        ax_cap  = axes[row_i, 0]
        ax_risk = axes[row_i, 1]
        cap_thr, risk_thr = thresholds.get(task, (0.80, 0.20))

        # Per-task annotation
        signal_stats = routing_signal_stats(task, splits)

        task_report: dict = {
            "cap_threshold": cap_thr,
            "risk_threshold": risk_thr,
            "routing_signal": signal_stats,
            "models": {},
        }

        any_tau = False
        for slm in SLMS:
            c = build_curves(task, slm, splits, learned_weights)
            if c is None:
                task_report["models"][slm] = {"error": "no scored rows"}
                continue

            xs   = c["xs"]
            cap_s  = c["cap_smooth"]
            risk_s = c["risk_smooth"]
            color  = SLM_COLORS[slm]
            label  = SLM_LABELS[slm]
            k_nn   = max(5, min(20, len(xs) // 10))
            tau = _find_tau(xs, c["cap_raw"], c["risk_raw"], cap_thr, risk_thr, k=k_nn)

            ax_cap.plot(xs, cap_s, color=color, linewidth=1.8, label=label, alpha=0.85)
            ax_risk.plot(xs, risk_s, color=color, linewidth=1.8, label=label, alpha=0.85)

            if tau is not None:
                any_tau = True
                ax_cap.axvline(tau, color=color, linestyle=":", linewidth=1.2, alpha=0.7)
                ax_risk.axvline(tau, color=color, linestyle=":", linewidth=1.2, alpha=0.7)
                # Mark τ* on cap curve
                cap_at_tau = _local_proportion(xs, c["cap_raw"], tau, k_nn)
                ax_cap.scatter([tau], [cap_at_tau], color=color, marker="*", s=80, zorder=5)
                risk_at_tau = _local_proportion(xs, c["risk_raw"], tau, k_nn)
                ax_risk.scatter([tau], [risk_at_tau], color=color, marker="*", s=80, zorder=5)

            task_report["models"][slm] = {
                "n_rows": c["n_rows"],
                "overall_cap": round(c["overall_cap"], 3),
                "overall_risk": round(c["overall_risk"], 3),
                "weight_source": c["weight_source"],
                "tau_star": round(tau, 4) if tau is not None else None,
                "routing_signal_rate": round(signal_stats.get(slm, {}).get("signal_rate", 0), 3),
            }

        # Threshold lines
        ax_cap.axhline(cap_thr, color="black", linestyle="--", linewidth=1.5,
                       label=f"cap threshold = {cap_thr:.2f}")
        ax_risk.axhline(risk_thr, color="black", linestyle="--", linewidth=1.5,
                        label=f"risk threshold = {risk_thr:.2f}")

        # Also plot baseline overall cap as reference
        base_rows = load_rows(task, BASELINE, splits)
        base_rows = [r for r in base_rows if "correct" in r]
        if base_rows:
            base_overall_cap = sum(float(r.get("correct", 0)) for r in base_rows) / len(base_rows)
            ax_cap.axhline(base_overall_cap, color="steelblue", linestyle="-.",
                           linewidth=1.2, alpha=0.7, label=f"LLM overall={base_overall_cap:.2f}")

        # Formatting
        task_label = task.replace("_", " ").title()
        ax_cap.set_title(f"{task_label}\nCapability P(correct | d)", fontsize=9, fontweight="bold")
        ax_risk.set_title(f"{task_label}\nRisk P(harm | d)", fontsize=9, fontweight="bold")
        ax_cap.set_xlabel("Difficulty score", fontsize=7)
        ax_risk.set_xlabel("Difficulty score", fontsize=7)
        ax_cap.set_ylabel("P(correct)", fontsize=7)
        ax_risk.set_ylabel("P(harm)", fontsize=7)
        ax_cap.set_ylim(-0.05, 1.1)
        ax_risk.set_ylim(-0.05, 1.1)
        ax_cap.tick_params(labelsize=6)
        ax_risk.tick_params(labelsize=6)
        ax_cap.legend(fontsize=6, loc="best")
        ax_risk.legend(fontsize=6, loc="best")
        ax_cap.grid(True, alpha=0.3)
        ax_risk.grid(True, alpha=0.3)

        # Signal annotation on cap plot
        sig_text = " | ".join(
            f"{SLM_LABELS[slm].split()[1]}: {v.get('signal_rate', 0)*100:.0f}%"
            for slm, v in signal_stats.items()
        )
        ax_cap.text(0.01, 0.02, f"routing signal: {sig_text}", transform=ax_cap.transAxes,
                    fontsize=5.5, color="gray", va="bottom")

        report[task] = task_report

    plt.tight_layout()
    out_png = RUNS_DIR / "sddf_audit_curves.png"
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"[plot] saved → {out_png}")

    out_json = RUNS_DIR / "sddf_audit_report.json"
    Path(out_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[report] saved → {out_json}")

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'TASK':<25} {'MODEL':<15} {'N':<5} {'SIGNAL%':<9} {'CAP':<7} {'RISK':<7} {'TAU*':<10} {'WEIGHT_SRC'}")
    print("=" * 100)
    for task, td in report.items():
        ct, rt = td["cap_threshold"], td["risk_threshold"]
        for slm, md in td.get("models", {}).items():
            if "error" in md:
                continue
            tau_str = f"{md['tau_star']:.3f}" if md["tau_star"] is not None else "NONE"
            flag = " ← NO TAU" if md["tau_star"] is None else ""
            print(
                f"{task:<25} {SLM_LABELS[slm]:<15} {md['n_rows']:<5} "
                f"{md['routing_signal_rate']*100:>5.1f}%   "
                f"{md['overall_cap']:.3f}  {md['overall_risk']:.3f}  "
                f"{tau_str:<10} {md['weight_source']}{flag}"
            )
    print("=" * 100)
    print(f"\nThresholds: {json.dumps({t: {'cap': v[0], 'risk': v[1]} for t, v in thresholds.items()}, indent=2)}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", nargs="+", default=["train", "val"],
                   choices=["train", "val", "test"])
    args = p.parse_args()
    plot_curves(args.split)


if __name__ == "__main__":
    main()
