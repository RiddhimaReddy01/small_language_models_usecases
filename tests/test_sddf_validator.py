from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from sddf.validator import save_historical_run_validation, validate_historical_runs


class SddfValidatorTests(unittest.TestCase):
    def test_validator_flags_partial_maths_dry_run(self) -> None:
        tmp = Path("tests/.tmp_validator_repo")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            (tmp / "maths" / "results" / "raw").mkdir(parents=True, exist_ok=True)
            sample = {
                "mode": "dry_run",
                "experiments": [
                    {
                        "model": "gemini_flash_lite",
                        "dataset": "GSM8K",
                        "records": [{"base": {"request_id": "1"}}],
                    }
                ],
            }
            (tmp / "maths" / "results" / "raw" / "results_quick.json").write_text(json.dumps(sample), encoding="utf-8")

            payload = validate_historical_runs(tmp)
            maths_runs = [run for run in payload["runs"] if run["benchmark"] == "maths"]
            self.assertEqual(len(maths_runs), 1)
            self.assertEqual(maths_runs[0]["overall_status"], "partial")
            self.assertTrue(any("dry_run" in note for note in maths_runs[0]["notes"]))
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)

    def test_validator_writes_output(self) -> None:
        tmp = Path("tests/.tmp_validator_write")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            tmp.mkdir(parents=True, exist_ok=True)
            output_path = tmp / "audit.json"
            saved = save_historical_run_validation(tmp, output_path)
            self.assertEqual(saved, output_path)
            self.assertTrue(output_path.exists())
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
