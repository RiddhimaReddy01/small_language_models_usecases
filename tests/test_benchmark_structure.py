from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS = [
    "classification",
    "maths",
    "text_generation",
    "Summarization",
    "Information Extraction",
    "Retrieval_grounded",
    "instruction_following",
    "code_generation",
]
REQUIRED_FILES = [
    "README.md",
    "scripts/dataset_sampling.py",
    "scripts/model_inference.py",
    "scripts/prediction_storage.py",
    "scripts/metric_computation.py",
    "scripts/benchmark_report.py",
]


class BenchmarkStructureTests(unittest.TestCase):
    def test_standardized_task_structure_exists(self) -> None:
        for task in TASKS:
            for relative_path in REQUIRED_FILES:
                with self.subTest(task=task, relative_path=relative_path):
                    self.assertTrue((REPO_ROOT / "tasks" / task / relative_path).exists())


if __name__ == "__main__":
    unittest.main()
