from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from sddf.reporting import generate_part_b_report


class SddfReportingTests(unittest.TestCase):
    def test_generate_part_b_report_from_synthetic_archive(self) -> None:
        tmp = Path("tests/.tmp_part_b_report")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            sddf_dir = tmp / "run" / "sddf"
            sddf_dir.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "example_id": "e1",
                    "task": "classification",
                    "dataset": "demo",
                    "model_name": "phi3:mini",
                    "model_family": "SLM",
                    "prediction": "positive",
                    "reference": "positive",
                    "primary_metric": 1.0,
                    "valid_output": 1,
                    "latency_sec": 0.1,
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": "H",
                    "difficulty_score": 1.0,
                    "difficulty_bin": 0,
                    "input_text": "great movie",
                    "metadata": {},
                },
                {
                    "example_id": "e1",
                    "task": "classification",
                    "dataset": "demo",
                    "model_name": "gemini-2.5-flash",
                    "model_family": "LLM",
                    "prediction": "positive",
                    "reference": "positive",
                    "primary_metric": 1.0,
                    "valid_output": 1,
                    "latency_sec": 0.2,
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": "H",
                    "difficulty_score": 1.0,
                    "difficulty_bin": 0,
                    "input_text": "great movie",
                    "metadata": {},
                },
                {
                    "example_id": "e2",
                    "task": "classification",
                    "dataset": "demo",
                    "model_name": "phi3:mini",
                    "model_family": "SLM",
                    "prediction": "negative",
                    "reference": "positive",
                    "primary_metric": 0.0,
                    "valid_output": 1,
                    "latency_sec": 0.1,
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": "H",
                    "difficulty_score": 3.0,
                    "difficulty_bin": 1,
                    "input_text": "ambiguous movie",
                    "metadata": {},
                },
                {
                    "example_id": "e2",
                    "task": "classification",
                    "dataset": "demo",
                    "model_name": "gemini-2.5-flash",
                    "model_family": "LLM",
                    "prediction": "positive",
                    "reference": "positive",
                    "primary_metric": 1.0,
                    "valid_output": 1,
                    "latency_sec": 0.2,
                    "memory_mb": None,
                    "cpu_util": None,
                    "difficulty_dim": "H",
                    "difficulty_score": 3.0,
                    "difficulty_bin": 1,
                    "input_text": "ambiguous movie",
                    "metadata": {},
                },
            ]
            archive = sddf_dir / "canonical_rows.jsonl"
            with archive.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")

            outputs = generate_part_b_report(tmp / "run", "classification")
            report_text = Path(outputs["report_path"]).read_text(encoding="utf-8")
            self.assertIn("Part B - SDDF Analysis", report_text)
            self.assertIn("Matched SLM vs LLM Analysis", report_text)
            self.assertIn("![Capability curve]", report_text)
            self.assertTrue(Path(outputs["summary_path"]).exists())
            self.assertTrue(any(path.suffix == ".png" for path in (tmp / "run" / "sddf" / "reports").iterdir()))
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)

    def test_generate_part_b_report_uses_inference_fallback_without_archive(self) -> None:
        tmp = Path("tests/.tmp_part_b_inferred")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            run_dir = tmp / "classification_results"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "raw_results_123.csv").write_text(
                "text,true_label,prediction,latency,is_valid,dataset,status\nhello,pos,pos,0.1,1,demo,success\n",
                encoding="utf-8",
            )
            (run_dir / "metrics_summary_123.json").write_text(
                json.dumps(
                    {
                        "metadata": {"model": "phi3:mini", "workers": 1},
                        "capability": {"demo": {"accuracy": 1.0}},
                        "operational": [{"dataset": "demo", "total_samples": 1}],
                    }
                ),
                encoding="utf-8",
            )

            outputs = generate_part_b_report(run_dir, "classification")
            report_text = Path(outputs["report_path"]).read_text(encoding="utf-8")
            summary = json.loads(Path(outputs["summary_path"]).read_text(encoding="utf-8"))

            self.assertIn("Inferred dominant dimension", report_text)
            self.assertEqual(summary["statuses"]["matched_slm_llm_analysis"]["status"], "partial")
            self.assertIn("Historical comparison", report_text)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
