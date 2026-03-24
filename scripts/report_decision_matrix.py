#!/usr/bin/env python3
"""
Generate decision matrices and failure taxonomy tables from a Phase 0 analysis JSON.

Inputs:
  --analysis  Path to analysis JSON (the one saved by Phase 0 / ProductionRouter.export_to_json)
  --outdir    Directory to write CSVs (default: reports/)

Outputs:
  - decision_matrix.csv               (task, model, tau_cap, tau_risk, avg_capability, avg_risk, zone)
  - capability_risk_{task}.csv        (model, bin_id, capability, risk, weighted_risk)
  - failure_taxonomy_{task}_{model}.csv (bin-level failure counts by severity/type if available)
"""

import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def load_analysis(path: Path):
    with path.open() as f:
        data = json.load(f)
    return data.get("analyses", [])


def decision_matrix(records):
    rows = []
    for rec in records:
        cap_curve = rec.get("capability_curve", {}) or {}
        risk_curve = rec.get("risk_curve", {}) or {}
        cap_vals = [v for v in cap_curve.values() if v is not None]
        risk_vals = [v for v in risk_curve.values() if v is not None]
        rows.append({
            "task": rec.get("task"),
            "model": rec.get("model"),
            "tau_cap": rec.get("tau_cap"),
            "tau_risk": rec.get("tau_risk"),
            "avg_capability": mean(cap_vals) if cap_vals else "",
            "avg_risk": mean(risk_vals) if risk_vals else "",
            "zone": rec.get("zone"),
        })
    return rows


def capability_risk_tables(records):
    tables = {}  # task -> list of rows
    for rec in records:
        task = rec.get("task")
        model = rec.get("model")
        cap_curve = rec.get("capability_curve", {}) or {}
        risk_curve = rec.get("risk_curve", {}) or {}
        weighted = rec.get("weighted_risks") or {}
        for bin_id in sorted({*map(int, cap_curve.keys()), *map(int, risk_curve.keys())}):
            tables.setdefault(task, []).append({
                "model": model,
                "bin_id": bin_id,
                "capability": cap_curve.get(str(bin_id), cap_curve.get(bin_id)),
                "risk": risk_curve.get(str(bin_id), risk_curve.get(bin_id)),
                "weighted_risk": weighted.get(str(bin_id), weighted.get(bin_id)),
            })
    return tables


def failure_taxonomy_tables(records):
    tables = {}  # (task, model) -> list rows
    for rec in records:
        task = rec.get("task")
        model = rec.get("model")
        fa = rec.get("failure_analysis")
        if not fa:
            continue
        rows = []
        for bin_id, stats in fa.items():
            by_sev = stats.get("by_severity", {})
            rows.append({
                "bin_id": bin_id,
                "total": stats.get("total"),
                "failures": stats.get("failures"),
                "failure_rate": stats.get("failure_rate"),
                "critical": by_sev.get("critical", 0),
                "high": by_sev.get("high", 0),
                "medium": by_sev.get("medium", 0),
                "low": by_sev.get("low", 0),
            })
        tables[(task, model)] = rows
    return tables


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True, help="Path to analysis JSON")
    ap.add_argument("--outdir", default="reports", help="Output directory for CSVs")
    args = ap.parse_args()

    records = load_analysis(Path(args.analysis))
    outdir = Path(args.outdir)

    # Decision matrix
    dm_rows = decision_matrix(records)
    write_csv(outdir / "decision_matrix.csv", dm_rows,
              ["task", "model", "tau_cap", "tau_risk", "avg_capability", "avg_risk", "zone"])

    # Capability/risk per task
    cap_tables = capability_risk_tables(records)
    for task, rows in cap_tables.items():
        write_csv(outdir / f"capability_risk_{task}.csv", rows,
                  ["model", "bin_id", "capability", "risk", "weighted_risk"])

    # Failure taxonomy per task/model
    ft_tables = failure_taxonomy_tables(records)
    for (task, model), rows in ft_tables.items():
        safe_model = model.replace("/", "_").replace(":", "_")
        write_csv(outdir / f"failure_taxonomy_{task}_{safe_model}.csv", rows,
                  ["bin_id", "total", "failures", "failure_rate", "critical", "high", "medium", "low"])


if __name__ == "__main__":
    main()
