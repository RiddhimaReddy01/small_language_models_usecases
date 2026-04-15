from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Export validation threshold-calibration tables.")
    parser.add_argument(
        "--report-json",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_threshold_calibration_report.json",
    )
    args = parser.parse_args()

    report_path = Path(args.report_json).resolve()
    out_dir = report_path.parent
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    runs = payload.get("runs", [])

    rows = sorted(runs, key=lambda x: (str(x.get("task", "")), str(x.get("model", "")), int(x.get("seed", -1))))

    # Calibration table Y (full)
    y_fields = [
        "task",
        "model",
        "seed",
        "selected_tau_score",
        "tau_source",
        "cap_dynamic",
        "risk_dynamic",
        "selected_capability",
        "selected_risk",
        "pass_cap_gate",
        "pass_risk_gate",
        "pass_calibration_gate",
        "tau_candidates_count",
        "feasible_tau_count",
        "feasible_tau_min",
        "feasible_tau_max",
        "artifact_path",
    ]
    _write_csv(out_dir / "tableY_threshold_calibration_full.csv", rows, y_fields)

    # Seed-42 compact view
    rows42 = [r for r in rows if int(r.get("seed", -1)) == 42]
    _write_csv(out_dir / "tableY_threshold_calibration_seed42.csv", rows42, y_fields)

    # Feasible tau summary
    y1_fields = [
        "task",
        "model",
        "seed",
        "selected_tau_score",
        "tau_source",
        "cap_dynamic",
        "risk_dynamic",
        "feasible_tau_count",
        "feasible_tau_min",
        "feasible_tau_max",
        "tau_candidates_count",
    ]
    _write_csv(out_dir / "tableYplus1_feasible_tau_summary_calibration.csv", rows, y1_fields)

    # Calibration gate status
    y2_fields = [
        "task",
        "model",
        "seed",
        "selected_tau_score",
        "tau_source",
        "selected_capability",
        "selected_risk",
        "cap_dynamic",
        "risk_dynamic",
        "pass_cap_gate",
        "pass_risk_gate",
        "pass_calibration_gate",
    ]
    _write_csv(out_dir / "tableYplus2_calibration_gate_status.csv", rows, y2_fields)

    summary_path = out_dir / "val_threshold_calibration_summary.txt"
    n_runs = len(rows)
    n_errors = len(payload.get("errors", []))
    n_pass = sum(1 for r in rows if bool(r.get("pass_calibration_gate")))
    unique_tau = sorted({float(r.get("selected_tau_score")) for r in rows if r.get("selected_tau_score") is not None})
    summary_path.write_text(
        "\n".join(
            [
                f"runs={n_runs}",
                f"errors={n_errors}",
                f"pass_calibration_gate={n_pass}",
                f"fail_calibration_gate={n_runs - n_pass}",
                f"selected_tau_score_unique_count={len(unique_tau)}",
                f"selected_tau_score_min={(min(unique_tau) if unique_tau else None)}",
                f"selected_tau_score_max={(max(unique_tau) if unique_tau else None)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote: {out_dir / 'tableY_threshold_calibration_full.csv'}")
    print(f"Wrote: {out_dir / 'tableY_threshold_calibration_seed42.csv'}")
    print(f"Wrote: {out_dir / 'tableYplus1_feasible_tau_summary_calibration.csv'}")
    print(f"Wrote: {out_dir / 'tableYplus2_calibration_gate_status.csv'}")
    print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

