#!/usr/bin/env python3
"""
Step 6: Failure Taxonomy Analysis

Part of Phase 0 (One-Time Analysis Pipeline)

Analyzes WHERE failures occur (by difficulty bin) and WHY they occur (by type)

Input: samples_by_bin from Step 1-2
Output: failure_patterns = {bin_id: {failure_type: count}}
"""

from collections import defaultdict
from typing import Dict, List, Optional, Callable


class FailureTaxonomy:
    """Analyze failure types per difficulty bin"""

    # Failure severity classification
    STRUCTURAL_SEVERITY = {
        "timeout": "critical",
        "empty_output": "critical",
        "token_limit": "critical",
        "syntax_error": "critical",
        "parse_error": "critical",
        "json_error": "high",
        "format_error": "high",
        "execution_error": "high"
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
        "no_answer": "high"
    }

    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
        None: 0.0
    }

    def __init__(self):
        self.failure_patterns = {}  # {bin_id: {failure_type: count}}
        self.severity_patterns = {}  # {bin_id: {severity: count}}

    def categorize_failure(self, sample: Dict) -> Optional[str]:
        """
        Determine failure type from sample

        Returns: failure_type string (e.g., "execution_error", "hallucination")
                or None if not a failure
        """
        # Check for failure type indicators
        failure_type = sample.get('failure_type', None)
        if failure_type:
            return failure_type

        if sample.get('valid', True):
            return None  # Not a failure

        # Infer from sample characteristics
        raw_output = sample.get('raw_output', '')

        if not raw_output or raw_output.strip() == '':
            return "empty_output"
        elif len(raw_output.split()) < 3:
            return "too_short"
        elif sample.get('exceeded_token_limit', False):
            return "token_limit"
        else:
            return "quality_failure"  # Generic quality/accuracy failure

    def get_failure_severity(self, failure_type: str) -> str:
        """Get severity level for a failure type"""
        # Check structural failures
        if failure_type in self.STRUCTURAL_SEVERITY:
            return self.STRUCTURAL_SEVERITY[failure_type]

        # Check semantic failures
        if failure_type in self.SEMANTIC_SEVERITY:
            return self.SEMANTIC_SEVERITY[failure_type]

        # Default
        return "low"

    def analyze_failures_by_bin(self, samples_by_bin: Dict[int, List[Dict]]) -> Dict:
        """
        Analyze failure patterns per difficulty bin

        Args:
            samples_by_bin: {bin_id: [sample_dicts]}

        Returns:
            {
                bin_id: {
                    'total': 100,
                    'failures': 25,
                    'failure_rate': 0.25,
                    'by_type': {
                        'execution_error': 10,
                        'hallucination': 8,
                        'timeout': 5,
                        'other': 2
                    },
                    'by_severity': {
                        'critical': 5,
                        'high': 10,
                        'medium': 8,
                        'low': 2
                    }
                }
            }
        """
        analysis = {}

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]

            total = len(samples)
            if total == 0:
                continue

            # Count failures
            failures = 0
            failure_types = defaultdict(int)
            failure_severities = defaultdict(int)

            for sample in samples:
                failure_type = self.categorize_failure(sample)

                if failure_type:
                    failures += 1
                    failure_types[failure_type] += 1

                    # Get severity
                    severity = self.get_failure_severity(failure_type)
                    failure_severities[severity] += 1

            analysis[bin_id] = {
                'total': total,
                'failures': failures,
                'failure_rate': failures / total,
                'by_type': dict(failure_types),
                'by_severity': dict(failure_severities)
            }

        return analysis

    def compute_weighted_risk_by_bin(self, analysis: Dict) -> Dict[int, float]:
        """
        Compute severity-weighted risk per bin

        weighted_risk = sum(severity_weight * count) / total_samples

        This is MORE SOPHISTICATED than simple failure rate:
        - A timeout (weight=1.0) counts more than a too_short output (weight=0.2)
        """
        weighted_risks = {}

        for bin_id, stats in analysis.items():
            total = stats['total']
            total_weight = 0

            for failure_type, count in stats['by_type'].items():
                severity = self.get_failure_severity(failure_type)
                weight = self.SEVERITY_WEIGHTS.get(severity, 0)
                total_weight += weight * count

            weighted_risk = total_weight / total if total > 0 else 0
            weighted_risks[bin_id] = weighted_risk

        return weighted_risks

    def print_taxonomy_report(self, analysis: Dict, weighted_risks: Dict):
        """Print human-readable failure taxonomy report"""

        print("\n" + "=" * 100)
        print("STEP 6: FAILURE TAXONOMY ANALYSIS")
        print("=" * 100)

        for bin_id in sorted(analysis.keys()):
            stats = analysis[bin_id]
            weighted_risk = weighted_risks.get(bin_id, 0)

            total = stats['total']
            failures = stats['failures']
            failure_rate = stats['failure_rate']

            print(f"\nBin {bin_id} ({total} samples):")
            print(f"  Failure Rate: {failures}/{total} = {failure_rate:.1%}")
            print(f"  Weighted Risk: {weighted_risk:.3f}")

            # Failure types
            if stats['by_type']:
                print(f"  Failure Types:")
                for ftype, count in sorted(
                    stats['by_type'].items(),
                    key=lambda x: -x[1]
                ):
                    pct = 100 * count / failures if failures > 0 else 0
                    severity = self.get_failure_severity(ftype)
                    print(f"    - {ftype:25s}: {count:3d} ({pct:5.1f}%) [severity: {severity}]")

            # Severity distribution
            if stats['by_severity']:
                print(f"  By Severity:")
                for severity, count in sorted(
                    stats['by_severity'].items(),
                    key=lambda x: (
                        {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x[0], 4),
                        -x[1]
                    )
                ):
                    pct = 100 * count / failures if failures > 0 else 0
                    print(f"    - {severity:10s}: {count:3d} ({pct:5.1f}%)")

    def correlate_with_tipping_points(self, weighted_risks: Dict, tau_risk: int) -> Dict:
        """
        Correlate failure taxonomy with risk tipping point

        Returns insights like:
        - "Execution errors increase 40% after τ_risk"
        - "Hallucinations constant across all bins"
        """
        insights = {}

        if tau_risk is None:
            return insights

        # Get failure types before and after τ_risk
        before_tipping = {}
        after_tipping = {}

        # Analyze trends
        for bin_id in sorted(weighted_risks.keys()):
            if bin_id < tau_risk:
                before_tipping[bin_id] = weighted_risks[bin_id]
            else:
                after_tipping[bin_id] = weighted_risks[bin_id]

        if before_tipping and after_tipping:
            avg_before = sum(before_tipping.values()) / len(before_tipping)
            avg_after = sum(after_tipping.values()) / len(after_tipping)
            increase = ((avg_after - avg_before) / avg_before * 100) if avg_before > 0 else 0

            insights['tipping_point_impact'] = {
                'avg_risk_before_tau_risk': avg_before,
                'avg_risk_after_tau_risk': avg_after,
                'percent_increase': increase,
                'interpretation': f"Risk increases {increase:.0f}% after τ_risk"
            }

        return insights


if __name__ == "__main__":
    # Example usage
    print("Failure Taxonomy Module - Use in Phase 0 Analysis Pipeline")
