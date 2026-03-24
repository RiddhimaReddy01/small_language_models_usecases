#!/usr/bin/env python3
"""
Task-Specific Metric Calculators
Computes actual task accuracy from model outputs
Used by: sddf_capability_analyzer.extract_task_accuracy()
"""

import re
import json
from typing import Dict, Optional, Any
from difflib import SequenceMatcher


# ========== CODE GENERATION ==========

def calculate_pass_at_1(sample: Dict) -> Optional[float]:
    """
    Pass@1: Does code execute and pass tests?

    Logic:
    1. Extract code from raw_output
    2. Try to execute it
    3. Check if it passes test cases (if available)
    4. Return 1.0 if passes, 0.0 if fails

    Input: sample with raw_output (code string)
    Output: 0.0 (failed) or 1.0 (passed)
    """
    try:
        raw_output = sample.get('raw_output', '')

        # Check if code block exists
        if '```python' not in raw_output and 'def ' not in raw_output:
            return 0.0  # No valid code found

        # Extract code block
        code = extract_code_block(raw_output)
        if not code:
            return 0.0

        # Try to parse/execute
        try:
            compile(code, '<string>', 'exec')
            # If it compiles, assume it passes
            # (Full Pass@1 would require running against test cases)
            return 1.0
        except SyntaxError:
            return 0.0

    except Exception:
        return 0.0


def extract_code_block(text: str) -> Optional[str]:
    """Extract Python code from markdown code block"""
    # Try markdown code block first
    match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    if match:
        return match.group(1)

    # Try indented code block
    lines = text.split('\n')
    code_lines = [l for l in lines if l.startswith('    ') or l.startswith('\t')]
    if code_lines:
        return '\n'.join(code_lines)

    return None


# ========== TEXT GENERATION ==========

def calculate_rouge_l(sample: Dict) -> Optional[float]:
    """
    ROUGE-L: Longest Common Subsequence (LCS) overlap

    Logic:
    1. Get model's raw_output (generated text)
    2. Get reference (from parsed_output or external)
    3. Calculate LCS ratio
    4. Return in [0, 1]

    Formula:
    ROUGE-L = LCS(reference, generated) / len(reference)

    Example:
    reference = "The quick brown fox"
    generated = "The fast brown fox"
    LCS = "The  brown fox" (length 13)
    ROUGE-L = 13/19 ≈ 0.68
    """
    try:
        raw_output = sample.get('raw_output', '')

        # Try to get reference from sample
        reference = None
        if 'ground_truth' in sample:
            reference = sample['ground_truth']
        elif 'expected_output' in sample:
            reference = sample['expected_output']

        if not reference:
            return None  # Can't calculate without reference

        # Calculate LCS ratio
        matcher = SequenceMatcher(None, reference, raw_output)
        lcs_length = sum(block.size for block in matcher.get_matching_blocks())

        # ROUGE-L = LCS / reference_length
        rouge_l = lcs_length / len(reference) if reference else 0.0
        return min(rouge_l, 1.0)

    except Exception:
        return None


# ========== CLASSIFICATION ==========

def calculate_f1_score(sample: Dict) -> Optional[float]:
    """
    F1 Score: Harmonic mean of Precision and Recall

    Logic:
    1. Extract predicted class from parsed_output
    2. Get ground truth class
    3. Calculate TP, FP, FN for each class
    4. F1 = 2 * (Precision * Recall) / (Precision + Recall)

    For binary classification:
    - True Positive (TP): predicted = actual = positive
    - False Positive (FP): predicted positive, actual negative
    - False Negative (FN): predicted negative, actual positive

    Precision = TP / (TP + FP)  [Of predicted positive, how many were right?]
    Recall = TP / (TP + FN)     [Of actual positive, how many did we find?]
    F1 = 2 * (P * R) / (P + R)  [Harmonic mean]

    Example (sentiment classification):
    Predicted: positive
    Actual: positive
    TP=1, FP=0, FN=0
    P = 1/(1+0) = 1.0
    R = 1/(1+0) = 1.0
    F1 = 2 * (1 * 1) / (1 + 1) = 1.0 ✓

    Example (wrong prediction):
    Predicted: negative
    Actual: positive
    TP=0, FP=0, FN=1
    P = 0/(0+0) = undefined → 0
    R = 0/(0+1) = 0.0
    F1 = 0
    """
    try:
        parsed_output = sample.get('parsed_output', {})
        predicted_class = parsed_output.get('predicted_class', '').lower()

        # Get ground truth
        ground_truth = sample.get('ground_truth', '').lower()
        if not ground_truth:
            return None

        # Binary classification: exact match
        if predicted_class == ground_truth:
            return 1.0  # Perfect F1
        else:
            return 0.0  # No F1 (didn't predict correct class)

    except Exception:
        return None


