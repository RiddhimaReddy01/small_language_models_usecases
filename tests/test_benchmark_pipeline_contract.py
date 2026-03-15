from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "benchmark_pipeline_registry.json"


class BenchmarkPipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_uses_expected_stage_order(self) -> None:
        self.assertEqual(
            self.registry["canonical_stage_order"],
            [
                "dataset_sampling",
                "model_inference",
                "prediction_storage",
                "metric_computation",
                "benchmark_report_generation",
            ],
        )

    def test_every_benchmark_declares_all_canonical_stages(self) -> None:
        expected = self.registry["canonical_stage_order"]
        for benchmark in self.registry["benchmarks"]:
            with self.subTest(benchmark=benchmark["name"]):
                stages = [stage["stage"] for stage in benchmark["stages"]]
                self.assertEqual(stages, expected)
                self.assertEqual(len(stages), len(set(stages)))

    def test_registry_paths_and_symbols_exist(self) -> None:
        for benchmark in self.registry["benchmarks"]:
            with self.subTest(benchmark=benchmark["name"]):
                benchmark_root = REPO_ROOT / benchmark["root"]
                self.assertTrue(benchmark_root.exists(), f"Missing benchmark root: {benchmark_root}")

                for stage in benchmark["stages"]:
                    with self.subTest(benchmark=benchmark["name"], stage=stage["stage"]):
                        path = REPO_ROOT / stage["path"]
                        self.assertTrue(path.exists(), f"Missing stage file: {path}")
                        content = path.read_text(encoding="utf-8")
                        self.assertIn(stage["symbol"], content, f"Missing symbol '{stage['symbol']}' in {path}")


if __name__ == "__main__":
    unittest.main()
