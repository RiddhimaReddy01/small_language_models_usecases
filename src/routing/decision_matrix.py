from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


QUALITY_THRESHOLD = 0.85
RISK_THRESHOLD = 0.20
CAPABILITY_THRESHOLD = 0.95


@dataclass
class TaskDecisionMatrixRecord:
    task: str
    benchmark: str
    summary_path: str
    sddf_root: str
    slm_name: str
    slm_size_b: float | None
    llm_name: str
    llm_size_b: float | None
    size_order: list[str]
    matched_examples: int
    tau_risk: float | None
    tau_risk_bin: int | None
    tau_cap: float | None
    tau_cap_bin: int | None
    risk_gate_pass: bool
    capability_gate_pass: bool
    routing_policy: str
    binding_gate: str
    curve_plot_path: str | None


def _parse_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _resolve_sddf_root(summary_path: Path, sddf_root_text: str | None) -> Path:
    if sddf_root_text:
        candidate = Path(sddf_root_text)
        if (candidate / "canonical_rows.jsonl").exists():
            return candidate
        sibling_candidate = summary_path.parent.parent / candidate.name
        if (sibling_candidate / "canonical_rows.jsonl").exists():
            return sibling_candidate
        candidate_name = candidate.name
        for parent in summary_path.parents:
            if parent.name == candidate_name and (parent / "canonical_rows.jsonl").exists():
                return parent
    fallback = summary_path.parent.parent
    if (fallback / "canonical_rows.jsonl").exists():
        return fallback
    raise FileNotFoundError(
        f"Could not resolve SDDF root for {summary_path} from value {sddf_root_text!r}."
    )


def _infer_model_size_b(model_name: str) -> float | None:
    normalized = model_name.lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*b", normalized)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+(?:\.\d+)?)b", normalized)
    if match:
        return float(match.group(1))
    return None


def _sort_key(model_name: str) -> tuple[float, str]:
    size = _infer_model_size_b(model_name)
    return (size if size is not None else 10_000.0, model_name.lower())


def _latest_part_b_summary(task_root: Path) -> Path | None:
    candidates = [
        path for path in task_root.rglob("part_b_summary.json")
        if ".tmp_tests" not in str(path)
    ]
    if not candidates:
        return None
    valid_candidates: list[Path] = []
    for path in candidates:
        try:
            summary = _parse_json(path)
            _resolve_sddf_root(path, summary.get("sddf_root"))
            valid_candidates.append(path)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    if valid_candidates:
        return max(valid_candidates, key=lambda path: path.stat().st_mtime)
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _bucket_rows(rows: list[dict[str, Any]], model_name: str) -> list[dict[str, Any]]:
    buckets: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("model_name") != model_name:
            continue
        difficulty_bin = row.get("difficulty_bin")
        score = float(row.get("difficulty_score", 0.0) or 0.0)
        bucket_id = int(difficulty_bin) if difficulty_bin is not None else 0
        buckets.setdefault((bucket_id, score if difficulty_bin is None else 0.0), []).append(row)

    ordered = sorted(
        buckets.items(),
        key=lambda item: (
            item[0][0],
            sum(float(row.get("difficulty_score", 0.0) or 0.0) for row in item[1]) / max(1, len(item[1])),
        ),
    )
    records: list[dict[str, Any]] = []
    for index, ((bucket_id, _), bucket_rows) in enumerate(ordered):
        center = sum(float(row.get("difficulty_score", 0.0) or 0.0) for row in bucket_rows) / max(1, len(bucket_rows))
        records.append({"bucket_index": index, "difficulty_bin": bucket_id, "center": center, "rows": bucket_rows})
    return records


def _derive_tau_risk(rows: list[dict[str, Any]], slm_name: str) -> tuple[float | None, int | None]:
    buckets = _bucket_rows(rows, slm_name)
    tau_risk: float | None = None
    tau_risk_bin: int | None = None
    for bucket in buckets:
        acceptable = 0
        total = len(bucket["rows"])
        for row in bucket["rows"]:
            valid_output = int(row.get("valid_output", 0) or 0) == 1
            primary_metric = float(row.get("primary_metric", 0.0) or 0.0)
            if valid_output and primary_metric >= QUALITY_THRESHOLD:
                acceptable += 1
        risk = 1.0 - (acceptable / total if total else 0.0)
        if risk <= RISK_THRESHOLD:
            tau_risk = bucket["center"]
            tau_risk_bin = bucket["bucket_index"]
    return tau_risk, tau_risk_bin


def _derive_tau_cap(pair: dict[str, Any]) -> tuple[float | None, int | None]:
    tau_cap: float | None = None
    tau_cap_bin: int | None = None
    for zone in pair.get("zones", []):
        ratio = zone.get("ratio_smooth")
        if ratio is None:
            continue
        if float(ratio) >= CAPABILITY_THRESHOLD:
            tau_cap = float(zone.get("bin_center", 0.0) or 0.0)
            tau_cap_bin = int(zone.get("difficulty_bin", 0) or 0)
    return tau_cap, tau_cap_bin


