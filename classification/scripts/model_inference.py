from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarking.interface import run_stage_cli


def run_model_inference_stage() -> int:
    return run_stage_cli("classification", "model_inference")


if __name__ == "__main__":
    raise SystemExit(run_model_inference_stage())
