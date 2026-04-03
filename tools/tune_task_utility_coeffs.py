from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS = ROOT / "model_runs"
OUT = MODEL_RUNS / "benchmarking" / "configs" / "task_utility_coeffs.json"


def _task_records() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for task_dir in sorted(p for p in MODEL_RUNS.iterdir() if p.is_dir()):
        tpath = task_dir / "sddf" / "thresholds.json"
        if not tpath.exists():
            continue
        payload = json.loads(tpath.read_text(encoding="utf-8"))
        task = str(payload.get("task") or task_dir.name)
        items: list[dict[str, Any]] = []
        for model_key, model_payload in (payload.get("thresholds") or {}).items():
            tau_u = model_payload.get("tau_utility_selection") or {}
            cands = list(tau_u.get("candidates") or [])
            n_val = float(model_payload.get("val_threshold_row_count") or 0)
            if cands:
                items.append(
                    {
                        "model_key": model_key,
                        "weight": max(1.0, n_val),
                        "candidates": cands,
                    }
                )
        if items:
            out[task] = items
    return out


def _best_for_task(items: list[dict[str, Any]]) -> dict[str, Any]:
    alphas = [0.5, 1.0, 1.5, 2.0]
    betas = [0.0, 0.25, 0.5, 0.75]
    gammas = [0.5, 1.0, 1.5, 2.0, 2.5]
    best: dict[str, Any] | None = None
    for a, b, g in product(alphas, betas, gammas):
        total_u = 0.0
        total_w = 0.0
        hard_fail = 0
        feasible_pairs = 0
        for item in items:
            best_c_u = None
            for c in item["candidates"]:
                if not bool(c.get("feasible", False)):
                    continue
                cov = float(c.get("coverage", 0.0))
                cap = float(c.get("selected_capability", 0.0))
                risk = float(c.get("selected_risk", 1.0))
                u = a * cov + b * cap - g * risk
                if best_c_u is None or u > best_c_u:
                    best_c_u = u
            if best_c_u is None:
                hard_fail += 1
                continue
            w = float(item["weight"])
            total_w += w
            total_u += best_c_u * w
            feasible_pairs += 1
        avg_u = total_u / max(1.0, total_w)
        score = avg_u - 0.25 * float(hard_fail)
        cur = {
            "alpha": float(a),
            "beta": float(b),
            "gamma": float(g),
            "avg_weighted_utility": float(avg_u),
            "feasible_pairs": int(feasible_pairs),
            "total_pairs": int(len(items)),
            "hard_fail_pairs": int(hard_fail),
            "score": float(score),
        }
        if best is None or cur["score"] > best["score"]:
            best = cur
    return best or {
        "alpha": 1.0,
        "beta": 0.25,
        "gamma": 1.0,
        "avg_weighted_utility": 0.0,
        "feasible_pairs": 0,
        "total_pairs": len(items),
        "hard_fail_pairs": len(items),
        "score": -1e9,
    }


def main() -> None:
    task_records = _task_records()
    tasks_out: dict[str, Any] = {}
    for task, items in task_records.items():
        tasks_out[task] = _best_for_task(items)
    payload = {
        "source": "validation_tau_candidate_grid_search",
        "grid": {
            "alpha": [0.5, 1.0, 1.5, 2.0],
            "beta": [0.0, 0.25, 0.5, 0.75],
            "gamma": [0.5, 1.0, 1.5, 2.0, 2.5],
        },
        "tasks": tasks_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT}")
    print(f"Tasks: {len(tasks_out)}")


if __name__ == "__main__":
    main()