def _build_policy(slm_name: str, llm_name: str, tau_risk: float | None, tau_cap: float | None) -> tuple[str, bool, bool, str]:
    risk_gate_pass = tau_risk is not None
    capability_gate_pass = tau_cap is not None
    if not risk_gate_pass:
        return (
            f"Escalate to {llm_name}; {slm_name} fails the risk gate before size-based capability selection can begin.",
            False,
            False,
            "risk",
        )
    if not capability_gate_pass:
        return (
            f"Escalate to {llm_name}; {slm_name} is risk-eligible but does not clear tau_cap.",
            True,
            False,
            "capability",
        )
    limit = min(tau_risk, tau_cap)
    binding_gate = "risk" if tau_risk <= tau_cap else "capability"
    return (
        f"Route to {slm_name} up to difficulty {limit:.3f}; escalate to {llm_name} beyond that boundary.",
        True,
        True,
        binding_gate,
    )


def build_task_decision_matrix(repo_root: Path) -> list[TaskDecisionMatrixRecord]:
    task_dirs = {
        "classification": repo_root / "tasks" / "classification",
        "maths": repo_root / "tasks" / "maths",
        "text_generation": repo_root / "tasks" / "text_generation",
        "summarization": repo_root / "tasks" / "Summarization",
        "information_extraction": repo_root / "tasks" / "Information Extraction",
        "retrieval_grounded": repo_root / "tasks" / "Retrieval_grounded",
        "instruction_following": repo_root / "tasks" / "instruction_following",
        "code_generation": repo_root / "tasks" / "code_generation",
    }

    records: list[TaskDecisionMatrixRecord] = []
    for task, task_root in task_dirs.items():
        summary_path = _latest_part_b_summary(task_root)
        if summary_path is None:
            continue
        summary = _parse_json(summary_path)
        pairs = summary.get("pairs") or []
        if not pairs:
            continue
        pair = max(pairs, key=lambda item: int(item.get("matched_examples", 0) or 0))
        sddf_root = _resolve_sddf_root(summary_path, summary.get("sddf_root"))
        canonical_rows = _parse_jsonl(sddf_root / "canonical_rows.jsonl")
        tau_risk, tau_risk_bin = _derive_tau_risk(canonical_rows, pair["slm_name"])
        tau_cap, tau_cap_bin = _derive_tau_cap(pair)
        policy, risk_gate_pass, capability_gate_pass, binding_gate = _build_policy(
            pair["slm_name"],
            pair["llm_name"],
            tau_risk,
            tau_cap,
        )
        ordered_models = sorted([pair["slm_name"], pair["llm_name"]], key=_sort_key)
        records.append(
            TaskDecisionMatrixRecord(
                task=task,
                benchmark=summary.get("benchmark", task),
                summary_path=str(summary_path),
                sddf_root=str(sddf_root),
                slm_name=pair["slm_name"],
                slm_size_b=_infer_model_size_b(pair["slm_name"]),
                llm_name=pair["llm_name"],
                llm_size_b=_infer_model_size_b(pair["llm_name"]),
                size_order=ordered_models,
                matched_examples=int(pair.get("matched_examples", 0) or 0),
                tau_risk=tau_risk,
                tau_risk_bin=tau_risk_bin,
                tau_cap=tau_cap,
                tau_cap_bin=tau_cap_bin,
                risk_gate_pass=risk_gate_pass,
                capability_gate_pass=capability_gate_pass,
                routing_policy=policy,
                binding_gate=binding_gate,
                curve_plot_path=pair.get("plot_path"),
            )
        )
    return records


def export_task_decision_matrix(repo_root: Path, markdown_path: Path, json_path: Path) -> list[TaskDecisionMatrixRecord]:
    records = build_task_decision_matrix(repo_root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps([asdict(record) for record in records], indent=2), encoding="utf-8")

    lines = [
        "# Task Decision Matrix",
        "",
        "Primary routing matrix: sort candidates by model size, apply `tau_risk` first, then `tau_cap`.",
        "",
        "| Task | Smallest candidate order | tau_risk | tau_cap | Binding gate | Routing policy |",
        "|---|---|---:|---:|---|---|",
    ]
    for record in records:
        size_order = " -> ".join(record.size_order)
        tau_risk = f"{record.tau_risk:.3f}" if record.tau_risk is not None else "None"
        tau_cap = f"{record.tau_cap:.3f}" if record.tau_cap is not None else "None"
        lines.append(
            f"| {record.task} | {size_order} | {tau_risk} | {tau_cap} | {record.binding_gate} | {record.routing_policy} |"
        )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return records
