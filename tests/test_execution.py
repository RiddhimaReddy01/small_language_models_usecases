from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkExecutionTests(unittest.TestCase):
    def test_text_generation_runs_via_root_runner(self) -> None:
        output_root = REPO_ROOT / "tests" / ".tmp_benchmark_runs"
        if output_root.exists():
            shutil.rmtree(output_root)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "run_benchmark.py"),
                    "--task",
                    "text_generation",
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "smoke",
                    "--",
                    "--mock",
                    "--sample_size",
                    "1",
                    "--task_type",
                    "samples",
                ],
                cwd=REPO_ROOT,
                timeout=120,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            run_dir = output_root / "smoke"
            self.assertTrue((run_dir / "run_manifest.json").exists())
            self.assertTrue((run_dir / "hardware.json").exists())
            self.assertTrue((run_dir / "metrics.json").exists())
            self.assertTrue((run_dir / "report.md").exists())
        finally:
            if output_root.exists():
                shutil.rmtree(output_root)


if __name__ == "__main__":
    unittest.main()
