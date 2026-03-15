from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codegen_eval.reporting import (
    export_combined_benchmark_tables,
    export_benchmark_tables,
    render_capability_table,
    render_markdown_report,
    render_operational_table,
)
from codegen_eval.runner import run_evaluation
from codegen_eval.types import EvaluationConfig, GenerationConfig, GenerationResult, ModelSpec, RunConfig, Task


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp_tests"


def make_test_dir() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


SUMMARY = [
    {
        "model": "Model A",
        "model_name": "example/model-a",
        "time_budget_minutes": 4,
        "human_eval_attempted": 0,
        "mbpp_attempted": 2,
        "total_attempted": 2,
        "tasks_completed_in_budget": 2,
        "pass@1": 0.5,
        "syntax_error_rate": 0.0,
        "runtime_failure_rate": 0.0,
        "logical_failure_rate": 0.5,
        "reliability_score": 0.5,
        "self_consistency_score": None,
        "format_compliance": 1.0,
        "signature_compliance": 1.0,
        "instruction_adherence": 1.0,
        "deterministic_reproducibility": None,
        "unsafe_code_rate": 0.0,
        "avg_latency_seconds": 1.2,
        "p95_latency_seconds": 1.4,
        "tokens_per_second": 5.0,
        "peak_ram_gb": 0.25,
        "avg_output_tokens": 48.0,
        "cost_per_request": 0.0,
    }
]


class ReportingTests(unittest.TestCase):
    def test_table_renderers_include_expected_headers(self) -> None:
        capability = render_capability_table(SUMMARY)
        operational = render_operational_table(SUMMARY)

        self.assertIn("| Model | MBPP Attempted |", capability)
        self.assertNotIn("HumanEval Attempted", capability)
        self.assertNotIn("Self-Consistency Score", capability)
        self.assertNotIn("Deterministic Reproducibility", capability)
        self.assertIn("Model A", capability)
        self.assertIn("| Model | Time Budget (min) |", operational)
        self.assertIn("5.000", operational)
        self.assertNotIn("Cost / Request", operational)

    def test_export_benchmark_tables_writes_tables_and_manifest(self) -> None:
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        tmp_path = make_test_dir()
        self.addCleanup(shutil.rmtree, tmp_path, True)
        run_dir = tmp_path / "runs" / "run_20260314_031256"
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(json.dumps(SUMMARY, indent=2), encoding="utf-8")
        (run_dir / "report.md").write_text(render_markdown_report(SUMMARY), encoding="utf-8")
        (run_dir / "config_snapshot.json").write_text(
            json.dumps(
                {
                    "evaluation": {"mbpp_sample": 2, "time_budget_minutes": 4},
                    "generation": {"temperature": 0.15},
                    "models": [{"label": "Model A", "kind": "hf_local"}],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        output_dir = tmp_path / "benchmarks"

        outcome = export_benchmark_tables(run_dir, output_dir, source_config_path="configs/experiments/example.json")

        self.assertTrue(Path(outcome["capability_path"]).exists())
        self.assertTrue(Path(outcome["operational_path"]).exists())
        manifest = json.loads((output_dir / "manifests" / "latest_benchmark.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["models"][0]["label"], "Model A")

    def test_export_combined_benchmark_tables_skips_rate_limited_runs(self) -> None:
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        tmp_path = make_test_dir()
        self.addCleanup(shutil.rmtree, tmp_path, True)
        run_a = tmp_path / "runs" / "run_a"
        run_b = tmp_path / "runs" / "run_b"
        run_a.mkdir(parents=True)
        run_b.mkdir(parents=True)

        for run_dir, model_label in ((run_a, "Model A"), (run_b, "Gemini 1.5 Flash (Baseline)")):
            summary = [dict(SUMMARY[0], model=model_label)]
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            (run_dir / "report.md").write_text(render_markdown_report(summary), encoding="utf-8")
            (run_dir / "config_snapshot.json").write_text(
                json.dumps(
                    {
                        "evaluation": {"mbpp_sample": 2, "time_budget_minutes": 4},
                        "generation": {"temperature": 0.15},
                        "models": [{"label": model_label, "kind": "hf_local"}],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        (run_a / "task_results.jsonl").write_text("{}", encoding="utf-8")
        (run_b / "task_results.jsonl").write_text(
            json.dumps({"error_message": "Rate limit exceeded"}) + "\n",
            encoding="utf-8",
        )

        outcome = export_combined_benchmark_tables(
            [run_a, run_b],
            tmp_path / "benchmarks",
            source_config_paths=["config_a.json", "config_b.json"],
            deprecate_on_rate_limit=True,
        )

        manifest = json.loads(Path(outcome["manifest_path"]).read_text(encoding="utf-8"))
        exported_summary = json.loads(Path(outcome["summary_path"]).read_text(encoding="utf-8"))
        self.assertEqual(len(exported_summary), 1)
        self.assertEqual(exported_summary[0]["model"], "Model A")
        self.assertEqual(manifest["deprecated_runs"][0]["status"], "deprecated_rate_limit")

    def test_run_evaluation_auto_exports_latest_tables(self) -> None:
        class StubAdapter:
            def generate(self, prompt: str) -> GenerationResult:
                return GenerationResult(
                    raw_text="def solve(x):\n    return x",
                    code="def solve(x):\n    return x",
                    latency_seconds=0.1,
                    output_tokens=12,
                    tokens_per_second=120.0,
                    input_tokens=8,
                    output_cost=0.0,
                )

        task = Task(
            task_id="mbpp-1",
            dataset="MBPP",
            problem_text="Return the input.",
            entry_point="solve",
            starter_code="def solve(x):\n    pass",
            test_code="assert solve(3) == 3",
        )
        run_config = RunConfig(
            evaluation=EvaluationConfig(human_eval_sample=0, mbpp_sample=1, time_budget_minutes=1),
            generation=GenerationConfig(),
            models=[ModelSpec(label="Model A", kind="hf_local", model_name="example/model-a")],
        )

        TEST_TMP_ROOT.mkdir(exist_ok=True)
        tmp_path = make_test_dir()
        self.addCleanup(shutil.rmtree, tmp_path, True)
        with (
            patch("codegen_eval.runner.load_task_pool", return_value=[task]),
            patch("codegen_eval.runner.create_model_adapter", return_value=StubAdapter()),
            patch(
                "codegen_eval.runner.execute_code",
                return_value={
                    "stdout": "PASS",
                    "stderr": "",
                    "returncode": 0,
                    "timeout": False,
                    "elapsed_seconds": 0.05,
                    "peak_ram_gb": 0.2,
                },
            ),
        ):
            outcome = run_evaluation(
                run_config,
                tmp_path / "runs",
                benchmark_output_dir=tmp_path / "benchmarks",
                source_config_path="configs/experiments/example.json",
            )

        capability_path = Path(outcome["benchmark_export"]["capability_path"])
        operational_path = Path(outcome["benchmark_export"]["operational_path"])
        manifest_path = Path(outcome["benchmark_export"]["manifest_path"])

        self.assertTrue(capability_path.exists())
        self.assertTrue(operational_path.exists())
        self.assertTrue(manifest_path.exists())
        self.assertIn("Model A", capability_path.read_text(encoding="utf-8"))
        self.assertIn("Avg Latency / Task (s)", operational_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_config_path"], str(Path("configs/experiments/example.json").resolve()))


if __name__ == "__main__":
    unittest.main()
