from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from sddf.setup_reporting import generate_part_a_report


class SddfSetupReportingTests(unittest.TestCase):
    def test_generate_part_a_report_for_maths_run(self) -> None:
        tmp = Path("tests/.tmp_part_a_report")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            run_dir = tmp / "maths_run"
            run_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "seed": 123,
                "mode": "live",
                "config_path": "config.yaml",
                "experiments": [
                    {
                        "model": "gemma_2b",
                        "dataset": "GSM8K",
                        "summary": {"accuracy": 0.2},
                        "records": [{"question": "2+2?", "base": {"request_id": "1"}}],
                    }
                ],
            }
            (run_dir / "results.json").write_text(json.dumps(payload), encoding="utf-8")
            outputs = generate_part_a_report("maths", run_dir / "results.json", output_dir=run_dir / "reports")
            report_text = Path(outputs["report_path"]).read_text(encoding="utf-8")
            self.assertIn("Part A - Benchmark Setup", report_text)
            self.assertIn("Task Definition", report_text)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
