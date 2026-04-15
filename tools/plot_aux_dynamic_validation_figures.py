from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.validation_dynamic import (
    build_difficulty_curves,
    compute_per_sample_metrics,
    run_validation,
)


def _label_fail(row: dict[str, Any]) -> int:
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _sanitize(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_", "."}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def _build_samples_and_scores(
    artifact_path: Path,
    splits_root: Path,
    score_source: str,
) -> tuple[str, str, Any, list[dict[str, Any]], dict[str, float]]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    task = str(artifact["task"])
    model = str(artifact["model"])
    seed = artifact.get("seed")

    val_path = splits_root / task / model / "val.jsonl"
    rows = _read_jsonl(val_path)
    if not rows:
        raise ValueError(f"Missing val split rows at {val_path}")

    ids: list[str] = []
    samples: list[dict[str, Any]] = []
    raw_scores: list[float] = []

    for i, row in enumerate(rows):
        sid = str(row.get("sample_id") or row.get("query_id") or f"{task}_{model}_{i}")
        ids.append(sid)
        if score_source == "score":
            sval = float(row.get("score", 0.5))
        else:
            # Default: use provided dataset bin in [0,9] as monotonic difficulty proxy.
            bval = float(row.get("bin", 5.0))
            sval = bval / 9.0
        raw_scores.append(sval)
        samples.append(
            {
                "sample_id": sid,
                "slm_correct": bool(1 - _label_fail(row)),
                "llm_correct": bool(row.get("llm_correct", True)),
                "failure_category": row.get("failure_category"),
                "failure_type": row.get("failure_type"),
                "severity": row.get("severity"),
                "severity_score": row.get("severity_score"),
                "risk_weight": row.get("risk_weight"),
                "status": row.get("status"),
                "valid": row.get("valid"),
                "error": row.get("error"),
            }
        )

    # Min-max normalize to [0,1] for validation_dynamic sorting.
    arr = np.array(raw_scores, dtype=float)
    lo = float(np.min(arr)) if arr.size else 0.0
    hi = float(np.max(arr)) if arr.size else 1.0
    if hi <= lo:
        norm = np.full_like(arr, 0.5, dtype=float)
    else:
        norm = (arr - lo) / (hi - lo)
    scores = {ids[i]: float(norm[i]) for i in range(len(ids))}
    return task, model, seed, samples, scores


