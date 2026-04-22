from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.s3_config_builder import build_s3_task_config


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build S3 task config from manager weights and auto-calculated dimension scores."
    )
    parser.add_argument(
        "--task-inputs",
        default="framework/benchmarking/s3_task_inputs.json",
        help="JSON mapping task -> task metadata/prompt for auto scoring.",
    )
    parser.add_argument(
        "--weights-source",
        default="framework/benchmarking/s3_task_config.json",
        help="JSON file containing a top-level `weights` object.",
    )
    parser.add_argument(
        "--output-path",
        default="framework/benchmarking/s3_task_config.auto.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--omit-default-star",
        action="store_true",
        help="Do not include '*' fallback profile in task_scores.",
    )
    args = parser.parse_args()

    task_inputs_path = Path(args.task_inputs).resolve()
    weights_source_path = Path(args.weights_source).resolve()
    out_path = Path(args.output_path).resolve()

    task_inputs = _load_json(task_inputs_path)
    if not isinstance(task_inputs, dict):
        raise ValueError("--task-inputs must be a JSON object mapping task->input payload")

    weights_payload = _load_json(weights_source_path)
    weights = weights_payload.get("weights", {})

    config = build_s3_task_config(
        weights=weights,
        task_inputs={str(k): dict(v) for k, v in task_inputs.items()},
        include_default_profile=not bool(args.omit_default_star),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Tasks={len(config.get('task_scores', {})) - (1 if '*' in config.get('task_scores', {}) else 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

