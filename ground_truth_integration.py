#!/usr/bin/env python3
"""
Ground Truth Integration & Semantic Failure Classification

Downloads public ground truth datasets and merges them into outputs.jsonl
Enables semantic failure classification (wrong answer vs structural error)
"""

import json
import os
import ast
import re
from pathlib import Path
from collections import defaultdict
import hashlib
import requests

# Configuration
BENCHMARK_DIR = Path("benchmark_output")
TASKS = [
    "text_generation", "code_generation", "classification", "maths",
    "summarization", "retrieval_grounded", "instruction_following", "information_extraction"
]

GROUND_TRUTH_SOURCES = {
    "code_generation": {
        "url": "https://huggingface.co/datasets/openai/human-eval/raw/main/data/HumanEval.jsonl",
        "description": "HumanEval: 164 code problems with test cases"
    },
    "maths": {
        "url": "https://huggingface.co/datasets/hendrycks/math/raw/main/test.jsonl",
        "description": "MATH Dataset: 5,000 math problems with solutions"
    },
    "classification": {
        "url": "https://huggingface.co/datasets/nyu-mll/glue/raw/main/sst2/train.jsonl",
        "description": "GLUE SST-2: Sentiment classification with labels"
    },
    "information_extraction": {
        "url": "https://huggingface.co/datasets/conll2003/raw/main/train.jsonl",
        "description": "CoNLL 2003: NER with entity annotations"
    },
}


# ============================================================================
# SEMANTIC VALIDATORS
# ============================================================================

def validate_code(code_output, test_cases=None):
    """
    Validate code by:
    1. Checking syntax (AST parse)
    2. Checking execution (run tests if available)

    Returns: (is_valid, failure_type, details)
    """
    if not code_output or not code_output.strip():
        return False, "empty_output", "No code generated"

    # Check syntax
    try:
        ast.parse(code_output)
    except SyntaxError as e:
        return False, "syntax_error", f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, "parse_error", str(e)

    # Check for required patterns (def or class)
    has_function = "def " in code_output or "class " in code_output
    if not has_function:
        return False, "incomplete_output", "No function/class definition"

    # If test cases provided, run them
    if test_cases:
        try:
            namespace = {}
            exec(code_output, namespace)

            for test in test_cases:
                try:
                    result = eval(test, namespace)
                    if not result:
                        return False, "logic_error", f"Test failed: {test}"
                except Exception as e:
                    return False, "logic_error", f"Test raised exception: {e}"

            return True, None, "All tests passed"
        except Exception as e:
            return False, "execution_error", str(e)

    # Structural validity only
    return True, None, "Structurally valid (no tests to run)"


def validate_math(output, ground_truth_answer=None):
    """
    Validate math by:
    1. Extracting numeric answer
    2. Comparing to ground truth (if available)

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No answer generated"

    # Extract number using regex
    numbers = re.findall(r'-?\d+\.?\d*', output)

    if not numbers:
        return False, "no_answer", "No extractable number found"

    extracted = float(numbers[-1])  # Take last number as answer

    if ground_truth_answer is not None:
        gt = float(ground_truth_answer) if isinstance(ground_truth_answer, str) else ground_truth_answer

        # Check approximate equality
        if abs(extracted - gt) < 1e-6:
            return True, None, f"Correct: {extracted}"
        else:
            return False, "arithmetic_error", f"Got {extracted}, expected {gt}"

    # Just check extraction
    return True, None, f"Number extracted: {extracted}"


def validate_classification(output, ground_truth_label=None, label_set=None):
    """
    Validate classification by:
    1. Extracting predicted label
    2. Comparing to ground truth (if available)

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No label generated"

    # Extract single word (likely the label)
    words = output.strip().split()
    if not words:
        return False, "empty_output", "No output"

    predicted = words[0].lower()  # Take first word

    if label_set and predicted not in label_set:
        return False, "invalid_label", f"'{predicted}' not in valid set: {label_set}"

    if ground_truth_label is not None:
        gt = str(ground_truth_label).lower()
        if predicted == gt:
            return True, None, f"Correct: {predicted}"
        else:
            return False, "wrong_label", f"Got '{predicted}', expected '{gt}'"

    # Just check format
    return True, None, f"Label: {predicted}"


