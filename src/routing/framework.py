#!/usr/bin/env python3
"""
Generalized Two-Tipping-Point Routing Framework

Applies the size-first routing decision matrix to ANY task, not just the 8 we studied.

Key concept: The framework is task-agnostic. Provide:
1. Task specification (name, validation logic)
2. Difficulty binning metric (what makes a sample "hard")
3. Raw outputs from models
4. Risk classification (structural vs semantic)

And it will:
1. Compute capability curves P̂_m(d)
2. Compute risk curves Risk_m(d)
3. Detect two tipping points (τ_cap, τ_risk)
4. Apply risk-first, then capability-first routing
5. Generate routing policy
"""

import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Tuple, Optional
import statistics
import math

from src.utils.stats import wilson_interval


@dataclass
class TaskSpec:
    """Specification for a custom task"""
    name: str
    validation_fn: Callable[[str], bool]  # Returns True if output is valid
    difficulty_metric: Callable[[str], float]  # Returns difficulty score [0, 1]
    quality_metric: Optional[Callable[[Dict], float]] = field(default=None)  # Returns quality score [0, 1] from sample
    quality_threshold: float = 0.80  # Threshold for acceptable quality (0.80 or 1.0)
    num_bins: int = 5  # Default: 5 difficulty bins (0-4)


@dataclass
class RoutingDecision:
    """Routing decision for a task"""
    task: str
    model: str
    quadrant: str
    tau_cap: Optional[int]
    tau_risk: Optional[int]
    capability_gap: float  # vs LLM baseline
    avg_risk: float
    recommended_model: str
    confidence: str  # HIGH, MEDIUM, LOW


