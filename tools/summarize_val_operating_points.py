from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS = ROOT / "model_runs"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    rows: list[dict[str, Any]] = []
    for task_dir in sorted(p for p in MODEL_RUNS.iterdir() if p.is_dir()):
        thresholds_path = task_dir / "sddf" / "thresholds.json"
        if not thresholds_path.exists():
            continue
        payload = json.loads(thresholds_path.read_text(encoding="utf-8"))
        task = str(payload.get("task") or task_dir.name)
        cap_threshold = _safe_float(payload.get("policy_capability_threshold"))
        risk_threshold = _safe_float(payload.get("policy_risk_threshold"))
        threshold_method = str(payload.get("threshold_method") or "")

        for model_key, model_payload in (payload.get("thresholds") or {}).items():
            tau_utility = model_payload.get("tau_utility_selection") or {}
            row = {
                "task": task,
                "model_key": model_key,
                "display_name": model_payload.get("display_name"),
                "threshold_method": threshold_method,
                "capability_threshold": cap_threshold,
                "risk_threshold": risk_threshold,
                "tau_star_difficulty": _safe_float(model_payload.get("tau_star_difficulty")),
                "threshold_split": model_payload.get("threshold_split"),
                "curve_fit_level": model_payload.get("curve_fit_level"),
                "matched_query_count": int(model_payload.get("matched_query_count") or 0),
                "val_threshold_row_count": int(model_payload.get("val_threshold_row_count") or 0),
                "utility_feasible": bool(tau_utility.get("feasible", False)),
                "utility_tau": _safe_float(tau_utility.get("tau")),
                "utility_coverage": _safe_float(tau_utility.get("coverage")),
                "utility_selected_capability": _safe_float(tau_utility.get("selected_capability")),
                "utility_selected_risk": _safe_float(tau_utility.get("selected_risk")),
                "utility_value": _safe_float(tau_utility.get("utility")),
            }
            rows.append(row)

    out_dir = MODEL_RUNS / "benchmarking"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_out = out_dir / "val_operating_points.json"
    csv_out = out_dir / "val_operating_points.csv"
    md_out = out_dir / "val_operating_points.md"

    json_out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    if rows:
        headers = list(rows[0].keys())
        with csv_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Validation Operating Sweet Spots",
            "",
            "| Task | Model | Tau | Feasible | Coverage | Capability | Risk | Utility |",
            "|---|---|---:|:---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            tau = "NA" if row["utility_tau"] is None else f"{row['utility_tau']:.4f}"
            cov = "NA" if row["utility_coverage"] is None else f"{row['utility_coverage']:.4f}"
            cap = "NA" if row["utility_selected_capability"] is None else f"{row['utility_selected_capability']:.4f}"
            risk = "NA" if row["utility_selected_risk"] is None else f"{row['utility_selected_risk']:.4f}"
            util = "NA" if row["utility_value"] is None else f"{row['utility_value']:.4f}"
            feas = "yes" if row["utility_feasible"] else "no"
            lines.append(
                f"| {row['task']} | {row['display_name'] or row['model_key']} | {tau} | {feas} | {cov} | {cap} | {risk} | {util} |"
            )
        md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        csv_out.write_text("", encoding="utf-8")
        md_out.write_text("# Validation Operating Sweet Spots\n\nNo rows found.\n", encoding="utf-8")

    print(f"Wrote: {json_out}")
    print(f"Wrote: {csv_out}")
    print(f"Wrote: {md_out}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()