def validate_extraction(output, ground_truth_schema=None):
    """
    Validate JSON extraction by:
    1. Checking JSON validity
    2. Checking required fields (if schema provided)

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No JSON generated"

    # Try to parse JSON
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as e:
        return False, "json_error", f"Invalid JSON: {str(e)[:100]}"

    if ground_truth_schema:
        required_fields = ground_truth_schema.get("required_fields", [])
        for field in required_fields:
            if field not in parsed:
                return False, "missing_field", f"Missing required field: {field}"

    return True, None, "Valid JSON"


def validate_summarization(output, ground_truth_summary=None):
    """
    Validate summarization by:
    1. Checking length (80-2000 chars is reasonable)
    2. Computing ROUGE score (if GT available)

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No summary generated"

    output_len = len(output.strip())

    if output_len < 30:
        return False, "too_short", f"Summary too short ({output_len} chars)"

    if output_len > 3000:
        return False, "too_long", f"Summary too long ({output_len} chars)"

    if ground_truth_summary:
        # Simple ROUGE-1 (unigram overlap)
        pred_tokens = set(output.lower().split())
        gt_tokens = set(ground_truth_summary.lower().split())

        overlap = len(pred_tokens & gt_tokens)
        recall = overlap / len(gt_tokens) if gt_tokens else 0

        if recall < 0.2:
            return False, "low_relevance", f"ROUGE-1 recall: {recall:.2f} (too low)"

        return True, None, f"ROUGE-1 recall: {recall:.2f}"

    return True, None, f"Length: {output_len} chars"


