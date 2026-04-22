from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS = ROOT / "model_runs"
OUT_DIR = MODEL_RUNS / "benchmarking" / "error_taxonomy"


FAILURE_HARM: dict[str, tuple[float, float]] = {
    "arithmetic_error": (0.9, 0.8),
    "wrong_label": (0.8, 0.8),
    "logic_error": (0.95, 0.85),
    "answer_mismatch": (0.85, 0.8),
    "low_relevance": (0.6, 0.7),
    "constraint_violation": (0.7, 0.7),
    "quality_failure": (0.5, 0.6),
    "format_error": (0.4, 0.4),
    "missing_field": (0.45, 0.45),
    "incomplete_output": (0.4, 0.35),
    "no_answer": (0.2, 0.2),
    "empty_output": (0.1, 0.1),
    "timeout_runtime": (0.1, 0.1),
    "missing_ground_truth": (0.3, 0.3),
}


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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "error_taxonomy_by_task_model.json"
    csv_path = OUT_DIR / "error_taxonomy_by_task_model.csv"
    md_path = OUT_DIR / "error_taxonomy_by_task_model.md"

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for task_dir in sorted(p for p in MODEL_RUNS.iterdir() if p.is_dir()):
        canonical = task_dir / "sddf" / "canonical_rows.jsonl"
        if not canonical.exists():
            continue
        for row in _load_jsonl(canonical):
            task = str(task_dir.name)
            model = str(row.get("model_name") or "unknown_model")
            grouped[(task, model)].append(row)

    out_rows: list[dict[str, Any]] = []
    for (task, model), rows in sorted(grouped.items()):
        n = len(rows)
        failures = [str(r.get("failure_type") or "") for r in rows if str(r.get("failure_type") or "").strip()]
        failure_counts = Counter(failures)
        total_fail = sum(failure_counts.values())
        avg_risk = sum(_safe_float(r.get("actual_semantic_risk"), 0.0) for r in rows) / max(1, n)

        # Harm profile from taxonomy map (severity * undetectability).
        weighted_harm = 0.0
        for failure, count in failure_counts.items():
            sev, und = FAILURE_HARM.get(failure, (0.6, 0.6))
            weighted_harm += float(count) * float(sev) * float(und)
        avg_failure_harm = weighted_harm / max(1, total_fail)

        top_failures = [
            {"failure_type": ft, "count": int(c), "rate_over_all_rows": float(c / max(1, n))}
            for ft, c in failure_counts.most_common(5)
        ]
        out_rows.append(
            {
                "task": task,
                "model_name": model,
                "n_rows": int(n),
                "n_failures": int(total_fail),
                "failure_rate": float(total_fail / max(1, n)),
                "avg_semantic_risk": float(avg_risk),
                "avg_failure_harm": float(avg_failure_harm),
                "failure_counts": {k: int(v) for k, v in sorted(failure_counts.items())},
                "top_failures": top_failures,
            }
        )

    payload = {"failure_harm_map": FAILURE_HARM, "rows": out_rows}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    headers = [
        "task",
        "model_name",
        "n_rows",
        "n_failures",
        "failure_rate",
        "avg_semantic_risk",
        "avg_failure_harm",
        "top_failure_1",
        "top_failure_1_count",
        "top_failure_2",
        "top_failure_2_count",
        "top_failure_3",
        "top_failure_3_count",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in out_rows:
            top = list(row["top_failures"])
            while len(top) < 3:
                top.append({"failure_type": "", "count": 0})
            writer.writerow(
                {
                    "task": row["task"],
                    "model_name": row["model_name"],
                    "n_rows": row["n_rows"],
                    "n_failures": row["n_failures"],
                    "failure_rate": row["failure_rate"],
                    "avg_semantic_risk": row["avg_semantic_risk"],
                    "avg_failure_harm": row["avg_failure_harm"],
                    "top_failure_1": top[0]["failure_type"],
                    "top_failure_1_count": top[0]["count"],
                    "top_failure_2": top[1]["failure_type"],
                    "top_failure_2_count": top[1]["count"],
                    "top_failure_3": top[2]["failure_type"],
                    "top_failure_3_count": top[2]["count"],
                }
            )

    lines = [
        "# Error Taxonomy by Task and Model",
        "",
        "| Task | Model | N | Failure Rate | Avg Semantic Risk | Avg Failure Harm | Top Failure (count) |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in out_rows:
        top = row["top_failures"][0] if row["top_failures"] else {"failure_type": "none", "count": 0}
        lines.append(
            f"| {row['task']} | {row['model_name']} | {row['n_rows']} | {row['failure_rate']:.3f} | "
            f"{row['avg_semantic_risk']:.3f} | {row['avg_failure_harm']:.3f} | "
            f"{top['failure_type']} ({top['count']}) |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {md_path}")
    print(f"Rows: {len(out_rows)}")


if __name__ == "__main__":
    main()