class GeneralizedRoutingFramework:
    """
    Apply two-tipping-point framework to any task/model combination

    Usage:
        # Define custom task
        def validate_my_task(output):
            return len(output.strip()) > 10

        def difficulty_of_sample(sample_text):
            return len(sample_text) / 1000  # Normalize to [0,1]

        task_spec = TaskSpec(
            name="my_task",
            validation_fn=validate_my_task,
            difficulty_metric=difficulty_of_sample
        )

        # Run framework
        router = GeneralizedRoutingFramework(
            capability_threshold=0.80,
            risk_threshold=0.20
        )

        decision = router.analyze_task(
            task_spec,
            outputs_by_model={'qwen': [...], 'llama': [...]}
        )
    """

    # Severity weights (from semantic failure analysis)
    SEVERITY_WEIGHTS = {
        "critical": 1.0,    # timeout, empty_output, token_limit, syntax_error
        "high": 0.8,        # execution_error, logic_error, wrong_label
        "medium": 0.5,      # incomplete_output, reasoning_error, hallucination
        "low": 0.2,         # too_short, too_long, low_relevance
        None: 0.0
    }

    def __init__(self, capability_threshold=0.80, risk_threshold=0.20):
        self.capability_threshold = capability_threshold
        self.risk_threshold = risk_threshold

    def difficulty_to_bin_probabilities(self, difficulty_score: float,
                                        num_bins: int = 5) -> Dict[int, float]:
        """
        Convert difficulty score to probabilistic bin assignment

        Uses linear interpolation near bin boundaries for smooth probability distribution

        Args:
            difficulty_score: 0.0 to 1.0
            num_bins: Number of bins (default 5)

        Returns:
            {bin_id: probability} - sums to 1.0

        Example:
            score = 0.249 (near boundary at 0.25)
            → {0: 0.996, 1: 0.004, 2: 0.0, 3: 0.0, 4: 0.0}

            score = 0.25 (exactly on boundary)
            → {0: 1.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        """
        # Clamp to [0, 1]
        difficulty_score = max(0.0, min(1.0, difficulty_score))

        # Map to continuous position [0, num_bins-1]
        bin_position = difficulty_score * (num_bins - 1)

        # Hard bins
        lower_bin = int(bin_position)
        upper_bin = min(lower_bin + 1, num_bins - 1)

        # Interpolation factor: 0.0 to 1.0
        fraction = bin_position - lower_bin

        # Distribute probability between lower and upper bin
        bin_probs = {}
        for bin_id in range(num_bins):
            if bin_id == lower_bin:
                bin_probs[bin_id] = 1.0 - fraction
            elif bin_id == upper_bin and upper_bin != lower_bin:
                bin_probs[bin_id] = fraction
            else:
                bin_probs[bin_id] = 0.0

        return bin_probs
    def bin_by_difficulty(self, samples: List[Dict],
                         difficulty_metric: Callable,
                         num_bins: int = 5) -> Dict[int, List[Dict]]:
        """
        Bin samples by difficulty metric (DETERMINISTIC for grouping)

        Used during Phase 0 analysis to group samples for statistics.
        Each sample assigned to its most likely bin (argmax of probabilities).

        Args:
            samples: List of sample dicts with 'raw_input' and 'raw_output'
            difficulty_metric: Function(input_text) -> float in [0, 1]
            num_bins: Number of difficulty bins

        Returns:
            {bin_id: [samples]}
        """
        # Pre-initialize all bins so callers can rely on presence of 0..num_bins-1
        # even if no samples fall into a particular bucket. Tests expect bins to
        # exist, not just the ones that received assignments.
        binned = defaultdict(list, {i: [] for i in range(num_bins)})

        for sample in samples:
            try:
                # Get difficulty score from input
                input_text = sample.get('raw_input', '')
                difficulty_score = difficulty_metric(input_text)

                # Get probabilistic bin assignment
                bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

                # Assign to most likely bin (argmax)
                bin_id = max(bin_probs, key=bin_probs.get)

                # Store both deterministic bin and probabilistic assignment
                sample['_bin_id'] = bin_id
                sample['_bin_probs'] = bin_probs
                sample['_difficulty_score'] = difficulty_score

                binned[bin_id].append(sample)
            except Exception as e:
                # If difficulty computation fails, skip sample
                continue

        return dict(binned)

    def compute_capability_curve(self, samples_by_bin: Dict[int, List],
                                validation_fn: Callable) -> Dict[int, float]:
        """
        Compute P̂_m(d) = accuracy per bin

        Returns:
            ({bin_id: accuracy_0_to_1}, {bin_id: sample_count})
        """
        capabilities = {}
        counts = {}

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]

            valid_count = 0
            for sample in samples:
                output = sample.get('raw_output', '')
                try:
                    if validation_fn(output):
                        valid_count += 1
                except:
                    pass

            accuracy = valid_count / len(samples) if samples else 0
            capabilities[bin_id] = accuracy

            counts[bin_id] = len(samples)

        return capabilities, counts

    def compute_risk_curve(self, samples_by_bin: Dict[int, List],
                          quality_metric: Optional[Callable] = None,
                          quality_threshold: float = 0.80) -> Dict[int, float]:
        """
        Compute Risk_m(d) as semantic/task-quality weighted failure risk per bin.

        Preferred behavior:
        - Use explicit semantic/structural failure labels when present.
        - Fall back to task-quality shortfall when a quality metric exists.
        - Fall back again to severity-weighted invalid outputs when richer signals
          are unavailable.

        Returns:
            ({bin_id: risk_0_to_1}, {bin_id: sample_count})
        """
        risks = {}
        counts = {}
        taxonomy = None
        try:
            from src.routing.failure_taxonomy import FailureTaxonomy
            taxonomy = FailureTaxonomy()
        except Exception:
            taxonomy = None

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]
            total_weight = 0.0

            for sample in samples:
                sample_weight = 0.0
                quality_score = None
                if quality_metric is not None:
                    try:
                        quality_score = float(quality_metric(sample))
                    except Exception:
                        quality_score = None

                is_valid = bool(sample.get('valid', True))
                has_quality_failure = (
                    quality_score is None or quality_score < quality_threshold
                ) if quality_metric is not None else False
                is_failure = (not is_valid) or has_quality_failure

                explicit_failure_type = sample.get("failure_type")
                if taxonomy is not None and ((not is_valid) or explicit_failure_type):
                    taxonomy_sample = dict(sample)
                    taxonomy_sample["valid"] = False
                    failure_type = taxonomy.categorize_failure(taxonomy_sample)
                    if failure_type:
                        severity = taxonomy.get_failure_severity(failure_type)
                        sample_weight = taxonomy.SEVERITY_WEIGHTS.get(severity, 0.0)

                if sample_weight == 0.0 and not is_valid:
                    severity = sample.get('severity', None)
                    sample_weight = self.SEVERITY_WEIGHTS.get(severity, 1.0 if is_failure else 0.0)

                if sample_weight == 0.0 and has_quality_failure:
                    if quality_score is None:
                        sample_weight = 1.0
                    else:
                        shortfall = (quality_threshold - quality_score) / max(quality_threshold, 1e-9)
                        sample_weight = max(0.0, min(1.0, shortfall))

                total_weight += sample_weight

            risk = total_weight / len(samples) if samples else 0

            risks[bin_id] = risk

            counts[bin_id] = len(samples)

        return risks, counts

    def compute_expected_capability(self, difficulty_score: float,
                                   capability_curve: Dict[int, float],
                                   num_bins: int = 5) -> float:
        """
        Compute expected capability using probabilistic bin assignment

        E[capability] = Σ_k P(bin_k | difficulty) × P(success | bin_k)

        Args:
            difficulty_score: 0.0 to 1.0
            capability_curve: {bin_id: accuracy}
            num_bins: Number of bins

        Returns:
            Expected capability (0.0 to 1.0)

        Example:
            difficulty = 0.249 (near bin boundary)
            capability = {0: 0.85, 1: 0.80, ...}
            → 0.996 × 0.85 + 0.004 × 0.80 = 0.8495
        """
        bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

        expected_capability = 0.0
        for bin_id, prob_bin in bin_probs.items():
            capability_given_bin = capability_curve.get(bin_id, 0.5)
            expected_capability += prob_bin * capability_given_bin

        return expected_capability

    def compute_expected_risk(self, difficulty_score: float,
                             risk_curve: Dict[int, float],
                             num_bins: int = 5) -> float:
        """
        Compute expected risk using probabilistic bin assignment

        E[risk] = Σ_k P(bin_k | difficulty) × P(failure | bin_k)

        Args:
            difficulty_score: 0.0 to 1.0
            risk_curve: {bin_id: risk}
            num_bins: Number of bins

        Returns:
            Expected risk (0.0 to 1.0)

        Example:
            difficulty = 0.249
            risk = {0: 0.15, 1: 0.20, ...}
            → 0.996 × 0.15 + 0.004 × 0.20 = 0.1504
        """
        bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

        expected_risk = 0.0
        for bin_id, prob_bin in bin_probs.items():
            risk_given_bin = risk_curve.get(bin_id, 0.5)
            expected_risk += prob_bin * risk_given_bin

        return expected_risk

    def detect_tipping_points(self, capability_curve: Dict[int, float],
                             risk_curve: Dict[int, float],
                             num_bins: int = 5,
                             capability_counts: Optional[Dict[int, int]] = None,
                             risk_counts: Optional[Dict[int, int]] = None,
                             min_samples: int = 5,
                             alpha: float = 0.05) -> Tuple[Optional[int], Optional[int]]:
        """
        Detect two tipping points

        τ_cap = max{d : P̂_m(d) ≥ threshold}
        τ_risk = min{d : Risk_m(d) > threshold}

        Returns:
            (tau_cap, tau_risk)
        """
        z = 1.96 if alpha == 0.05 else 1.64

        expected_capabilities = {}
        expected_risks = {}
        for d in range(num_bins):
            difficulty_mid = d / max(1, (num_bins - 1))
            expected_capabilities[d] = self.compute_expected_capability(difficulty_mid, capability_curve, num_bins)
            expected_risks[d] = self.compute_expected_risk(difficulty_mid, risk_curve, num_bins)

        # Capability tipping point: last bin where lower CI >= threshold
        tau_cap = None
        for d in range(num_bins):
            cap = expected_capabilities.get(d, 0.0)
            n = (capability_counts or {}).get(d, 0)
            if n < min_samples:
                continue
            lower, _ = wilson_interval(cap, n, z)
            if lower is not None and lower >= self.capability_threshold:
                tau_cap = d

        # Risk tipping point: first bin where lower CI of risk >= threshold
        tau_risk = None
        for d in range(num_bins):
            risk = expected_risks.get(d, 0.0)
            n = (risk_counts or {}).get(d, 0)
            if n < min_samples:
                continue
            lower, _ = wilson_interval(risk, n, z)
            if lower is not None and lower >= self.risk_threshold:
                tau_risk = d
                break

        return tau_cap, tau_risk

    def classify_quadrant(self, tau_cap: Optional[int], tau_risk: Optional[int],
                         capability_gap: float, avg_risk: float) -> str:
        """
        Map the two-threshold outcome into legacy internal labels.

        The canonical presentation is risk-first, then capability.
        Q1/Q2/Q3/Q4 remain as compatibility labels for existing callers/tests.
        """
        if tau_cap is not None and tau_cap < 4:
            if tau_risk is not None and tau_risk <= tau_cap:
                return "Q4"  # Both fail early
            else:
                return "Q3"  # Cap fails, risk OK
        else:
            # tau_cap is 4 or None
            if tau_risk is not None and tau_risk < 4:
                return "Q2"  # Capable but risky
            else:
                return "Q1"  # Safe throughout

    def analyze_task(self, task_spec: TaskSpec,
                    outputs_by_model: Dict[str, List[Dict]],
                    llm_baseline: Optional[str] = None) -> Dict[str, RoutingDecision]:
        """
        Analyze task across all models and generate routing decisions

        Args:
            task_spec: Task specification with validation and difficulty logic
            outputs_by_model: {model_name: [output_records]}
            llm_baseline: Optional LLM baseline for capability gap computation

        Returns:
            {model_name: RoutingDecision}
        """
        decisions = {}

        # Bin by difficulty for each model (hard bins for reporting; soft for calc)
        binned_by_model = {}
        taxonomy_by_model = {}
        for model_name, outputs in outputs_by_model.items():
            binned = self.bin_by_difficulty(
                outputs,
                task_spec.difficulty_metric,
                task_spec.num_bins
            )
            binned_by_model[model_name] = binned

            # Optional: failure taxonomy
            try:
                from src.routing.failure_taxonomy import FailureTaxonomy
                taxonomy = FailureTaxonomy()
                failure_analysis = taxonomy.analyze_failures_by_bin(binned)
                weighted_risks = taxonomy.compute_weighted_risk_by_bin(failure_analysis)
                taxonomy_by_model[model_name] = {
                    "failure_analysis": failure_analysis,
                    "weighted_risks": weighted_risks,
                }
            except Exception:
                taxonomy_by_model[model_name] = None

        # Compute curves for each model
        capabilities = {}
        risks = {}
        expected_caps = {}
        expected_risks = {}

        for model_name, binned in binned_by_model.items():
            cap_curve, cap_counts = self.compute_capability_curve(binned, task_spec.validation_fn)
            risk_curve, risk_counts = self.compute_risk_curve(
                binned,
                quality_metric=task_spec.quality_metric,
                quality_threshold=task_spec.quality_threshold
            )

            capabilities[model_name] = cap_curve
            risks[model_name] = risk_curve

            # Expected (soft) curves sampled at bin midpoints for storage
            exp_cap = {d: self.compute_expected_capability(d / max(1, task_spec.num_bins - 1), cap_curve, task_spec.num_bins)
                       for d in range(task_spec.num_bins)}
            exp_risk = {d: self.compute_expected_risk(d / max(1, task_spec.num_bins - 1), risk_curve, task_spec.num_bins)
                        for d in range(task_spec.num_bins)}
            expected_caps[model_name] = exp_cap
            expected_risks[model_name] = exp_risk

            # Store counts for CI gating
            binned_by_model[model_name] = {
                "bins": binned,
                "cap_counts": cap_counts,
                "risk_counts": risk_counts,
                "taxonomy": taxonomy_by_model.get(model_name),
            }

        # Detect tipping points and classify
        for model_name in outputs_by_model.keys():
            cap_curve = capabilities[model_name]
            risk_curve = risks[model_name]
            cap_counts = binned_by_model[model_name]["cap_counts"]
            risk_counts = binned_by_model[model_name]["risk_counts"]

            tau_cap, tau_risk = self.detect_tipping_points(
                cap_curve, risk_curve, task_spec.num_bins, cap_counts, risk_counts
            )

            # Compute capability gap vs LLM
            capability_gap = 0.0
            if llm_baseline and model_name != llm_baseline:
                llm_cap = capabilities.get(llm_baseline, {})
                gaps = []
                for d in range(task_spec.num_bins):
                    if d in cap_curve and d in llm_cap:
                        gaps.append(llm_cap[d] - cap_curve[d])
                if gaps:
                    capability_gap = statistics.mean(gaps)

            # Compute average risk
            valid_risks = [r for r in risk_curve.values() if r is not None]
            avg_risk = statistics.mean(valid_risks) if valid_risks else 0

            # Preserve legacy quadrant labels for compatibility with existing callers.
            quadrant = self.classify_quadrant(tau_cap, tau_risk, capability_gap, avg_risk)

            # Determine routing
            if quadrant == "Q1":
                routing = model_name  # Use this SLM
                confidence = "HIGH"
            elif quadrant == "Q2":
                routing = "llama"  # Risky, use LLM
                confidence = "MEDIUM"
            elif quadrant == "Q3":
                routing = "hybrid"  # Try SLM, fallback
                confidence = "MEDIUM"
            else:  # Q4
                routing = "llama"  # Incapable, use LLM
                confidence = "HIGH"

            decision = RoutingDecision(
                task=task_spec.name,
                model=model_name,
                quadrant=quadrant,
                tau_cap=tau_cap,
                tau_risk=tau_risk,
                capability_gap=capability_gap,
                avg_risk=avg_risk,
                recommended_model=routing,
                confidence=confidence
            )

            decisions[model_name] = decision

        # Persist learned thresholds back to outputs_by_model (sidecar)
        for model_name in outputs_by_model.keys():
            outputs_by_model[model_name].append({
                "_learned_tau_cap": decisions[model_name].tau_cap,
                "_learned_tau_risk": decisions[model_name].tau_risk
            })

        return {
            "decisions": decisions,
            "capability_curves": capabilities,
            "risk_curves": risks,
            "expected_capability": expected_caps,
            "expected_risk": expected_risks,
            "cap_counts": {m: binned_by_model[m]["cap_counts"] for m in outputs_by_model.keys()},
            "risk_counts": {m: binned_by_model[m]["risk_counts"] for m in outputs_by_model.keys()},
            "taxonomy": {m: binned_by_model[m]["taxonomy"] for m in outputs_by_model.keys()},
        }

    def generate_policy(self, decisions: Dict[str, RoutingDecision]) -> str:
        """Generate human-readable routing policy"""
        if not decisions:
            return "No decisions to report"

        task_name = list(decisions.values())[0].task

        policy = f"""
ROUTING POLICY FOR TASK: {task_name}
{'='*70}

"""

        # Group by the legacy compatibility labels.
        by_quadrant = defaultdict(list)
        for model, decision in decisions.items():
            by_quadrant[decision.quadrant].append((model, decision))

        for quadrant in ["Q1", "Q2", "Q3", "Q4"]:
            if quadrant not in by_quadrant:
                continue

            policy += f"\n{quadrant}:\n"
            policy += "-" * 70 + "\n"

            for model, decision in by_quadrant[quadrant]:
                policy += f"  {model:20s} tau_cap={decision.tau_cap}  tau_risk={decision.tau_risk}  gap={decision.capability_gap:+.1%}  risk={decision.avg_risk:.1%}  -> {decision.recommended_model}\n"

        # Recommendation
        q1_models = [m for m, d in by_quadrant.get("Q1", []) if m != "llama_llama-3.3-70b-versatile"]

        if q1_models:
            recommended = min(q1_models, key=lambda m: decisions[m].avg_risk)
            policy += f"\nRECOMMENDATION: Deploy {recommended} (risk/capability gates pass)\n"
        else:
            policy += f"\nRECOMMENDATION: Use Llama-70B (no safe SLM found)\n"

        return policy