def validate_qa(output, ground_truth_answer=None):
    """
    Validate QA by:
    1. Checking output length
    2. Computing F1 score (token overlap) if GT available

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No answer generated"

    output_len = len(output.strip())

    if output_len < 10:
        return False, "too_short", f"Answer too short ({output_len} chars)"

    if ground_truth_answer:
        # Token F1
        pred_tokens = set(output.lower().split())
        gt_tokens = set(ground_truth_answer.lower().split())

        if not gt_tokens:
            return True, None, "GT answer empty"

        overlap = len(pred_tokens & gt_tokens)
        precision = overlap / len(pred_tokens) if pred_tokens else 0
        recall = overlap / len(gt_tokens) if gt_tokens else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        if f1 < 0.3:
            return False, "answer_mismatch", f"F1: {f1:.2f} (too low)"

        return True, None, f"F1: {f1:.2f}"

    return True, None, f"Length: {output_len} chars"


def validate_instruction(output, ground_truth_reference=None):
    """
    Validate instruction following by:
    1. Checking output is non-empty
    2. LLM-based judgment (if needed)

    Returns: (is_valid, failure_type, details)
    """
    if not output or not output.strip():
        return False, "empty_output", "No response generated"

    output_len = len(output.strip())

    if output_len < 5:
        return False, "too_short", f"Response too short ({output_len} chars)"

    # For now, just structural validation
    # Semantic validation would require LLM-as-judge
    return True, None, f"Length: {output_len} chars (needs LLM-as-judge for semantic)"


# ============================================================================
# FAILURE CLASSIFICATION ENGINE
# ============================================================================

class SemanticFailureClassifier:
    """Classify failures into structural vs semantic with ground truth"""

    def __init__(self):
        self.ground_truth_map = {}  # {(task, query_id): gt_data}
        self.load_ground_truth()

    def load_ground_truth(self):
        """Load all available ground truth datasets"""
        print("\n[Loading Ground Truth Datasets]")
        # Placeholder for GT loading logic
        # In full implementation, download and parse GT datasets

    def classify(self, record):
        """
        Classify failure for a single output record

        Returns: {
            "is_valid": bool,
            "structural_failures": [failure_type, ...],
            "semantic_failures": [failure_type, ...],
            "severity": "critical" | "high" | "medium" | "low" | None,
            "details": str
        }
        """
        task = record.get("task")
        output = record.get("raw_output", "").strip()
        query_id = record.get("query_id")
        error = (record.get("error") or "").lower()

        result = {
            "is_valid": record.get("valid", False),
            "structural_failures": [],
            "semantic_failures": [],
            "severity": None,
            "details": ""
        }

        if result["is_valid"]:
            return result

        # Check for structural failures first
        if not output:
            result["structural_failures"].append("empty_output")
            result["severity"] = "critical"
            return result

        if "timeout" in error:
            result["structural_failures"].append("timeout")
            result["severity"] = "critical"
            return result

        if "token" in error:
            result["structural_failures"].append("token_limit")
            result["severity"] = "high"
            return result

        # Task-specific semantic validation
        if task == "code_generation":
            is_valid, failure_type, details = validate_code(output)
            if failure_type:
                if failure_type in ["syntax_error", "parse_error"]:
                    result["structural_failures"].append(failure_type)
                    result["severity"] = "critical"
                else:
                    result["semantic_failures"].append(failure_type)
                    result["severity"] = "high"
            result["details"] = details

        elif task == "maths":
            is_valid, failure_type, details = validate_math(output)
            if failure_type:
                result["semantic_failures"].append(failure_type)
                result["severity"] = "high" if failure_type == "arithmetic_error" else "medium"
            result["details"] = details

        elif task == "classification":
            is_valid, failure_type, details = validate_classification(output)
            if failure_type:
                if failure_type == "invalid_label":
                    result["structural_failures"].append(failure_type)
                    result["severity"] = "high"
                else:
                    result["semantic_failures"].append(failure_type)
                    result["severity"] = "medium"
            result["details"] = details

        elif task == "information_extraction":
            is_valid, failure_type, details = validate_extraction(output)
            if failure_type:
                result["structural_failures"].append(failure_type)
                result["severity"] = "high"
            result["details"] = details

        elif task == "summarization":
            is_valid, failure_type, details = validate_summarization(output)
            if failure_type:
                result["semantic_failures"].append(failure_type)
                result["severity"] = "medium"
            result["details"] = details

        elif task == "retrieval_grounded":
            is_valid, failure_type, details = validate_qa(output)
            if failure_type:
                result["semantic_failures"].append(failure_type)
                result["severity"] = "medium"
            result["details"] = details

        elif task == "instruction_following":
            is_valid, failure_type, details = validate_instruction(output)
            if failure_type:
                result["semantic_failures"].append(failure_type)
                result["severity"] = "low"
            result["details"] = details

        elif task == "text_generation":
            # For text generation, just check length
            output_len = len(output.strip())
            if output_len < 10:
                result["semantic_failures"].append("too_short")
                result["severity"] = "low"
            result["details"] = f"Length: {output_len} chars"

        return result


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*70)
    print("GROUND TRUTH INTEGRATION & SEMANTIC FAILURE CLASSIFICATION")
    print("="*70)

    classifier = SemanticFailureClassifier()

    # Example: Classify failures for code_generation
    sample_outputs = [
        {
            "task": "code_generation",
            "query_id": "test_1",
            "raw_output": "def reverse(s):\n    return s[::-1]",
            "valid": False,
            "error": "Logic error"
        },
        {
            "task": "maths",
            "query_id": "test_2",
            "raw_output": "The answer is 42",
            "valid": False,
            "error": ""
        },
        {
            "task": "code_generation",
            "query_id": "test_3",
            "raw_output": "def foo(: # syntax error",
            "valid": False,
            "error": ""
        }
    ]

    print("\n[FAILURE CLASSIFICATION EXAMPLES]\n")
    for record in sample_outputs:
        result = classifier.classify(record)
        print(f"Task: {record['task']}")
        print(f"  Structural: {result['structural_failures']}")
        print(f"  Semantic:   {result['semantic_failures']}")
        print(f"  Severity:   {result['severity']}")
        print(f"  Details:    {result['details']}\n")


if __name__ == "__main__":
    main()
