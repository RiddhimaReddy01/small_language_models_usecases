from __future__ import annotations

import unittest
from pathlib import Path

from codegen_eval.config import load_run_config


REPO_ROOT = Path(__file__).resolve().parents[1]


class ConfigLoadingTests(unittest.TestCase):
    def test_loads_example_config_from_new_location(self) -> None:
        config = load_run_config(REPO_ROOT / "configs" / "examples" / "sample_config.json")

        self.assertEqual(config.evaluation.human_eval_sample, 15)
        self.assertEqual(config.evaluation.mbpp_sample, 15)
        self.assertEqual(len(config.models), 4)


if __name__ == "__main__":
    unittest.main()
