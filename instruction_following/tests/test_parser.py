"""Test the constraint validator parser."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from instruction_following.constraint_validators import ConstraintValidator

# Test cases
test_cases = [
    {
        "name": "Word count (exactly 5)",
        "text": "This is a test response",  # 5 words
        "constraints": [{"type": "length", "length_type": "exactly", "value": 5}],
        "expected": (1, 1)
    },
    {
        "name": "Word count (at most 10)",
        "text": "This is a test",  # 4 words
        "constraints": [{"type": "length", "length_type": "at_most", "value": 10}],
        "expected": (1, 1)
    },
    {
        "name": "Inclusion (must contain 'test')",
        "text": "This is a test response",
        "constraints": [{"type": "inclusion", "words": ["test"]}],
        "expected": (1, 1)
    },
    {
        "name": "Exclusion (avoid 'bad')",
        "text": "This is a good response",
        "constraints": [{"type": "exclusion", "words": ["bad"]}],
        "expected": (1, 1)
    },
    {
        "name": "Format (bullets)",
        "text": "- First point\n- Second point",
        "constraints": [{"type": "format", "format": "bullets"}],
        "expected": (1, 1)
    },
    {
        "name": "Multiple constraints",
        "text": "This is a test",
        "constraints": [
            {"type": "length", "length_type": "exactly", "value": 4},
            {"type": "inclusion", "words": ["test"]},
            {"type": "exclusion", "words": ["bad"]}
        ],
        "expected": (3, 3)
    },
    {
        "name": "Failed length constraint",
        "text": "This is wrong",  # 3 words, expects 10
        "constraints": [{"type": "length", "length_type": "exactly", "value": 10}],
        "expected": (0, 1)
    }
]

print("=" * 80)
print("CONSTRAINT VALIDATOR TEST SUITE")
print("=" * 80)

passed = 0
failed = 0

for test in test_cases:
    satisfied, total, metrics = ConstraintValidator.validate_constraints(
        test["text"],
        test["constraints"]
    )

    success = (satisfied, total) == test["expected"]
    status = "PASS" if success else "FAIL"

    if success:
        passed += 1
    else:
        failed += 1

    print(f"\n[{status}] {test['name']}")
    print(f"  Text: '{test['text']}'")
    print(f"  Expected: {test['expected']}, Got: ({satisfied}, {total})")

    if not success:
        print(f"  Constraints: {test['constraints']}")
        print(f"  Metrics: {metrics}")

print("\n" + "=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)

if failed == 0:
    print("Parser is working correctly!")
else:
    print(f"Parser has {failed} issue(s) to fix")
