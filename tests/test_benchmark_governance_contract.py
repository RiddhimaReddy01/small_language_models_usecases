from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_REGISTRY_PATH = REPO_ROOT / "benchmark_governance_registry.json"


class BenchmarkGovernanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(GOVERNANCE_REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_all_benchmarks_are_registered(self) -> None:
        names = [item["name"] for item in self.registry["benchmarks"]]
        self.assertEqual(
            names,
            [
                "classification",
                "text_generation",
                "information_extraction",
                "summarization",
                "code_generation",
                "instruction_following",
                "maths",
                "retrieval_grounded",
            ],
        )

    def test_registry_paths_exist(self) -> None:
        for benchmark in self.registry["benchmarks"]:
            with self.subTest(benchmark=benchmark["name"]):
                root = REPO_ROOT / benchmark["benchmark_root"]
                self.assertTrue(root.exists(), f"Missing benchmark root: {root}")
                for rel_path in benchmark["config_paths"] + benchmark["code_paths"]:
                    path = REPO_ROOT / rel_path
                    self.assertTrue(path.exists(), f"Missing evidence path: {path}")


if __name__ == "__main__":
    unittest.main()
