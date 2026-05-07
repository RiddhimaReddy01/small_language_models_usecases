from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.s3 import score_s3_dimensions, decide_s3_and_route


TASK_FAMILIES = (
    "classification",
    "code_generation",
    "information_extraction",
    "instruction_following",
    "maths",
    "retrieval_grounded",
    "summarization",
    "text_generation",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _thresholds_for_task(task_thresholds: dict[str, Any], task: str, tau1: float, tau2: float) -> tuple[float, float]:
    block = task_thresholds.get(task, task_thresholds.get("*", {}))
    if not isinstance(block, dict):
        return float(tau1), float(tau2)
    t1 = float(block.get("tau1", tau1))
    t2 = float(block.get("tau2", tau2))
    if t2 < t1:
        raise ValueError(f"Invalid thresholds for {task}: tau2 < tau1")
    return t1, t2


def main() -> int:
    parser = argparse.ArgumentParser(description="Manager-facing S3 decision for one task family.")
    parser.add_argument("--task-family", required=True, choices=TASK_FAMILIES)
    parser.add_argument("--prompt", required=True, help="Short task description from manager.")
    parser.add_argument("--expected-format", default="")
    parser.add_argument("--business-critical", action="store_true")
    parser.add_argument("--requires-human-approval", action="store_true")
    parser.add_argument("--data-classification", default="internal")
    parser.add_argument("--contains-pii", action="store_true")
    parser.add_argument("--contains-phi", action="store_true")
    parser.add_argument("--target-p99-ms", type=int, default=None)
    parser.add_argument("--real-time", action="store_true")
    parser.add_argument("--qps", type=float, default=None)
    parser.add_argument("--daily-requests", type=int, default=None)
    parser.add_argument("--bursty", action="store_true")
    parser.add_argument("--overrides", default="", help="Optional JSON string like '{\"SK\":4}'.")
    parser.add_argument("--weights-source", default="framework/benchmarking/s3_task_config.json")
    parser.add_argument("--task-tier-thresholds", default="framework/benchmarking/s3_task_tier_thresholds.json")
    parser.add_argument("--tau-risk", type=float, default=9.0)
    parser.add_argument("--tau-cap", type=float, default=9.0)
    parser.add_argument("--default-tau1", type=float, default=3.2)
    parser.add_argument("--default-tau2", type=float, default=4.0)
    parser.add_argument("--output-path", default="")
    args = parser.parse_args()

    overrides: dict[str, int] = {}
    if str(args.overrides).strip():
        raw = json.loads(args.overrides)
        overrides = {str(k): int(v) for k, v in dict(raw).items()}

    score_payload = {
        "task": str(args.task_family),
        "prompt": str(args.prompt),
        "expected_format": str(args.expected_format) if args.expected_format else None,
        "business_critical": bool(args.business_critical),
        "requires_human_approval": bool(args.requires_human_approval),
        "data_classification": str(args.data_classification),
        "contains_pii": bool(args.contains_pii),
        "contains_phi": bool(args.contains_phi),
        "target_p99_ms": args.target_p99_ms,
        "real_time": bool(args.real_time),
        "qps": args.qps,
        "daily_requests": args.daily_requests,
        "bursty": bool(args.bursty),
        "overrides": overrides or None,
    }
    s3_scores = score_s3_dimensions(score_payload)

    weights_doc = _load_json(Path(args.weights_source).resolve())
    weights = {k: int(v) for k, v in dict(weights_doc.get("weights", {})).items()}

    task_thresholds_doc = _load_json(Path(args.task_tier_thresholds).resolve())
    tau1, tau2 = _thresholds_for_task(
        task_thresholds=task_thresholds_doc,
        task=str(args.task_family),
        tau1=float(args.default_tau1),
        tau2=float(args.default_tau2),
    )

    decision = decide_s3_and_route(
        scores=s3_scores,  # type: ignore[arg-type]
        weights=weights,  # type: ignore[arg-type]
        tau_risk=float(args.tau_risk),
        tau_cap=float(args.tau_cap),
        tau1=tau1,
        tau2=tau2,
    )

    out = {
        "task_family": str(args.task_family),
        "s3_scores": s3_scores,
        "weights": weights,
        "tier_thresholds_used": {"tau1": tau1, "tau2": tau2},
        "decision": decision,
    }

    rendered = json.dumps(out, indent=2)
    print(rendered)
    if str(args.output_path).strip():
        out_path = Path(args.output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

