"""Failure taxonomy utilities used by the SDDF reporting pipeline."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional


class FailureTaxonomy:
    """Analyze failure types and severity levels per difficulty bin."""

    STRUCTURAL_SEVERITY = {
        "timeout": "critical",
        "empty_output": "critical",
        "token_limit": "critical",
        "syntax_error": "critical",
        "parse_error": "critical",
        "json_error": "high",
        "format_error": "high",
        "execution_error": "high",
    }

    SEMANTIC_SEVERITY = {
        "logic_error": "high",
        "wrong_label": "high",
        "arithmetic_error": "high",
        "answer_mismatch": "high",
        "reasoning_error": "medium",
        "incomplete_output": "medium",
        "missing_field": "medium",
        "constraint_violation": "medium",
        "hallucination": "medium",
        "low_relevance": "low",
        "too_short": "low",
        "too_long": "low",
        "no_answer": "high",
        "quality_failure": "low",
    }

    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
        None: 0.0,
    }

    def categorize_failure(self, sample: Dict) -> Optional[str]:
        failure_type = sample.get("failure_type")
        if failure_type:
            return str(failure_type)

        if sample.get("valid", True):
            return None

        raw_output = str(sample.get("raw_output", "") or "")
        if not raw_output.strip():
            return "empty_output"
        if len(raw_output.split()) < 3:
            return "too_short"
        if sample.get("exceeded_token_limit", False):
            return "token_limit"
        return "quality_failure"

    def get_failure_severity(self, failure_type: str) -> str:
        if failure_type in self.STRUCTURAL_SEVERITY:
            return self.STRUCTURAL_SEVERITY[failure_type]
        if failure_type in self.SEMANTIC_SEVERITY:
            return self.SEMANTIC_SEVERITY[failure_type]
        return "low"

    def analyze_failures_by_bin(self, samples_by_bin: Dict[int, List[Dict]]) -> Dict:
        analysis = {}
        for bin_id, samples in sorted(samples_by_bin.items()):
            total = len(samples)
            if total == 0:
                continue

            failures = 0
            by_type = defaultdict(int)
            by_severity = defaultdict(int)
            for sample in samples:
                failure_type = self.categorize_failure(sample)
                if not failure_type:
                    continue
                failures += 1
                by_type[failure_type] += 1
                by_severity[self.get_failure_severity(failure_type)] += 1

            analysis[bin_id] = {
                "total": total,
                "failures": failures,
                "failure_rate": failures / total,
                "by_type": dict(by_type),
                "by_severity": dict(by_severity),
            }
        return analysis

    def compute_weighted_risk_by_bin(self, analysis: Dict) -> Dict[int, float]:
        weighted = {}
        for bin_id, stats in analysis.items():
            total = int(stats.get("total", 0))
            if total <= 0:
                weighted[bin_id] = 0.0
                continue
            score = 0.0
            for failure_type, count in stats.get("by_type", {}).items():
                sev = self.get_failure_severity(str(failure_type))
                score += self.SEVERITY_WEIGHTS.get(sev, 0.0) * float(count)
            weighted[bin_id] = score / total
        return weighted


__all__ = ["FailureTaxonomy"]
