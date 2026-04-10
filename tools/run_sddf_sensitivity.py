from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
PHASE_REPORTS = ROOT / "model_runs" / "benchmarking" / "phase_reports"
OUT_DIR = ROOT / "model_runs" / "benchmarking" / "sensitivity"


@dataclass
class SweepConfig:
    cap_threshold: float
    risk_threshold: float
    min_samples: int
    utility_alpha: float
    utility_beta: float
    utility_gamma: float
    tau_bootstrap_draws: int
    tau_conservative_percentile: float


def _parse_float_grid(raw: str) -> list[float]:
    vals = []
    for token in (raw or "").split(","):
        token = token.strip()
        if token:
            vals.append(float(token))
    return vals


def _parse_int_grid(raw: str) -> list[int]:
    vals = []
    for token in (raw or "").split(","):
        token = token.strip()
        if token:
            vals.append(int(token))
    return vals


def _run(cmd: list[str], dry_run: bool) -> None:
    print("[RUN]", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _read_phase_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _summarize(rows: list[dict[str, str]]) -> dict[str, float]:
    if not rows:
        return {
            "n_task_model_rows": 0.0,
            "pass_rate": 0.0,
            "avg_precision": 0.0,
            "avg_recall": 0.0,
            "avg_f1": 0.0,
            "avg_accuracy": 0.0,
            "avg_coverage_slm": 0.0,
            "avg_delta_utility_vs_always_slm": 0.0,
            "avg_mcnemar_p_holm": 1.0,
        }
    def _f(row: dict[str, str], key: str, default: float = 0.0) -> float:
        try:
            return float(row.get(key, default))
        except (TypeError, ValueError):
            return default

    n = len(rows)
    pass_rate = sum(1 for r in rows if str(r.get("pass_operating_gate", "")).lower() in {"true", "1", "yes"}) / n
    holm_vals = [_f(r, "mcnemar_p_policy_vs_always_slm_holm", 1.0) for r in rows]
    return {
        "n_task_model_rows": float(n),
        "pass_rate": float(pass_rate),
        "avg_precision": float(mean(_f(r, "precision", 0.0) for r in rows)),
        "avg_recall": float(mean(_f(r, "recall", 0.0) for r in rows)),
        "avg_f1": float(mean(_f(r, "f1", 0.0) for r in rows)),
        "avg_accuracy": float(mean(_f(r, "accuracy", 0.0) for r in rows)),
        "avg_coverage_slm": float(mean(_f(r, "coverage_slm", 0.0) for r in rows)),
        "avg_delta_utility_vs_always_slm": float(mean(_f(r, "delta_utility_vs_always_slm", 0.0) for r in rows)),
        "avg_mcnemar_p_holm": float(mean(holm_vals)) if holm_vals else 1.0,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Run SDDF ablations/sensitivity sweeps and aggregate phase metrics.")
    p.add_argument("--report-split", type=str, default="test", choices=["val", "test"])
    p.add_argument("--cap-grid", type=str, default="0.75,0.80,0.85")
    p.add_argument("--risk-grid", type=str, default="0.15,0.20,0.25")
    p.add_argument("--min-samples-grid", type=str, default="5,10")
    p.add_argument("--alpha-grid", type=str, default="0.5,1.0,1.5")
    p.add_argument("--beta-grid", type=str, default="0.0,0.25,0.5")
    p.add_argument("--gamma-grid", type=str, default="0.5,1.0,1.5")
    p.add_argument("--tau-bootstrap-grid", type=str, default="100,200,400")
    p.add_argument("--tau-percentile-grid", type=str, default="5,10,20")
    p.add_argument("--limit", type=int, default=0, help="Optional cap on number of configurations (0 = all).")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    cap_grid = _parse_float_grid(args.cap_grid)
    risk_grid = _parse_float_grid(args.risk_grid)
    min_samples_grid = _parse_int_grid(args.min_samples_grid)
    alpha_grid = _parse_float_grid(args.alpha_grid)
    beta_grid = _parse_float_grid(args.beta_grid)
    gamma_grid = _parse_float_grid(args.gamma_grid)
    tau_bootstrap_grid = _parse_int_grid(args.tau_bootstrap_grid)
    tau_percentile_grid = _parse_float_grid(args.tau_percentile_grid)

    configs: list[SweepConfig] = []
    for cap in cap_grid:
        for risk in risk_grid:
            for min_samples in min_samples_grid:
                for a in alpha_grid:
                    for b in beta_grid:
                        for g in gamma_grid:
                            for bdraw in tau_bootstrap_grid:
                                for pct in tau_percentile_grid:
                                    configs.append(
                                        SweepConfig(
                                            cap_threshold=float(cap),
                                            risk_threshold=float(risk),
                                            min_samples=int(min_samples),
                                            utility_alpha=float(a),
                                            utility_beta=float(b),
                                            utility_gamma=float(g),
                                            tau_bootstrap_draws=int(bdraw),
                                            tau_conservative_percentile=float(pct),
                                        )
                                    )
    if int(args.limit) > 0:
        configs = configs[: int(args.limit)]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    rows_out: list[dict[str, float | str | int]] = []

    for idx, cfg in enumerate(configs, start=1):
        stem = (
            f"{args.report_split}_sensitivity_{idx:03d}"
            f"_cap{cfg.cap_threshold:.2f}_risk{cfg.risk_threshold:.2f}"
            f"_min{cfg.min_samples}_a{cfg.utility_alpha:.2f}_b{cfg.utility_beta:.2f}_g{cfg.utility_gamma:.2f}"
            f"_boot{cfg.tau_bootstrap_draws}_p{cfg.tau_conservative_percentile:.0f}"
        ).replace(".", "p")

        run_sddf = [
            py, str(ROOT / "tools" / "run_sddf_pipeline.py"),
            "--report-split", args.report_split,
            "--skip-dashboard",
            "--skip-summary",
            "--cap-threshold", str(cfg.cap_threshold),
            "--risk-threshold", str(cfg.risk_threshold),
            "--min-samples", str(cfg.min_samples),
            "--utility-alpha", str(cfg.utility_alpha),
            "--utility-beta", str(cfg.utility_beta),
            "--utility-gamma", str(cfg.utility_gamma),
            "--tau-bootstrap-draws", str(cfg.tau_bootstrap_draws),
            "--tau-conservative-percentile", str(cfg.tau_conservative_percentile),
        ]
        eval_phase = [
            py, str(ROOT / "tools" / "evaluate_test_phase.py"),
            "--utility-alpha", str(cfg.utility_alpha),
            "--utility-beta", str(cfg.utility_beta),
            "--utility-gamma", str(cfg.utility_gamma),
            "--output-stem", stem,
            "--strict-leakage",
        ]

        _run(run_sddf, dry_run=args.dry_run)
        _run(eval_phase, dry_run=args.dry_run)

        if args.dry_run:
            continue

        phase_csv = PHASE_REPORTS / f"{stem}.csv"
        summary = _summarize(_read_phase_csv(phase_csv))
        rows_out.append(
            {
                "config_id": idx,
                "report_split": args.report_split,
                "cap_threshold": cfg.cap_threshold,
                "risk_threshold": cfg.risk_threshold,
                "min_samples": cfg.min_samples,
                "utility_alpha": cfg.utility_alpha,
                "utility_beta": cfg.utility_beta,
                "utility_gamma": cfg.utility_gamma,
                "tau_bootstrap_draws": cfg.tau_bootstrap_draws,
                "tau_conservative_percentile": cfg.tau_conservative_percentile,
                **summary,
                "phase_csv": str(phase_csv.relative_to(ROOT)),
            }
        )

    if args.dry_run:
        print(f"[DRY-RUN] Planned configurations: {len(configs)}")
        return

    out_json = OUT_DIR / f"{args.report_split}_sensitivity_summary.json"
    out_csv = OUT_DIR / f"{args.report_split}_sensitivity_summary.csv"
    out_json.write_text(json.dumps(rows_out, indent=2), encoding="utf-8")
    if rows_out:
        headers = list(rows_out[0].keys())
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            w.writerows(rows_out)
    else:
        out_csv.write_text("", encoding="utf-8")
    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    main()
