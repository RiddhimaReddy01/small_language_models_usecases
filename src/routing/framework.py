#!/usr/bin/env python3
"""
Generalized Two-Tipping-Point Routing Framework

Applies the quadrant-based routing decision matrix to ANY task, not just the 8 we studied.

Key concept: The framework is task-agnostic. Provide:
1. Task specification (name, validation logic)
2. Difficulty binning metric (what makes a sample "hard")
3. Raw outputs from models
4. Risk classification (structural vs semantic)

And it will:
1. Compute capability curves P̂_m(d)
2. Compute risk curves Risk_m(d)
3. Detect two tipping points (τ_cap, τ_risk)
4. Classify into quadrant (Q1/Q2/Q3/Q4)
5. Generate routing policy
"""

import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Tuple, Optional
import statistics


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

    def bin_by_difficulty(self, samples: List[Dict],
                         difficulty_metric: Callable,
                         num_bins: int = 5) -> Dict[int, List[Dict]]:
        """
        Bin samples by difficulty metric

        Args:
            samples: List of sample dicts with 'raw_input' and 'raw_output'
            difficulty_metric: Function(input_text) -> float in [0, 1]
            num_bins: Number of difficulty bins

        Returns:
            {bin_id: [samples]}
        """
        binned = defaultdict(list)

        for sample in samples:
            try:
                # Get difficulty score from input
                input_text = sample.get('raw_input', '')
                difficulty_score = difficulty_metric(input_text)

                # Clamp to [0, 1]
                difficulty_score = max(0.0, min(1.0, difficulty_score))

                # Map to bin
                bin_id = int(difficulty_score * (num_bins - 1))
                bin_id = min(bin_id, num_bins - 1)  # Ensure within range

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
            {bin_id: accuracy_0_to_1}
        """
        capabilities = {}

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]

            if not samples:
                continue

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

        return capabilities

    def compute_risk_curve(self, samples_by_bin: Dict[int, List],
                          quality_metric: Optional[Callable] = None,
                          quality_threshold: float = 0.80) -> Dict[int, float]:
        """
        Compute Risk_m(d) = quality failure rate per bin

        NEW APPROACH (recommended): Use continuous quality metrics
        - Risk = fraction of samples where quality_score < quality_threshold
        - Aligns with gates.py evaluation (primary_metric >= threshold)
        - Separates structural failures (valid_output=0) from quality failures

        OLD APPROACH (fallback): Severity-weighted binary failures
        - If quality_metric is None, uses 'severity' field on invalid samples

        Returns:
            {bin_id: risk_0_to_1}
        """
        risks = {}

        for bin_id in sorted(samples_by_bin.keys()):
            samples = samples_by_bin[bin_id]

            if not samples:
                continue

            # NEW APPROACH: Continuous quality degradation
            if quality_metric is not None:
                failure_count = 0
                for sample in samples:
                    try:
                        quality_score = quality_metric(sample)
                        if quality_score < quality_threshold:
                            failure_count += 1
                    except:
                        # If quality computation fails, count as failure
                        failure_count += 1

                risk = failure_count / len(samples) if samples else 0

            # OLD APPROACH: Severity-weighted binary failures (fallback)
            else:
                total_weight = 0
                for sample in samples:
                    is_valid = sample.get('valid', False)

                    if not is_valid:
                        severity = sample.get('severity', None)
                        weight = self.SEVERITY_WEIGHTS.get(severity, 0)
                        total_weight += weight

                risk = total_weight / len(samples) if samples else 0

            risks[bin_id] = risk

        return risks

    def detect_tipping_points(self, capability_curve: Dict[int, float],
                             risk_curve: Dict[int, float]) -> Tuple[Optional[int], Optional[int]]:
        """
        Detect two tipping points

        τ_cap = max{d : P̂_m(d) ≥ threshold}
        τ_risk = min{d : Risk_m(d) > threshold}

        Returns:
            (tau_cap, tau_risk)
        """
        # Capability tipping point: last bin where accuracy >= threshold
        tau_cap = None
        for d in range(5):
            if d in capability_curve and capability_curve[d] >= self.capability_threshold:
                tau_cap = d

        # Risk tipping point: first bin where risk > threshold
        tau_risk = None
        for d in range(5):
            if d in risk_curve and risk_curve[d] > self.risk_threshold:
                tau_risk = d
                break

        return tau_cap, tau_risk

    def classify_quadrant(self, tau_cap: Optional[int], tau_risk: Optional[int],
                         capability_gap: float, avg_risk: float) -> str:
        """
        Classify into Q1/Q2/Q3/Q4 based on tipping points and gaps

        Q1: τ_cap=4, τ_risk=None → Safe + Capable
        Q2: τ_cap=4, τ_risk<4 → Capable + Risky
        Q3: τ_cap<4, τ_risk>τ_cap → Incapable + Safe
        Q4: τ_cap<4, τ_risk≤τ_cap → Incapable + Risky
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
                    llm_baseline: Optional[Dict] = None) -> Dict[str, RoutingDecision]:
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

        # Bin by difficulty for each model
        binned_by_model = {}
        for model_name, outputs in outputs_by_model.items():
            binned = self.bin_by_difficulty(
                outputs,
                task_spec.difficulty_metric,
                task_spec.num_bins
            )
            binned_by_model[model_name] = binned

        # Compute curves for each model
        capabilities = {}
        risks = {}

        for model_name, binned in binned_by_model.items():
            cap_curve = self.compute_capability_curve(binned, task_spec.validation_fn)
            risk_curve = self.compute_risk_curve(
                binned,
                quality_metric=task_spec.quality_metric,
                quality_threshold=task_spec.quality_threshold
            )

            capabilities[model_name] = cap_curve
            risks[model_name] = risk_curve

        # Detect tipping points and classify
        for model_name in outputs_by_model.keys():
            cap_curve = capabilities[model_name]
            risk_curve = risks[model_name]

            tau_cap, tau_risk = self.detect_tipping_points(cap_curve, risk_curve)

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

            # Classify quadrant
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

        return decisions

    def generate_policy(self, decisions: Dict[str, RoutingDecision]) -> str:
        """Generate human-readable routing policy"""
        if not decisions:
            return "No decisions to report"

        task_name = list(decisions.values())[0].task

        policy = f"""
ROUTING POLICY FOR TASK: {task_name}
{'='*70}

"""

        # Group by quadrant
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
        q1_models = [d.model for d in by_quadrant.get("Q1", []) if d.model != "llama_llama-3.3-70b-versatile"]

        if q1_models:
            recommended = min(q1_models, key=lambda m: decisions[m].avg_risk)
            policy += f"\nRECOMMENDATION: Deploy {recommended} (Q1 - safe SLM)\n"
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