def _plot_figures_for_run(
    *,
    out_dir: Path,
    task: str,
    model: str,
    seed: Any,
    cap_curve: dict[int, float],
    risk_curve: dict[int, float],
    coverage_by_bin: dict[int, int],
    cap_dyn: float,
    risk_dyn: float,
    selected_tau: Any,
    tau_source: str,
) -> None:
    bins = sorted(cap_curve.keys())
    if not bins:
        return

    cap_vals = [float(cap_curve[b]) for b in bins]
    risk_vals = [float(risk_curve.get(b, 1.0)) for b in bins]
    cov_total = float(sum(coverage_by_bin.values()))
    cov_vals = [(float(coverage_by_bin.get(b, 0)) / cov_total) if cov_total > 0 else 0.0 for b in bins]
    feasible = [
        (cap_vals[i] >= cap_dyn) and (risk_vals[i] <= risk_dyn) and (cov_vals[i] <= 0.70)
        for i in range(len(bins))
    ]

    tag = f"{_sanitize(task)}__{_sanitize(model)}__seed{seed}"
    tau_float = None if selected_tau is None else float(selected_tau)

    # Y1
    fig1, ax1 = plt.subplots(figsize=(7.2, 4.8))
    ax1.plot(bins, cap_vals, marker="o", lw=2)
    ax1.axhline(cap_dyn, ls="--", lw=1.5)
    if tau_float is not None:
        ax1.axvline(tau_float, ls="-.", lw=1.5)
    ax1.set_ylim(0.0, 1.05)
    ax1.set_xlabel("Difficulty Bin d")
    ax1.set_ylabel("Capability C_d")
    ax1.set_title(f"Y1 Capability Curve | {task} | {model} | seed={seed}")
    ax1.grid(alpha=0.25)
    fig1.tight_layout()
    fig1.savefig(out_dir / f"figure_Y1_capability_curve__{tag}.png", dpi=200)
    plt.close(fig1)

    # Y2
    fig2, ax2 = plt.subplots(figsize=(7.2, 4.8))
    ax2.plot(bins, risk_vals, marker="o", lw=2, color="#d95f02")
    ax2.axhline(risk_dyn, ls="--", lw=1.5, color="#1b9e77")
    if tau_float is not None:
        ax2.axvline(tau_float, ls="-.", lw=1.5, color="#7570b3")
    ax2.set_ylim(0.0, 1.05)
    ax2.set_xlabel("Difficulty Bin d")
    ax2.set_ylabel("Risk R_d")
    ax2.set_title(f"Y2 Risk Curve | {task} | {model} | seed={seed}")
    ax2.grid(alpha=0.25)
    fig2.tight_layout()
    fig2.savefig(out_dir / f"figure_Y2_risk_curve__{tag}.png", dpi=200)
    plt.close(fig2)

    # Y3
    fig3, ax3 = plt.subplots(figsize=(7.2, 4.8))
    colors = ["#4daf4a" if ok else "#e41a1c" for ok in feasible]
    ax3.bar(bins, [1.0 if ok else 0.0 for ok in feasible], color=colors, width=0.8)
    if tau_float is not None:
        ax3.axvline(tau_float, ls="-.", lw=1.5, color="#377eb8")
    ax3.set_ylim(-0.05, 1.15)
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(["Not feasible", "Feasible"])
    ax3.set_xlabel("Difficulty Bin d")
    ax3.set_ylabel("Feasible")
    ax3.set_title(f"Y3 Feasible Bins | {task} | {model} | seed={seed} | {tau_source}")
    ax3.grid(axis="y", alpha=0.25)
    fig3.tight_layout()
    fig3.savefig(out_dir / f"figure_Y3_feasible_bins__{tag}.png", dpi=200)
    plt.close(fig3)

    # Y4
    fig4, ax4 = plt.subplots(figsize=(7.2, 4.8))
    ax4.bar(bins, cov_vals, width=0.8, color="#80b1d3")
    ax4.axhline(0.70, ls="--", lw=1.5, color="#e41a1c")
    if tau_float is not None:
        ax4.axvline(tau_float, ls="-.", lw=1.5, color="#377eb8")
    ax4.set_ylim(0.0, 1.05)
    ax4.set_xlabel("Difficulty Bin d")
    ax4.set_ylabel("Coverage Cov_d")
    ax4.set_title(f"Y4 Coverage by Bin | {task} | {model} | seed={seed}")
    ax4.grid(axis="y", alpha=0.25)
    fig4.tight_layout()
    fig4.savefig(out_dir / f"figure_Y4_coverage_bins__{tag}.png", dpi=200)
    plt.close(fig4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Y1-Y4 auxiliary dynamic validation figures.")
    parser.add_argument("--report-json", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_evaluation_report.json")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--output-dir", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/figures_aux_validation")
    parser.add_argument("--score-source", choices=["bin", "score"], default="bin")
    parser.add_argument("--cap-static", type=float, default=0.65)
    parser.add_argument("--risk-static", type=float, default=0.30)
    parser.add_argument("--task", default="", help="Optional exact task filter")
    parser.add_argument("--model", default="", help="Optional exact model filter")
    parser.add_argument("--seed", type=int, default=-1, help="Optional seed filter (default: all)")
    parser.add_argument("--limit", type=int, default=0, help="Optional max runs to render (0 = all)")
    args = parser.parse_args()

    report_path = Path(args.report_json).resolve()
    splits_root = Path(args.splits_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    runs = payload.get("runs", [])

    rendered = 0
    skipped = 0
    for run in runs:
        task = str(run.get("task", ""))
        model = str(run.get("model", ""))
        seed = run.get("seed")
        if args.task and task != args.task:
            continue
        if args.model and model != args.model:
            continue
        if args.seed >= 0 and int(seed) != int(args.seed):
            continue
        if args.limit > 0 and rendered >= args.limit:
            break

        artifact_path = Path(str(run.get("artifact_path", "")))
        if not artifact_path.exists():
            skipped += 1
            continue

        try:
            task_a, model_a, seed_a, samples, scores = _build_samples_and_scores(
                artifact_path=artifact_path,
                splits_root=splits_root,
                score_source=str(args.score_source),
            )
            result = run_validation(
                val_samples=samples,
                scores=scores,
                task=task_a,
                cap_static=float(args.cap_static),
                risk_static=float(args.risk_static),
            )
            metrics, _, _ = compute_per_sample_metrics(samples, scores, task_a)
            cap_curve, risk_curve, coverage_by_bin = build_difficulty_curves(metrics, n_bins=10)

            _plot_figures_for_run(
                out_dir=out_dir,
                task=task_a,
                model=model_a,
                seed=seed_a,
                cap_curve=cap_curve,
                risk_curve=risk_curve,
                coverage_by_bin=coverage_by_bin,
                cap_dyn=float(result.get("cap_dynamic", 0.0)),
                risk_dyn=float(result.get("risk_dynamic", 1.0)),
                selected_tau=result.get("selected_tau"),
                tau_source=str(result.get("tau_source", "")),
            )
            rendered += 1
        except Exception as exc:
            skipped += 1
            print(f"[warn] skipped {task}/{model}/seed={seed}: {exc}", file=sys.stderr)

    print(f"Wrote figures to: {out_dir}")
    print(f"Rendered runs: {rendered}")
    print(f"Skipped runs: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
