from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_RUNS_DIR = ROOT / "model runs"
SOURCE_PATH = MODEL_RUNS_DIR / "task_model_runs_table.json"
SDDF_PATH = MODEL_RUNS_DIR / "SDDF_FRAMEWORK_TABLE.md"
DECISION_PATH = MODEL_RUNS_DIR / "DECISION_MATRIX_TABLE.md"
PARETO_PATH = MODEL_RUNS_DIR / "PARETO_TABLE.md"
JSON_PATH = MODEL_RUNS_DIR / "downstream_views.json"


def load_source() -> dict[str, Any]:
    return json.loads(SOURCE_PATH.read_text(encoding="utf-8"))


def fmt_num(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.2f}"
        if abs(value) >= 1:
            return f"{value:.3f}"
        return f"{value:.3f}"
    return str(value)


def capability_summary(task: dict[str, Any]) -> str:
    snap = task["capability_snapshot"]
    items = [f"{k}={fmt_num(v)}" for k, v in snap.items()]
    return "; ".join(items)


def operational_summary(task: dict[str, Any]) -> str:
    snap = task["operational_snapshot"]
    items = [f"{k}={fmt_num(v)}" for k, v in snap.items()]
    return "; ".join(items)


def decision_status(task: dict[str, Any]) -> str:
    slots = [task["slm_0"], task["slm_1"], task["slm_2"], task["baseline"]]
    missing = sum(1 for slot in slots if not slot.get("nearest_archived_evidence") and not slot.get("nearest_checked_out_numeric_snapshot"))
    if missing >= 2:
        return "partial"
    return "evidence-backed"


def build_sddf_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# SDDF Framework Table",
        "",
        "This table shows how the canonical model ladder feeds into the SDDF framework for each task.",
        "",
        "| Task | Candidate order | Capability evidence | Operational evidence | SDDF status |",
        "| --- | --- | --- | --- | --- |",
    ]
    order = "`SLM-0 -> SLM-1 -> SLM-2 -> BASELINE`"
    for task in data["tasks"]:
        lines.append(
            f"| `{task['task']}` | {order} | {capability_summary(task)} | {operational_summary(task)} | {decision_status(task)} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- capability metrics become the task-specific success curves used in SDDF binning and `tau_cap` estimation",
            "- operational metrics become the latency/cost/reliability side of SDDF and downstream routing tradeoffs",
            "- partial rows mean the canonical slot exists, but the exact archived model run is missing from the checked-out repo",
        ]
    )
    return "\n".join(lines) + "\n"


def build_decision_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Decision Matrix Table",
        "",
        "This table pushes the canonical ladder downstream into the routing decision view.",
        "",
        "| Task | Smallest candidate order | Risk gate | Capability gate | Decision input status | Routing note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for task in data["tasks"]:
        status = decision_status(task)
        capability = capability_summary(task)
        operational = operational_summary(task)
        note = (
            "Use `tau_risk` first, then `tau_cap`, with refreshed exact-slot runs recommended."
            if status == "partial"
            else "Sufficient archived evidence to compare ladder tiers before baseline escalation."
        )
        lines.append(
            f"| `{task['task']}` | `SLM-0 -> SLM-1 -> SLM-2 -> BASELINE` | {operational} | {capability} | {status} | {note} |"
        )
    return "\n".join(lines) + "\n"


def build_pareto_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Pareto Table",
        "",
        "This table carries the canonical ladder into a cost/latency/capability comparison view.",
        "",
        "| Task | Tier | Evidence | Capability snapshot | Operational snapshot | Pareto note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for task in data["tasks"]:
        cap = capability_summary(task)
        op = operational_summary(task)
        tiers = [
            ("SLM-0", task["slm_0"]),
            ("SLM-1", task["slm_1"]),
            ("SLM-2", task["slm_2"]),
            ("BASELINE", task["baseline"]),
        ]
        for tier_name, tier in tiers:
            evidence = (
                tier.get("nearest_archived_evidence")
                or tier.get("nearest_checked_out_numeric_snapshot")
                or "canonical slot only"
            )
            if tier_name == "BASELINE":
                note = "Quality ceiling / escalation target."
            elif "canonical slot only" in evidence:
                note = "Refresh this tier for exact Pareto placement."
            else:
                note = "Use archived numbers as provisional Pareto point."
            lines.append(f"| `{task['task']}` | `{tier_name}` | {evidence} | {cap} | {op} | {note} |")
    return "\n".join(lines) + "\n"


def build_json(data: dict[str, Any]) -> dict[str, Any]:
    tasks = []
    for task in data["tasks"]:
        tasks.append(
            {
                "task": task["task"],
                "candidate_order": ["SLM-0", "SLM-1", "SLM-2", "BASELINE"],
                "decision_input_status": decision_status(task),
                "capability_snapshot": task["capability_snapshot"],
                "operational_snapshot": task["operational_snapshot"],
                "tiers": {
                    "SLM-0": task["slm_0"],
                    "SLM-1": task["slm_1"],
                    "SLM-2": task["slm_2"],
                    "BASELINE": task["baseline"],
                },
            }
        )
    return {"canonical_ladder": data["canonical_ladder"], "tasks": tasks}


def main() -> None:
    data = load_source()
    SDDF_PATH.write_text(build_sddf_markdown(data), encoding="utf-8")
    DECISION_PATH.write_text(build_decision_markdown(data), encoding="utf-8")
    PARETO_PATH.write_text(build_pareto_markdown(data), encoding="utf-8")
    JSON_PATH.write_text(json.dumps(build_json(data), indent=2), encoding="utf-8")
    print("Generated downstream SDDF/decision/Pareto views in 'model runs'.")


if __name__ == "__main__":
    main()
