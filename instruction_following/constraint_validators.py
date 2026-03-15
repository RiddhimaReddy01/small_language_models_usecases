"""Constraint validators for instruction following evaluation."""
import re
from typing import Dict, List, Tuple
from collections import Counter


class ConstraintValidator:
    """Validates various constraint types from IFEval."""

    @staticmethod
    def check_word_count(text: str, constraint_type: str, value: int) -> bool:
        """Check word count constraints."""
        words = text.split()
        word_count = len(words)

        if constraint_type == "less_than":
            return word_count < value
        elif constraint_type == "at_least":
            return word_count >= value
        elif constraint_type == "at_most":
            return word_count <= value
        elif constraint_type == "exactly":
            return word_count == value
        return False

    @staticmethod
    def check_sentence_count(text: str, constraint_type: str, value: int) -> bool:
        """Check sentence count constraints."""
        sentences = re.split(r'[.!?]+', text.strip())
        sentence_count = len([s for s in sentences if s.strip()])

        if constraint_type == "less_than":
            return sentence_count < value
        elif constraint_type == "at_least":
            return sentence_count >= value
        elif constraint_type == "at_most":
            return sentence_count <= value
        elif constraint_type == "exactly":
            return sentence_count == value
        return False

    @staticmethod
    def check_inclusion(text: str, words: List[str]) -> bool:
        """Check if all words are included in text."""
        text_lower = text.lower()
        return all(word.lower() in text_lower for word in words)

    @staticmethod
    def check_exclusion(text: str, words: List[str]) -> bool:
        """Check if none of the words are in text."""
        text_lower = text.lower()
        return not any(word.lower() in text_lower for word in words)

    @staticmethod
    def check_format(text: str, format_type: str) -> bool:
        """Check formatting constraints."""
        if format_type == "bullets":
            return bool(re.search(r'^\s*[•\-\*]\s', text, re.MULTILINE))
        elif format_type == "numbered":
            return bool(re.search(r'^\s*\d+[\.\)]\s', text, re.MULTILINE))
        elif format_type == "paragraphs":
            return len(text.split('\n\n')) > 1
        return False

    @staticmethod
    def check_letter_frequency(text: str, letter: str, constraint_type: str, value: int) -> bool:
        """Check letter frequency constraints."""
        count = text.lower().count(letter.lower())

        if constraint_type == "at_least":
            return count >= value
        elif constraint_type == "at_most":
            return count <= value
        elif constraint_type == "exactly":
            return count == value
        return False

    @staticmethod
    def validate_constraints(text: str, constraints: List[Dict]) -> Tuple[int, int, Dict]:
        """
        Validate all constraints for a response with detailed metrics.

        Returns:
            Tuple of (satisfied_constraints, total_constraints, detailed_metrics)
        """
        satisfied = 0
        total = len(constraints)
        metrics = {
            "format_satisfied": 0,
            "format_total": 0,
            "length_satisfied": 0,
            "length_total": 0,
            "lexical_satisfied": 0,
            "lexical_total": 0,
            "constraint_violations": [],
        }

        for constraint in constraints:
            constraint_type = constraint.get("type", "")
            is_satisfied = False

            if constraint_type == "length":
                sub_type = constraint.get("length_type", "")
                value = constraint.get("value", 0)
                metrics["length_total"] += 1
                if ConstraintValidator.check_word_count(text, sub_type, value):
                    satisfied += 1
                    is_satisfied = True
                    metrics["length_satisfied"] += 1

            elif constraint_type == "sentence_count":
                sub_type = constraint.get("length_type", "")
                value = constraint.get("value", 0)
                metrics["length_total"] += 1
                if ConstraintValidator.check_sentence_count(text, sub_type, value):
                    satisfied += 1
                    is_satisfied = True
                    metrics["length_satisfied"] += 1

            elif constraint_type == "inclusion":
                words = constraint.get("words", [])
                metrics["lexical_total"] += 1
                if ConstraintValidator.check_inclusion(text, words):
                    satisfied += 1
                    is_satisfied = True
                    metrics["lexical_satisfied"] += 1

            elif constraint_type == "exclusion":
                words = constraint.get("words", [])
                metrics["lexical_total"] += 1
                if ConstraintValidator.check_exclusion(text, words):
                    satisfied += 1
                    is_satisfied = True
                    metrics["lexical_satisfied"] += 1

            elif constraint_type == "format":
                fmt = constraint.get("format", "")
                metrics["format_total"] += 1
                if ConstraintValidator.check_format(text, fmt):
                    satisfied += 1
                    is_satisfied = True
                    metrics["format_satisfied"] += 1

            elif constraint_type == "letter_frequency":
                letter = constraint.get("letter", "")
                sub_type = constraint.get("frequency_type", "")
                value = constraint.get("value", 0)
                metrics["lexical_total"] += 1
                if ConstraintValidator.check_letter_frequency(text, letter, sub_type, value):
                    satisfied += 1
                    is_satisfied = True
                    metrics["lexical_satisfied"] += 1

            if not is_satisfied:
                metrics["constraint_violations"].append({
                    "type": constraint_type,
                    "details": constraint
                })

        return satisfied, total, metrics
