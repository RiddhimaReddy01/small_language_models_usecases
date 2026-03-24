from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def summarize_task(task_dir: Path) -> dict:
    summary = {
        "task": task_dir.name,
        "capability_metrics": [],
        "operational_metrics": [],
        "risk_notes": {},
        "errors": [],
    }
    part_a = task_dir / "results" / "reports" / "part_a_summary.json"
    part_b = task_dir / "results" / "reports" / "part_b_summary.json"
    try:
        if part_a.exists():
            data = load_json(part_a)
            if isinstance(data, list):
                data = next(
                    (entry for entry in data if isinstance(entry, dict) and "metrics" in entry),
                    data[0] if data else {},
                )
            capability = data.get("metrics", {}).get("capability", {}) if isinstance(data, dict) else {}
            for dataset, stats in capability.items():
                summary["capability_metrics"].append({"dataset": dataset, "values": stats})
            summary["operational_metrics"] = data.get("metrics", {}).get("operational", [])
        else:
            summary["capability_metrics"].append({"dataset": "missing", "values": None})
        if part_b.exists():
            summary["risk_notes"] = load_json(part_b).get("statuses", {})
        else:
            summary["risk_notes"] = {"missing": "No SDDF reports generated"}
    except Exception as exc:
        summary["errors"].append(str(exc))

    return summary


def main() -> int:
    root = Path("tasks")
    if not root.exists():
        print("No tasks directory found.")
        return 1

    report = []
    for task_dir in sorted(root.iterdir()):
        if not task_dir.is_dir():
            continue
        report.append(summarize_task(task_dir))

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
