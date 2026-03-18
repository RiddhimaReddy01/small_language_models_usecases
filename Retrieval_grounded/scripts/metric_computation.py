from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarking.interface import run_stage_cli


def run_metric_computation_stage() -> int:
    return run_stage_cli("retrieval_grounded", "metric_computation")


if __name__ == "__main__":
    raise SystemExit(run_metric_computation_stage())