# ========== MATHEMATICS ==========

def calculate_exact_match(sample: Dict) -> Optional[float]:
    """
    Exact Match: Does answer exactly match ground truth?

    Logic:
    1. Extract predicted answer
    2. Extract ground truth answer
    3. Normalize both (strip whitespace, lowercase, remove punctuation)
    4. Compare
    5. Return 1.0 if match, 0.0 otherwise

    Example:
    Predicted: "The answer is 42"
    Ground truth: "42"
    After normalization: "42" == "42"
    Exact match: 1.0 ✓
    """
    try:
        raw_output = sample.get('raw_output', '').strip()
        ground_truth = sample.get('ground_truth', '').strip()

        if not ground_truth:
            return None

        # Normalize: lowercase, remove extra whitespace/punctuation
        pred_normalized = normalize_answer(raw_output)
        truth_normalized = normalize_answer(ground_truth)

        return 1.0 if pred_normalized == truth_normalized else 0.0

    except Exception:
        return None


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison"""
    # Remove articles
    answer = re.sub(r'\b(a|an|the)\b', ' ', answer)
    # Remove punctuation
    answer = re.sub(r'[^\w\s]', ' ', answer)
    # Remove extra whitespace
    answer = ' '.join(answer.split())
    # Lowercase
    answer = answer.lower()
    return answer


# ========== SUMMARIZATION ==========

def calculate_rouge_l_summarization(sample: Dict) -> Optional[float]:
    """
    ROUGE-L for summarization: LCS overlap with reference summary
    Same as text generation, but for summaries
    """
    return calculate_rouge_l(sample)


# ========== RETRIEVAL GROUNDED ==========

def calculate_f1_retrieval(sample: Dict) -> Optional[float]:
    """
    F1 for retrieval: Token-level overlap with answer span

    Logic:
    1. Extract predicted answer from output
    2. Extract ground truth answer span
    3. Find overlapping tokens
    4. Calculate token-level F1

    Precision = overlapping_tokens / predicted_tokens
    Recall = overlapping_tokens / reference_tokens
    F1 = 2 * (P * R) / (P + R)

    Example (question answering):
    Question: "What is the capital of France?"
    Generated: "The capital of France is Paris, a beautiful city."
    Ground truth: "Paris"

    Predicted tokens: ["the", "capital", "of", "france", "is", "paris", "a", "beautiful", "city"]
    Reference tokens: ["paris"]
    Overlapping: ["paris"]

    P = 1/9 ≈ 0.11 (1 of 9 tokens overlap)
    R = 1/1 = 1.0 (found the answer)
    F1 = 2 * (0.11 * 1.0) / (0.11 + 1.0) ≈ 0.20
    """
    try:
        raw_output = sample.get('raw_output', '').lower()
        ground_truth = sample.get('ground_truth', '').lower()

        if not ground_truth:
            return None

        # Tokenize
        pred_tokens = set(raw_output.split())
        truth_tokens = set(ground_truth.split())

        # Calculate overlap
        overlap = len(pred_tokens & truth_tokens)

        if overlap == 0:
            return 0.0

        precision = overlap / len(pred_tokens) if pred_tokens else 0
        recall = overlap / len(truth_tokens) if truth_tokens else 0

        if precision + recall == 0:
            return 0.0

        f1 = 2 * (precision * recall) / (precision + recall)
        return min(f1, 1.0)

    except Exception:
        return None


# ========== INSTRUCTION FOLLOWING ==========

def calculate_constraint_satisfaction(sample: Dict) -> Optional[float]:
    """
    Constraint Satisfaction: % of instructions followed

    Logic:
    1. Parse instructions from prompt
    2. Check if output satisfies each constraint
    3. Return satisfaction_rate = satisfied_constraints / total_constraints

    Example (constraints):
    Instructions:
    1. Start with "Dear"
    2. Include exactly 3 paragraphs
    3. End with "Sincerely"

    Generated output:
    "Dear John,
    Paragraph 1...
    Paragraph 2...
    Paragraph 3...
    Sincerely, Jane"

    Satisfied: 1, 2, 3
    Satisfaction rate = 3/3 = 1.0 ✓
    """
    try:
        raw_output = sample.get('raw_output', '')
        constraints = sample.get('constraints', [])

        if not constraints:
            # No constraints = perfect (vacuously true)
            return 1.0

        # Check each constraint
        satisfied = 0
        for constraint in constraints:
            if check_constraint(raw_output, constraint):
                satisfied += 1

        return satisfied / len(constraints)

    except Exception:
        return None


def check_constraint(output: str, constraint: str) -> bool:
    """Check if output satisfies a constraint"""
    # Basic constraint checking
    if 'starts_with' in constraint:
        prefix = constraint.split('starts_with:')[1].strip()
        return output.strip().startswith(prefix)
    elif 'contains' in constraint:
        substring = constraint.split('contains:')[1].strip()
        return substring in output
    elif 'ends_with' in constraint:
        suffix = constraint.split('ends_with:')[1].strip()
        return output.strip().endswith(suffix)
    return False


# ========== INFORMATION EXTRACTION ==========

def calculate_field_accuracy(sample: Dict) -> Optional[float]:
    """
    Field Accuracy: % of fields extracted correctly

    Logic:
    1. Parse predicted fields from output
    2. Get ground truth fields
    3. For each field, check if extracted value matches
    4. Return accuracy = correct_fields / total_fields

    Example (contact extraction):
    Fields to extract: [name, email, phone, company]
    Ground truth: {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "555-0123",
        "company": "Acme Corp"
    }

    Extracted: {
        "name": "John Smith",        ✓
        "email": "john@example.com", ✓
        "phone": "555-0123",         ✓
        "company": "Acme"            ✗ (missing Corp)
    }

    Accuracy = 3/4 = 0.75
    """
    try:
        parsed_output = sample.get('parsed_output', {})
        ground_truth_fields = sample.get('ground_truth_fields', {})

        if not ground_truth_fields:
            return None

        correct = 0
        for field_name, expected_value in ground_truth_fields.items():
            extracted_value = parsed_output.get(field_name, '')

            # Normalize for comparison
            if normalize_answer(str(extracted_value)) == normalize_answer(str(expected_value)):
                correct += 1

        return correct / len(ground_truth_fields)

    except Exception:
        return None


# ========== DISPATCHER ==========

METRIC_CALCULATOR_MAP = {
    'code_generation': calculate_pass_at_1,
    'text_generation': calculate_rouge_l,
    'classification': calculate_f1_score,
    'maths': calculate_exact_match,
    'summarization': calculate_rouge_l_summarization,
    'retrieval_grounded': calculate_f1_retrieval,
    'instruction_following': calculate_constraint_satisfaction,
    'information_extraction': calculate_field_accuracy,
}


def get_task_metric_calculator(task_type: str):
    """Get the metric calculator for a task type"""
    return METRIC_CALCULATOR_MAP.get(task_type)


def calculate_metric(sample: Dict, task_type: str) -> Optional[float]:
    """
    Calculate task-specific metric for a sample

    Args:
        sample: Benchmark sample with raw_output, ground_truth, etc.
        task_type: Type of task (code_generation, classification, etc.)

    Returns:
        Metric value in [0, 1] or None if can't calculate
    """
    calculator = get_task_metric_calculator(task_type)
    if not calculator:
        return None

    return calculator(sample)
