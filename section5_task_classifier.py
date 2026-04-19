#!/usr/bin/env python3
"""
SECTION 5: Task Family Classification via Zero-Shot Transformer (PyTorch-only)

Maps arbitrary query prompts to primary task family using zero-shot NLI classification.
Uses roberta-large-mnli: PyTorch-native, avoids TensorFlow dependencies.

Output: primary_task_family, confidence_score

Run: python section5_task_classifier.py --demo
     python section5_task_classifier.py --query "your query here"
"""

import json
import sys
from pathlib import Path
from typing import Dict, Tuple
from dataclasses import dataclass
import logging

try:
    from transformers import pipeline
    import torch
except ImportError as e:
    print(f"ERROR: Required packages not installed.")
    print(f"Run: pip install transformers torch")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TASK FAMILY DEFINITIONS
# ============================================================================

TASK_FAMILIES = [
    "classification",
    "code_generation",
    "information_extraction",
    "instruction_following",
    "maths",
    "retrieval_grounded",
    "summarization",
    "text_generation",
]

TASK_FAMILY_DESCRIPTIONS = {
    "classification": "Assign a predefined category or label",
    "code_generation": "Write or generate source code",
    "information_extraction": "Extract named entities and facts",
    "instruction_following": "Follow specific format requirements",
    "maths": "Solve equations and math problems",
    "retrieval_grounded": "Answer using provided document context",
    "summarization": "Create a shorter summary",
    "text_generation": "Create new prose or narrative",
}


@dataclass
class TaskClassificationResult:
    """Result of Section 5 task family classification"""
    query: str
    primary_task_family: str
    confidence: float
    all_scores: Dict[str, float]
    method: str = "zero-shot-transformer"


# ============================================================================
# SECTION 5: ZERO-SHOT TRANSFORMER CLASSIFIER (PYTORCH-ONLY)
# ============================================================================