# ============================================================================
# EXAMPLE: Custom Task Analysis
# ============================================================================

def example_custom_task():
    """
    Example: Analyzing a custom task with the generalized framework
    """

    # Define task specification
    def validate_output(output: str) -> bool:
        """Output must be non-empty and > 20 chars"""
        return len(output.strip()) > 20

    def difficulty_of_input(input_text: str) -> float:
        """Difficulty = input length normalized to [0, 1]"""
        # Assume inputs range from 100-2000 chars
        normalized = min(len(input_text) / 2000.0, 1.0)
        return normalized

    task_spec = TaskSpec(
        name="custom_analysis",
        validation_fn=validate_output,
        difficulty_metric=difficulty_of_input,
        num_bins=5
    )

    # Simulate outputs from different models
    # (In practice, these would be loaded from actual inference logs)
    outputs_qwen = [
        {
            'raw_input': 'short',  # Easy
            'raw_output': 'This is a valid output' * 3,
            'valid': True,
            'severity': None
        },
        {
            'raw_input': 'x' * 1500,  # Hard
            'raw_output': 'too short',  # Failed validation
            'valid': False,
            'severity': 'high'
        },
    ]

    outputs_llama = [
        {
            'raw_input': 'short',
            'raw_output': 'This is a valid llama output' * 3,
            'valid': True,
            'severity': None
        },
        {
            'raw_input': 'x' * 1500,
            'raw_output': 'This is also valid from llama' * 3,
            'valid': True,
            'severity': None
        },
    ]

    # Run analysis
    router = GeneralizedRoutingFramework()
    decisions = router.analyze_task(
        task_spec,
        {
            'qwen': outputs_qwen,
            'llama': outputs_llama,
        },
        llm_baseline='llama'
    )

    # Print results
    policy = router.generate_policy(decisions)
    print(policy)


if __name__ == "__main__":
    print("Generalized Two-Tipping-Point Routing Framework\n")
    print("This framework can analyze ANY task using a custom specification.\n")
    print("Example output:\n")
    example_custom_task()
