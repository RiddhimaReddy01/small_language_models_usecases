from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _run(args: list[str]) -> None:
    cmd = [str(PY), *args]
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    if not PY.exists():
        raise FileNotFoundError(f"Python executable not found: {PY}")

    # 1) Validation generation + selection report.
    _run(["tools/generate_benchmark75_sddf.py", "--report-split", "val", "--val-count-per-task", "200"])
    _run(["tools/evaluate_test_phase.py", "--output-stem", "val_phase_report"])

    # 2) Tune per-task utility coefficients from validation candidates.
    _run(["tools/tune_task_utility_coeffs.py"])
    coeffs = ROOT / "model_runs" / "benchmarking" / "configs" / "task_utility_coeffs.json"

    # 3) Frozen test run with tuned task-level utility coefficients.
    _run(
        [
            "tools/generate_benchmark75_sddf.py",
            "--report-split",
            "test",
            "--val-count-per-task",
            "200",
            "--task-utility-coeffs",
            str(coeffs),
        ]
    )
    _run(["tools/evaluate_test_phase.py", "--output-stem", "test_phase_report"])

    # 4) Auxiliary reports kept separate from train/val/test claims.
    _run(["tools/summarize_error_taxonomy.py"])
    _run(["tools/summarize_deployment_tradeoffs.py"])

    print("Reproducibility bundle completed.")


if __name__ == "__main__":
    main()