class TaskFamilyClassifier:
    """Classify queries to task families using zero-shot NLI (PyTorch-native)"""

    def __init__(self, model_name: str = "roberta-large-mnli", device: int = -1):
        """
        Initialize zero-shot classifier with PyTorch-only model.

        Args:
            model_name: HuggingFace model ID (PyTorch-native models)
              - "roberta-large-mnli": 355M params, high accuracy, recommended
              - "microsoft/xlm-roberta-large-mnli": 550M params, multilingual
              - "cross-encoder/nli-roberta-base": 125M params, faster, still good
            device: GPU device index (-1 = CPU, 0 = GPU:0, etc.)
        """
        logger.info(f"Loading zero-shot classifier: {model_name}")
        logger.info(f"Device: {'CPU' if device == -1 else f'GPU:{device}'}")

        try:
            # Force PyTorch framework, avoid TensorFlow
            self.classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=device,
                framework="pt",  # CRITICAL: Force PyTorch only
            )
            self.model_name = model_name
            logger.info("Classifier loaded successfully (PyTorch)")

        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")
            logger.info("Retrying with cross-encoder/nli-roberta-base...")
            self.classifier = pipeline(
                "zero-shot-classification",
                model="cross-encoder/nli-roberta-base",
                device=device,
                framework="pt",
            )
            self.model_name = "cross-encoder/nli-roberta-base"
            logger.info("Fallback classifier loaded (PyTorch)")

    def classify(self, query: str) -> TaskClassificationResult:
        """
        Classify a query to its primary task family using zero-shot NLI.

        Args:
            query: The query/prompt to classify

        Returns:
            TaskClassificationResult with primary family and confidence
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Use descriptions as hypotheses for NLI-based zero-shot
        # Format: "This text is about: <description>"
        hypotheses = [
            f"This text is about: {TASK_FAMILY_DESCRIPTIONS[tf]}"
            for tf in TASK_FAMILIES
        ]

        # Run zero-shot classification
        # multi_label=False means each query gets one best label
        result = self.classifier(query, hypotheses, multi_label=False)

        # Parse results: labels are the hypothesis texts, need to map back to task families
        returned_labels = result["labels"]  # Full hypothesis text returned
        scores = result["scores"]  # Confidence scores [0, 1]

        # Map returned hypotheses back to task family names
        hypothesis_to_task = {
            f"This text is about: {TASK_FAMILY_DESCRIPTIONS[tf]}": tf
            for tf in TASK_FAMILIES
        }

        # Extract task family names from returned labels
        labels = [hypothesis_to_task.get(hyp, hyp) for hyp in returned_labels]

        # Build score dict {task: confidence}
        all_scores = {label: float(score) for label, score in zip(labels, scores)}

        # Primary = highest scoring
        primary_task = labels[0]
        primary_confidence = float(scores[0])

        return TaskClassificationResult(
            query=query,
            primary_task_family=primary_task,
            confidence=primary_confidence,
            all_scores=all_scores,
            method="zero-shot-transformer",
        )

    def classify_batch(self, queries: list[str]) -> list[TaskClassificationResult]:
        """Classify multiple queries"""
        return [self.classify(q) for q in queries]


# ============================================================================
# DEMO & TESTING
# ============================================================================

def demo_section5():
    """Demonstrate Section 5 task family classification with zero-shot transformer"""

    print("\n" + "=" * 80)
    print("SECTION 5: TASK FAMILY CLASSIFICATION (Zero-Shot Transformer, PyTorch-only)")
    print("=" * 80)

    classifier = TaskFamilyClassifier()

    # Test queries representing each task family
    test_queries = [
        # classification
        "Determine whether this movie review is positive or negative: 'Absolutely brilliant film!'",
        # code_generation
        "Write a Python function that finds the longest substring without repeating characters",
        # information_extraction
        "Extract all person names, locations, and dates from the following text: ...",
        # instruction_following
        "Follow these steps: 1) Read the input, 2) Process each line, 3) Output in JSON format",
        # maths
        "Solve for x: 2x + 5 = 15. Show all steps.",
        # retrieval_grounded
        "Based on the provided document, what are the main benefits of this product?",
        # summarization
        "Summarize the following long article in 2-3 sentences",
        # text_generation
        "Write a creative short story about a detective solving a mysterious case",
    ]

    print("\nClassifying 8 test queries (one per task family):\n")
    print(f"{'Query':<60} | {'Primary Task':<20} | {'Confidence':<10}")
    print("-" * 95)

    results = []
    for query in test_queries:
        result = classifier.classify(query)
        results.append(result)
        query_short = (query[:57] + "...") if len(query) > 60 else query
        print(
            f"{query_short:<60} | {result.primary_task_family:<20} | {result.confidence:.4f}"
        )

    # Detailed view of first result
    print("\n" + "-" * 80)
    print("DETAILED: First Result (Classification Task)")
    print("-" * 80)
    result = results[0]
    print(f"Query: {result.query}\n")
    print(f"Primary Task Family: {result.primary_task_family}")
    print(f"Confidence: {result.confidence:.4f}")
    print(f"Method: {result.method}\n")
    print("All Task Family Scores (ranked by confidence):")
    for task, score in sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True):
        bar = "=" * int(score * 30)
        print(f"  {task:<25} {score:.4f} {bar}")

    # Accuracy check
    print("\n" + "-" * 80)
    print("ACCURACY CHECK")
    print("-" * 80)
    expected = TASK_FAMILIES
    predicted = [r.primary_task_family for r in results]
    correct = sum(1 for e, p in zip(expected, predicted) if e == p)
    print(f"Correctly classified: {correct}/{len(expected)}")
    for i, (exp, pred, result) in enumerate(zip(expected, predicted, results)):
        match = "OK" if exp == pred else "XX"
        print(f"  {match} Expected {exp:<25} Got {pred:<25} (conf={result.confidence:.4f})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Section 5: Task Family Classifier (Zero-Shot)")
    parser.add_argument("--query", default=None, help="Single query to classify")
    parser.add_argument("--demo", action="store_true", help="Run demo on 8 test queries")
    parser.add_argument("--model", default="roberta-large-mnli", help="HuggingFace model")
    parser.add_argument("--device", type=int, default=-1, help="GPU device (-1=CPU)")
    args = parser.parse_args()

    if args.demo or not args.query:
        demo_section5()
    else:
        classifier = TaskFamilyClassifier(model_name=args.model, device=args.device)
        result = classifier.classify(args.query)
        print(json.dumps(
            {
                "query": result.query,
                "primary_task_family": result.primary_task_family,
                "confidence": result.confidence,
                "all_scores": result.all_scores,
                "method": result.method,
            },
            indent=2,
        ))
