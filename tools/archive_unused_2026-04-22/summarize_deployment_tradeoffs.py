from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS = ROOT / "model_runs"
OUT_DIR = MODEL_RUNS / "benchmarking" / "deployment"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize deployment tradeoffs (cost/latency/safety) from canonical rows.")
    parser.add_argument("--cost-slm", type=float, default=1.0)
    parser.add_argument("--cost-hybrid", type=float, default=2.5)
    parser.add_argument("--cost-baseline", type=float, default=6.0)
    parser.add_argument("--safety-risk-threshold", type=float, default=0.20)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "deployment_tradeoffs.json"
    csv_path = OUT_DIR / "deployment_tradeoffs.csv"
    md_path = OUT_DIR / "deployment_tradeoffs.md"

    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for task_dir in sorted(p for p in MODEL_RUNS.iterdir() if p.is_dir()):
        canonical = task_dir / "sddf" / "canonical_rows.jsonl"
        if not canonical.exists():
            continue
        for row in _load_jsonl(canonical):
            key = (task_dir.name, str(row.get("model_name") or "unknown_model"))
            rows_by_key[key].append(row)

    out_rows: list[dict[str, Any]] = []
    for (task, model), rows in sorted(rows_by_key.items()):
        n = len(rows)
        if n == 0:
            continue
        slm = 0
        hyb = 0
        base = 0
        total_cost = 0.0
        total_latency = 0.0
        total_risk = 0.0
        total_cap = 0.0
        unsafe = 0
        for row in rows:
            route = str(row.get("predicted_route_state") or "").upper()
            if route == "SLM":
                slm += 1
                total_cost += float(args.cost_slm)
            elif route == "HYBRID_ABSTAIN":
                hyb += 1
                total_cost += float(args.cost_hybrid)
            else:
                base += 1
                total_cost += float(args.cost_baseline)
            lat = _safe_float(row.get("latency_sec"), 0.0)
            risk = _safe_float(row.get("actual_semantic_risk"), 1.0)
            cap = _safe_float(row.get("actual_capability"), 0.0)
            total_latency += lat
            total_risk += risk
            total_cap += cap
            if risk > float(args.safety_risk_threshold):
                unsafe += 1
        avg_cost = total_cost / n
        avg_latency = total_latency / n
        avg_risk = total_risk / n
        avg_cap = total_cap / n
        unsafe_rate = unsafe / n
        out_rows.append(
            {
                "task": task,
                "model_name": model,
                "n_rows": n,
                "route_share_slm": slm / n,
                "route_share_hybrid": hyb / n,
                "route_share_baseline": base / n,
                "avg_cost_units": avg_cost,
                "avg_latency_sec": avg_latency,
                "avg_semantic_risk": avg_risk,
                "avg_capability": avg_cap,
                "unsafe_rate": unsafe_rate,
            }
        )

    payload = {
        "cost_assumptions": {
            "slm": float(args.cost_slm),
            "hybrid": float(args.cost_hybrid),
            "baseline": float(args.cost_baseline),
            "safety_risk_threshold": float(args.safety_risk_threshold),
        },
        "rows": out_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    headers = list(out_rows[0].keys()) if out_rows else [
        "task", "model_name", "n_rows", "route_share_slm", "route_share_hybrid",
        "route_share_baseline", "avg_cost_units", "avg_latency_sec",
        "avg_semantic_risk", "avg_capability", "unsafe_rate",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        "# Deployment Tradeoffs (Separate from Train/Val/Test)",
        "",
        "| Task | Model | N | SLM% | HYBRID% | BASELINE% | Avg Cost | Avg Latency(s) | Avg Risk | Avg Capability | Unsafe Rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in out_rows:
        lines.append(
            f"| {row['task']} | {row['model_name']} | {row['n_rows']} | "
            f"{row['route_share_slm']:.3f} | {row['route_share_hybrid']:.3f} | {row['route_share_baseline']:.3f} | "
            f"{row['avg_cost_units']:.3f} | {row['avg_latency_sec']:.3f} | {row['avg_semantic_risk']:.3f} | "
            f"{row['avg_capability']:.3f} | {row['unsafe_rate']:.3f} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {md_path}")
    print(f"Rows: {len(out_rows)}")


if __name__ == "__main__":
    main()
