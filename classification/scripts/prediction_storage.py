from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarking.interface import run_stage_cli


def run_prediction_storage_stage() -> int:
    return run_stage_cli("classification", "prediction_storage")


if __name__ == "__main__":
    raise SystemExit(run_prediction_storage_stage())
