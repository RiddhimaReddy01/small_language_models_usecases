"""Tests for the instruction constraint validator."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from instruction_following.constraint_validators import ConstraintValidator


TEST_CASES = [
    {
        "name": "word count exactly",
        "text": "This is a test response",
        "constraints": [{"type": "length", "length_type": "exactly", "value": 5}],
        "expected": (1, 1),
    },
    {
        "name": "word count at most",
        "text": "This is a test",
        "constraints": [{"type": "length", "length_type": "at_most", "value": 10}],
        "expected": (1, 1),
    },
    {
        "name": "inclusion constraint",
        "text": "This is a test response",
        "constraints": [{"type": "inclusion", "words": ["test"]}],
        "expected": (1, 1),
    },
    {
        "name": "exclusion constraint",
        "text": "This is a good response",
        "constraints": [{"type": "exclusion", "words": ["bad"]}],
        "expected": (1, 1),
    },
    {
        "name": "bullet format",
        "text": "- First point\n- Second point",
        "constraints": [{"type": "format", "format": "bullets"}],
        "expected": (1, 1),
    },
    {
        "name": "multiple constraints",
        "text": "This is a test",
        "constraints": [
            {"type": "length", "length_type": "exactly", "value": 4},
            {"type": "inclusion", "words": ["test"]},
            {"type": "exclusion", "words": ["bad"]},
        ],
        "expected": (3, 3),
    },
    {
        "name": "failed length constraint",
        "text": "This is wrong",
        "constraints": [{"type": "length", "length_type": "exactly", "value": 10}],
        "expected": (0, 1),
    },
]


class ConstraintValidatorTests(unittest.TestCase):
    def test_constraint_cases(self) -> None:
        for case in TEST_CASES:
            with self.subTest(case=case["name"]):
                satisfied, total, _ = ConstraintValidator.validate_constraints(
                    case["text"],
                    case["constraints"],
                )
                self.assertEqual((satisfied, total), case["expected"])


if __name__ == "__main__":
    unittest.main()
