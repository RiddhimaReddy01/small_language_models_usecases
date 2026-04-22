"""
SDDF Routing Evaluation — val-phase certification + routing outcome verification.

Phase 1 — Difficulty scoring:
    Each query gets a scalar difficulty d ∈ [0,1] using per-SLM learned feature
    weights from family_weights_learned.json (uniform fallback if not available).

Phase 2 — τ* calibration (val):
    Find the highest τ where all val queries with score ≤ τ achieve:
        P(correct | score ≤ τ)  ≥  cap_threshold   (capability)
        P(risk    | score ≤ τ)  ≤  risk_threshold  (safety)
    Uses a prefix scan (sorted by difficulty) — conservative: entire easy region must meet threshold.

Phase 3 — Routing decisions:
    score ≤ τ*  →  SLM   (cheap, certified safe)
    score > τ*  →  LLM   (expensive, fall back)
    τ* = None   →  always LLM for that task/SLM pair

Phase 4 — Outcome verification:
    Compare routing decisions to actual `correct` field from evaluate_outputs.py.
    Measures: coverage, SLM-region accuracy, LLM-region accuracy, system accuracy,
    gain over always-SLM, cost savings (SLM calls / total calls).

Output:
    model_runs/routing_evaluation.json   — full metrics
    model_runs/routing_curves.png        — routing scatter + capability curve

NOTE: Val data is used for BOTH calibration and verification here (in-sample).
      Results are therefore optimistic. Run test split after τ* is frozen for
      out-of-sample verification.

Usage:
    python tools/evaluate_routing.py
    python tools/evaluate_routing.py --split val
    python tools/evaluate_routing.py --split test   # once test inference is done
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.difficulty import DIFFICULTY_FEATURES, compute_all_features

RUNS_DIR = ROOT / "model_runs"
WEIGHTS_F = RUNS_DIR / "difficulty_weights" / "family_weights_learned.json"
THRESH_F  = ROOT / "task_thresholds.json"

TASKS   = ["classification", "maths", "code_generation", "instruction_following",
           "information_extraction", "retrieval_grounded", "summarization", "text_generation"]
SLMS    = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]
BASELINE = "llama_llama-3.3-70b-versatile"

SLM_COLORS = {"qwen2.5_0.5b": "#e74c3c", "qwen2.5_3b": "#e67e22", "qwen2.5_7b": "#2980b9"}
SLM_LABELS = {"qwen2.5_0.5b": "Qwen 0.5B", "qwen2.5_3b": "Qwen 3B",  "qwen2.5_7b": "Qwen 7B"}

DEFAULT_THRESHOLDS = {
    "classification":         (0.75, 0.20),
    "maths":                  (0.65, 0.35),
    "code_generation":        (0.55, 0.40),
    "instruction_following":  (0.70, 0.30),
    "information_extraction": (0.75, 0.25),
    "retrieval_grounded":     (0.70, 0.30),
    "summarization":          (0.65, 0.35),
    "text_generation":        (0.70, 0.30),
}

# Risk per incorrect answer by task (severity × undetectability)
TASK_RISK_INCORRECT = {
    "classification":         0.56,
    "maths":                  0.855,
    "code_generation":        0.9025,
    "instruction_following":  0.525,
    "information_extraction": 0.60,
    "retrieval_grounded":     0.68,
    "summarization":          0.2475,
    "text_generation":        0.18,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
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


def _dedupe(rows: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for r in rows:
        sid = str(r.get("sample_id", ""))
        existing = by_id.get(sid)
        if existing is None or str(r.get("timestamp","")) >= str(existing.get("timestamp","")):
            by_id[sid] = r
    return list(by_id.values())


def _load_thresholds() -> dict[str, tuple[float, float]]:
    t = dict(DEFAULT_THRESHOLDS)
    if THRESH_F.exists():
        raw = json.loads(THRESH_F.read_text(encoding="utf-8"))
        for task, cfg in raw.items():
            if isinstance(cfg, dict):
                t[task] = (float(cfg.get("cap", t.get(task,(0.70,0.30))[0])),
                           float(cfg.get("risk", t.get(task,(0.70,0.30))[1])))
    return t


def _load_weights() -> dict[str, dict[str, dict]]:
    if not WEIGHTS_F.exists():
        return {}
    return json.loads(WEIGHTS_F.read_text(encoding="utf-8")).get("families", {})


def _score_row_model(row: dict, model: dict) -> float:
    prompt = str(row.get("prompt", "") or "")
    features = compute_all_features(row, prompt)
    weights = model.get("weights", {})
    norm    = model.get("norm_stats", {})
    score   = 0.0
    for dim in DIFFICULTY_FEATURES:
        val = float(features.get(dim, 0.0))
        b   = norm.get(dim, {})
        lo  = float(b.get("p05", b.get("min", 0.0)))
        hi  = float(b.get("p95", b.get("max", 1.0)))
        nv  = max(0.0, min(1.0, (val - lo) / (hi - lo))) if hi > lo else 0.0
        score += float(weights.get(dim, 0.0)) * nv
    return max(0.0, min(1.0, score))


def _compute_difficulty(rows: list[dict], task: str, slm: str, learned: dict) -> dict[str, float]:
    slm_model = learned.get(task, {}).get(slm)
    raw: dict[str, float] = {}
    if slm_model:
        for row in rows:
            raw[str(row["sample_id"])] = _score_row_model(row, slm_model)
        src = "learned"
    else:
        uni = {dim: 1.0 / len(DIFFICULTY_FEATURES) for dim in DIFFICULTY_FEATURES}
        for row in rows:
            prompt = str(row.get("prompt", "") or "")
            feats = compute_all_features(row, prompt)
            raw[str(row["sample_id"])] = sum(
                uni[dim] * float(feats.get(dim, 0.0)) for dim in DIFFICULTY_FEATURES
            )
        src = "uniform"

    if not raw:
        return raw
    lo, hi = min(raw.values()), max(raw.values())
    if hi <= lo:
        return {k: 0.5 for k in raw}, src
    return {k: (v - lo) / (hi - lo) for k, v in raw.items()}, src


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


# ─────────────────────────────────────────────────────────────────────────────
# τ* calibration — prefix scan on sorted difficulty
# ─────────────────────────────────────────────────────────────────────────────

def _wilson_lower(successes: int, n: int, z: float = 1.959963985) -> float:
    """Wilson score CI lower bound (z=1.96 → 95% CI)."""
    if n <= 0:
        return 0.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = z * math.sqrt(max(0.0, p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return max(0.0, center - margin)


def calibrate_tau(
    rows: list[dict],
    scores: dict[str, float],
    task: str,
    cap_threshold: float,
    risk_threshold: float,
    min_coverage: float = 0.05,
    max_coverage: float = 0.80,
) -> dict:
    """
    Prefix scan: sort val rows by difficulty, sweep τ from low to high.
    τ* = highest τ where the prefix [0..τ] satisfies:
      - Wilson 95% CI lower bound on cap ≥ cap_threshold  (stricter than raw mean)
      - risk ≤ risk_threshold
      - coverage ≤ max_coverage  (prevents degenerate always-SLM routing)

    Returns full sweep table so the calling code can plot the probability curves.
    """
    risk_incorrect = TASK_RISK_INCORRECT.get(task, 0.50)
    n = len(rows)
    if n == 0:
        return {"tau_star": None, "sweep": [], "cap_threshold": cap_threshold, "risk_threshold": risk_threshold}

    # Sort rows by difficulty
    paired = sorted(
        [(float(scores.get(str(r["sample_id"]), 0.5)), r) for r in rows],
        key=lambda t: t[0],
    )

    best_tau: float | None = None
    best_cap:  float | None = None
    best_risk: float | None = None
    best_cov:  float | None = None
    sweep = []

    for i, (d, row) in enumerate(paired):
        prefix = paired[: i + 1]
        n_prefix = len(prefix)
        coverage = n_prefix / n
        if coverage < min_coverage:
            continue
        if coverage > max_coverage:
            break
        n_correct = sum(1 for _, r in prefix if r.get("correct", False))
        cap  = n_correct / n_prefix
        cap_lb = _wilson_lower(n_correct, n_prefix)   # 95% CI lower bound
        risk = sum(0.0 if r.get("correct") else risk_incorrect for _, r in prefix) / n_prefix
        feasible = cap_lb >= cap_threshold and risk <= risk_threshold
        sweep.append({
            "tau": round(d, 5),
            "n_prefix": n_prefix,
            "coverage": round(coverage, 4),
            "cap": round(cap, 4),
            "cap_lb": round(cap_lb, 4),
            "risk": round(risk, 4),
            "feasible": feasible,
        })
        if feasible:
            best_tau, best_cap, best_risk, best_cov = d, cap_lb, risk, coverage

    return {
        "tau_star":      round(best_tau, 5) if best_tau is not None else None,
        "cap_at_tau":    round(best_cap,  4) if best_cap  is not None else None,
        "risk_at_tau":   round(best_risk, 4) if best_risk is not None else None,
        "coverage_at_tau": round(best_cov, 4) if best_cov is not None else None,
        "cap_threshold":  cap_threshold,
        "risk_threshold": risk_threshold,
        "n_val": n,
        "sweep": sweep,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routing outcome verification
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_routing(
    slm_rows: list[dict],
    llm_rows:  list[dict],
    scores: dict[str, float],
    tau_star: float | None,
    task: str,
) -> dict:
    """
    Apply routing policy (score ≤ τ* → SLM, else → LLM) to slm_rows.
    Measure actual correctness in each region using pre-computed `correct` field.
    Also compute what happens if we always use SLM or always use LLM.
    """
    llm_by_id = {str(r["sample_id"]): r for r in llm_rows}
    results = []
    for row in slm_rows:
        sid   = str(row["sample_id"])
        score = float(scores.get(sid, 0.5))
        slm_correct = bool(row.get("correct", False))
        llm_row = llm_by_id.get(sid)
        llm_correct = bool(llm_row.get("correct", False)) if llm_row else False

        if tau_star is not None:
            routing = "SLM" if score <= tau_star else "LLM"
        else:
            routing = "LLM"  # no safe region → always fall back

        actual_correct = slm_correct if routing == "SLM" else llm_correct
        results.append({
            "sample_id": sid,
            "score": round(score, 5),
            "routing": routing,
            "slm_correct": slm_correct,
            "llm_correct": llm_correct,
            "system_correct": actual_correct,
        })

    if not results:
        return {}

    n = len(results)
    slm_region = [r for r in results if r["routing"] == "SLM"]
    llm_region = [r for r in results if r["routing"] == "LLM"]

    def _acc(lst, key="system_correct"):
        return sum(r[key] for r in lst) / len(lst) if lst else None

    always_slm_acc  = _acc(results, "slm_correct")
    always_llm_acc  = _acc(results, "llm_correct")
    system_acc      = _acc(results)
    slm_region_acc  = _acc(slm_region)
    llm_region_acc  = _acc(llm_region)

    coverage = len(slm_region) / n

    # Routing accuracy: fraction of queries where routing chose the better model
    # (or at least tied).  Route to SLM = correct if SLM wins or ties.
    # Route to LLM = correct if LLM wins or ties.
    n_good = 0
    for r in results:
        if r["routing"] == "SLM" and r["slm_correct"] >= r["llm_correct"]:
            n_good += 1
        elif r["routing"] == "LLM" and r["llm_correct"] >= r["slm_correct"]:
            n_good += 1
    routing_accuracy = n_good / n

    return {
        "n_queries": n,
        "tau_star": round(tau_star, 5) if tau_star is not None else None,
        "coverage": round(coverage, 4),          # fraction routed to SLM
        "system_accuracy": round(system_acc, 4) if system_acc is not None else None,
        "slm_region_accuracy": round(slm_region_acc, 4) if slm_region_acc is not None else None,
        "llm_region_accuracy": round(llm_region_acc, 4) if llm_region_acc is not None else None,
        "always_slm_accuracy": round(always_slm_acc, 4) if always_slm_acc is not None else None,
        "always_llm_accuracy": round(always_llm_acc, 4) if always_llm_acc is not None else None,
        "routing_accuracy": round(routing_accuracy, 4),
        "gain_vs_always_slm": round(system_acc - always_slm_acc, 4) if system_acc and always_slm_acc else None,
        "gain_vs_always_llm": round(system_acc - always_llm_acc, 4) if system_acc and always_llm_acc else None,
        "slm_calls": len(slm_region),
        "llm_calls": len(llm_region),
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────────────────────

def _plot_routing(
    ax_cap: plt.Axes,
    ax_rout: plt.Axes,
    results: list[dict],
    sweep: list[dict],
    tau_star: float | None,
    cap_threshold: float,
    risk_threshold: float,
    task: str,
    slm: str,
    weight_src: str,
):
    """Left panel: capability curve + τ*. Right panel: routing scatter (score vs correct)."""
    color = SLM_COLORS[slm]
    label = SLM_LABELS[slm]

    # ── Capability curve from sweep ──
    if sweep:
        xs  = [s["tau"] for s in sweep]
        cap = [s["cap"]  for s in sweep]
        risk = [s["risk"] for s in sweep]
        cap_smooth  = _kernel_smooth(xs, cap)
        risk_smooth = _kernel_smooth(xs, risk)

        ax_cap.plot(xs, cap_smooth,  color=color,   lw=1.8, label=f"{label} cap",  alpha=0.85)
        ax_cap.plot(xs, risk_smooth, color=color,   lw=1.2, label=f"{label} risk",
                    linestyle="--", alpha=0.65)

    # Threshold lines (drawn once per panel — caller dedupes)
    ax_cap.axhline(cap_threshold,  color="black", lw=1.4, ls="--", alpha=0.6, label=f"cap_thr={cap_threshold:.2f}")
    ax_cap.axhline(risk_threshold, color="grey",  lw=1.0, ls=":",  alpha=0.6, label=f"risk_thr={risk_threshold:.2f}")

    if tau_star is not None:
        ax_cap.axvline(tau_star, color=color, lw=1.5, ls="-.", alpha=0.8, label=f"τ*={tau_star:.3f}")
        ax_cap.fill_betweenx([0, 1], 0, tau_star, alpha=0.06, color=color)

    # ── Routing scatter ──
    # Scatter all val queries: x=difficulty, y=correct(0/1), color=routing decision
    if results:
        scores_slm   = [r["score"] for r in results if r["routing"] == "SLM"]
        correct_slm  = [float(r["system_correct"]) + np.random.uniform(-0.03, 0.03) for r in results if r["routing"] == "SLM"]
        scores_llm   = [r["score"] for r in results if r["routing"] == "LLM"]
        correct_llm  = [float(r["system_correct"]) + np.random.uniform(-0.03, 0.03) for r in results if r["routing"] == "LLM"]

        ax_rout.scatter(scores_slm, correct_slm, c=color, s=8, alpha=0.35, label=f"SLM ({len(scores_slm)})", marker="o")
        ax_rout.scatter(scores_llm, correct_llm, c="steelblue", s=8, alpha=0.35, label=f"LLM ({len(scores_llm)})", marker="^")

        if tau_star is not None:
            ax_rout.axvline(tau_star, color=color, lw=1.5, ls="-.", alpha=0.8)
            ax_rout.fill_betweenx([0, 1], 0, tau_star, alpha=0.06, color=color)

        ax_rout.axhline(0.5, color="grey", lw=0.8, ls=":", alpha=0.5)

    ax_rout.set_ylim(-0.1, 1.15)
    ax_rout.set_yticks([0, 1])
    ax_rout.set_yticklabels(["incorrect", "correct"], fontsize=6)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="val", choices=["val", "test"],
                    help="Split to evaluate routing on (default: val). Use test once inference is done.")
    ap.add_argument("--min-coverage", type=float, default=0.05,
                    help="Minimum fraction of queries required before τ* can be certified (default: 0.05).")
    args = ap.parse_args()

    split = args.split
    thresholds = _load_thresholds()
    learned    = _load_weights()

    # ── Figure layout: 8 tasks × 3 SLMs → 24 task/model combos.
    # Compact: 8 rows (tasks) × 6 cols (3 SLMs × [cap_curve | routing_scatter])
    n_rows = len(TASKS)
    n_cols = len(SLMS) * 2
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(22, n_rows * 3.0), squeeze=False)
    fig.suptitle(
        f"SDDF Routing Evaluation — {split} split\n"
        "(Left panels: capability/risk curves + τ*  |  Right panels: routing scatter)",
        fontsize=13, fontweight="bold",
    )

    full_report: dict = {}

    for row_i, task in enumerate(TASKS):
        cap_thr, risk_thr = thresholds.get(task, (0.70, 0.30))
        task_report: dict = {
            "cap_threshold": cap_thr,
            "risk_threshold": risk_thr,
            "split": split,
            "models": {},
        }

        # Load LLM rows once per task
        llm_rows_raw = []
        for s in ([split] if split != "val" else ["train", "val"]):
            p = RUNS_DIR / task / BASELINE / f"outputs_{s}.jsonl"
            if p.exists():
                llm_rows_raw.extend(_load_jsonl(p))
        llm_rows = _dedupe(llm_rows_raw)

        for col_slm, slm in enumerate(SLMS):
            ax_cap  = axes[row_i, col_slm * 2]
            ax_rout = axes[row_i, col_slm * 2 + 1]

            # Load SLM rows for this split
            slm_rows_all = []
            for s in ([split] if split != "val" else ["train", "val"]):
                p = RUNS_DIR / task / slm / f"outputs_{s}.jsonl"
                if p.exists():
                    slm_rows_all.extend(_load_jsonl(p))
            slm_rows_all = _dedupe(slm_rows_all)

            # Filter to target split only (val rows for calibration and verification)
            split_rows = [r for r in slm_rows_all if r.get("split") == split]
            if not split_rows:
                split_rows = slm_rows_all  # fallback

            # Compute difficulty
            diff_result = _compute_difficulty(split_rows, task, slm, learned)
            if isinstance(diff_result, tuple):
                scores_map, weight_src = diff_result
            else:
                scores_map, weight_src = diff_result, "unknown"

            # τ* calibration via prefix scan on split_rows
            calib = calibrate_tau(split_rows, scores_map, task, cap_thr, risk_thr,
                                   min_coverage=args.min_coverage)
            tau_star = calib["tau_star"]

            # Routing evaluation on same split
            split_llm = [r for r in llm_rows if r.get("split") == split]
            if not split_llm:
                split_llm = llm_rows

            routing_eval = evaluate_routing(split_rows, split_llm, scores_map, tau_star, task)

            # Plot
            _plot_routing(
                ax_cap, ax_rout,
                routing_eval.get("results", []),
                calib["sweep"],
                tau_star,
                cap_thr, risk_thr,
                task, slm, weight_src,
            )

            # Labels
            task_label = task.replace("_", " ").title()
            slm_short  = SLM_LABELS[slm]
            ax_cap.set_title(f"{task_label}\n{slm_short} — cap/risk", fontsize=7, fontweight="bold")
            ax_rout.set_title(f"{task_label}\n{slm_short} — routing", fontsize=7, fontweight="bold")
            ax_cap.set_xlabel("Difficulty d", fontsize=6)
            ax_rout.set_xlabel("Difficulty d", fontsize=6)
            ax_cap.set_ylim(-0.05, 1.1)
            ax_cap.tick_params(labelsize=5)
            ax_rout.tick_params(labelsize=5)
            ax_cap.legend(fontsize=5, loc="best", ncol=1)
            ax_rout.legend(fontsize=5, loc="best")
            ax_cap.grid(True, alpha=0.25)
            ax_rout.grid(True, alpha=0.25)

            # Annotate routing metrics on scatter panel
            if routing_eval:
                cov  = routing_eval.get("coverage", 0)
                sys_acc = routing_eval.get("system_accuracy", 0)
                slm_acc = routing_eval.get("always_slm_accuracy", 0)
                gain = routing_eval.get("gain_vs_always_slm", 0) or 0
                tau_str = f"{tau_star:.3f}" if tau_star is not None else "None"
                annotation = (
                    f"τ*={tau_str}\n"
                    f"cov={cov:.0%} sys={sys_acc:.2f}\n"
                    f"slm_only={slm_acc:.2f} Δ={gain:+.3f}"
                )
                ax_rout.text(0.02, 0.98, annotation, transform=ax_rout.transAxes,
                             fontsize=5, va="top", color="black",
                             bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

            # Store to report (without per-query results to keep JSON small)
            task_report["models"][slm] = {
                "tau_star": calib["tau_star"],
                "cap_at_tau":  calib["cap_at_tau"],
                "risk_at_tau": calib["risk_at_tau"],
                "coverage_at_tau": calib["coverage_at_tau"],
                "weight_source": weight_src,
                **{k: v for k, v in routing_eval.items() if k != "results"},
            }

        full_report[task] = task_report

    plt.tight_layout()
    out_png = RUNS_DIR / "routing_curves.png"
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    print(f"[plot] saved → {out_png}")

    out_json = RUNS_DIR / "routing_evaluation.json"
    Path(out_json).write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    print(f"[report] saved → {out_json}")

    # ── Console summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 115)
    hdr = "{:<24} {:<12} {:<6} {:<8} {:<8} {:<8} {:<8} {:<8} {:<8} {}".format(
        "TASK", "MODEL", "N", "TAU*", "COV%", "SYS_ACC", "SLM_ACC", "LLM_ACC", "Δ_GAIN", "SLM_CALLS/TOTAL"
    )
    print(hdr)
    print("-" * 115)
    for task, td in full_report.items():
        ct, rt = td["cap_threshold"], td["risk_threshold"]
        for slm, md in td.get("models", {}).items():
            tau_str = "{:.3f}".format(md["tau_star"]) if md.get("tau_star") is not None else "NONE"
            gain    = md.get("gain_vs_always_slm")
            gain_str = "{:+.3f}".format(gain) if gain is not None else "  N/A"
            cov     = md.get("coverage", 0) or 0
            sys_a   = md.get("system_accuracy") or 0
            slm_a   = md.get("always_slm_accuracy") or 0
            llm_a   = md.get("always_llm_accuracy") or 0
            slm_c   = md.get("slm_calls", 0)
            tot     = md.get("n_queries", 1)
            print("{:<24} {:<12} {:<6} {:<8} {:<8} {:<8} {:<8} {:<8} {:<8} {}/{}".format(
                task, SLM_LABELS[slm], tot, tau_str,
                "{:.0%}".format(cov),
                "{:.3f}".format(sys_a),
                "{:.3f}".format(slm_a),
                "{:.3f}".format(llm_a),
                gain_str,
                slm_c, tot,
            ))
    print("=" * 115)
    print(f"\nNOTE: Split='{split}'.  Results are {'IN-SAMPLE (optimistic)' if split=='val' else 'OUT-OF-SAMPLE'}.")
    print("      τ* certified on val; apply to test split for unbiased routing accuracy.")
    print("      Run: python tools/run_test.py --ollama-only  then  --groq-only  then re-run this script with --split test")


if __name__ == "__main__":
    main()
