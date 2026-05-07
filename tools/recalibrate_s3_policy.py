from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sddf.s3 import recommend_s3_score_overrides, recommend_task_tier_thresholds


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Recalibrate S3 policy from SDDF evidence.")
    parser.add_argument(
        "--bridge-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/s3_sddf_bridge_seed42.auto.family.json",
    )
    parser.add_argument(
        "--val-report-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_evaluation_report.json",
    )
    parser.add_argument(
        "--test-report-path",
        default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/test_evaluation_report.json",
    )
    parser.add_argument(
        "--current-task-thresholds",
        default="framework/benchmarking/s3_task_tier_thresholds.json",
    )
    parser.add_argument(
        "--output-path",
        default="framework/benchmarking/s3_policy_recommendations.json",
    )
    args = parser.parse_args()

    bridge = _load_json(Path(args.bridge_path).resolve())
    val_report = _load_json(Path(args.val_report_path).resolve())
    test_report = _load_json(Path(args.test_report_path).resolve())
    curr_thresholds = _load_json(Path(args.current_task_thresholds).resolve())

    thresholds_next = recommend_task_tier_thresholds(
        current_thresholds=curr_thresholds,
        test_report=test_report,
    )
    score_overrides_next = recommend_s3_score_overrides(
        bridge_output=bridge,
        val_report=val_report,
    )

    out = {
        "source_files": {
            "bridge_path": str(Path(args.bridge_path).resolve()),
            "val_report_path": str(Path(args.val_report_path).resolve()),
            "test_report_path": str(Path(args.test_report_path).resolve()),
            "current_task_thresholds": str(Path(args.current_task_thresholds).resolve()),
        },
        "recommendations": {
            "task_tier_thresholds_next": thresholds_next,
            "task_score_overrides_next": score_overrides_next,
        },
        "note": (
            "Apply recommendations after governance review. "
            "Thresholds tune formula-tier sensitivity; score overrides tune S3 dimension priors."
        ),
    }

    out_path = Path(args.output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Tasks(threshold_recs)={len(thresholds_next) - (1 if '*' in thresholds_next else 0)}")
    print(f"Tasks(score_override_recs)={len(score_overrides_next)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

