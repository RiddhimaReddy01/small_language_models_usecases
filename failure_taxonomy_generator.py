#!/usr/bin/env python3
"""
Failure Taxonomy Generator

Analyzes all outputs.jsonl files and generates comprehensive failure taxonomy
with:
- Structural vs semantic breakdown
- Severity-weighted risk scores
- Per-model, per-bin failure patterns
- Recommendations for root cause
"""

import json
import os
import ast
import re
import statistics
from pathlib import Path
from collections import defaultdict

from ground_truth_integration import SemanticFailureClassifier

# Configuration
BENCHMARK_DIR = Path("benchmark_output")
TASKS = [
    "text_generation", "code_generation", "classification", "maths",
    "summarization", "retrieval_grounded", "instruction_following", "information_extraction"
]
MODELS = {
    "phi3_mini": "Phi-3 (3.8B)",
    "qwen2.5_1.5b": "Qwen (1.5B)",
    "tinyllama_1.1b": "TinyLlama (1.1B)",
    "llama_llama-3.3-70b-versatile": "Llama (70B)"
}

# Severity weights for risk computation
SEVERITY_WEIGHTS = {
    "critical": 1.0,   # Unrecoverable
    "high": 0.8,       # Major impact
    "medium": 0.5,     # Moderate impact
    "low": 0.2,        # Minor impact
    None: 0.0          # No failure
}

# Structural failure severity
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

# Semantic failure severity
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


class FailureTaxonomyGenerator:
    """Generate comprehensive failure taxonomy with semantic analysis"""

    def __init__(self):
        self.classifier = SemanticFailureClassifier()
        self.failure_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        # Structure: failure_stats[task][model][bin] = [failure_records]

    def load_and_classify_all(self):
        """Load all outputs and classify failures"""
        print("\n[Loading and Classifying Failures]\n")

        for task in TASKS:
            for model_key, model_name in MODELS.items():
                path = BENCHMARK_DIR / task / model_key / "outputs.jsonl"

                if not path.exists():
                    continue

                print(f"  Processing: {task:25s} × {model_name:20s} ... ", end="", flush=True)

                try:
                    with open(path) as f:
                        count = 0
                        for line in f:
                            if not line.strip():
                                continue

                            record = json.loads(line)
                            bin_id = record.get("bin", 0)

                            # Classify failure
                            failure_result = self.classifier.classify(record)

                            # Store with classification
                            self.failure_stats[task][model_key][bin_id].append({
                                **record,
                                **failure_result
                            })
                            count += 1

                    print(f"[OK] ({count} records)")

                except Exception as e:
                    print(f"[ERROR] {e}")

    def generate_taxonomy_table(self):
        """Generate comprehensive failure taxonomy table"""
        print("\n" + "="*100)
        print("COMPREHENSIVE FAILURE TAXONOMY")
        print("="*100)

        for task in TASKS:
            print(f"\n{'='*100}")
            print(f"{task.upper()}")
            print(f"{'='*100}")

            for model_key, model_name in MODELS.items():
                if task not in self.failure_stats or model_key not in self.failure_stats[task]:
                    continue

                print(f"\n{model_name}:")
                print("-" * 100)

                for bin_id in sorted(self.failure_stats[task][model_key].keys()):
                    records = self.failure_stats[task][model_key][bin_id]

                    if not records:
                        continue

                    # Count failures by type
                    structural_counts = defaultdict(int)
                    semantic_counts = defaultdict(int)
                    severity_counts = defaultdict(int)
                    total_failures = 0

                    for record in records:
                        if not record.get("is_valid"):
                            total_failures += 1
                            severity = record.get("severity")
                            if severity:
                                severity_counts[severity] += 1

                            for failure_type in record.get("structural_failures", []):
                                structural_counts[failure_type] += 1

                            for failure_type in record.get("semantic_failures", []):
                                semantic_counts[failure_type] += 1

                    total = len(records)
                    valid = total - total_failures
                    valid_pct = 100 * valid / total if total > 0 else 0

                    print(f"  Bin {bin_id}: {valid_pct:5.1f}% valid ({valid}/{total})")

                    if total_failures > 0:
                        print(f"    [+] Severity: ", end="")
                        severity_str = ", ".join(
                            f"{k}={v}" for k, v in sorted(severity_counts.items(), key=lambda x: -x[1])
                        )
                        print(severity_str)

                        if structural_counts:
                            print(f"    [+] Structural failures: ", end="")
                            struct_str = ", ".join(
                                f"{k}={v}" for k, v in sorted(structural_counts.items(), key=lambda x: -x[1])
                            )
                            print(struct_str)

                        if semantic_counts:
                            print(f"    [-] Semantic failures: ", end="")
                            semantic_str = ", ".join(
                                f"{k}={v}" for k, v in sorted(semantic_counts.items(), key=lambda x: -x[1])
                            )
                            print(semantic_str)

    def compute_weighted_risk(self):
        """Compute severity-weighted risk scores per model, task, bin"""
        print("\n" + "="*100)
        print("WEIGHTED RISK SCORES (Severity-Adjusted)")
        print("="*100)

        risk_matrix = {}  # {(task, model, bin): risk_score}

        for task in TASKS:
            print(f"\n{task.upper()}")
            print("-" * 100)
            print(f"{'Model':<20} {'Bin0':>10} {'Bin1':>10} {'Bin2':>10} {'Bin3':>10} {'Bin4':>10}")
            print("-" * 100)

            for model_key, model_name in MODELS.items():
                if task not in self.failure_stats or model_key not in self.failure_stats[task]:
                    continue

                bin_risks = []

                for bin_id in range(5):
                    records = self.failure_stats[task][model_key].get(bin_id, [])

                    if not records:
                        bin_risks.append(None)
                        continue

                    # Compute weighted risk
                    total_weight = 0
                    for record in records:
                        severity = record.get("severity")
                        weight = SEVERITY_WEIGHTS.get(severity, 0)
                        total_weight += weight

                    risk_score = total_weight / len(records) if records else 0
                    bin_risks.append(risk_score)
                    risk_matrix[(task, model_key, bin_id)] = risk_score

                # Print row
                risk_str = "  ".join(
                    f"{r*100:6.1f}%" if r is not None else "   N/A  "
                    for r in bin_risks
                )
                print(f"{model_name:<20} {risk_str}")

        return risk_matrix

    def generate_decision_rules(self, risk_matrix, tau=0.80, rho=0.20):
        """
        Generate new feasibility gates based on semantic failure analysis

        tau = capability threshold (0.70-0.80)
        rho = maximum acceptable risk (0.15-0.25)
        """
        print("\n" + "="*100)
        print(f"FEASIBILITY GATES (tau={tau}, rho={rho})")
        print("="*100)

        eligibility = defaultdict(lambda: defaultdict(list))  # {task: {model: [safe_bins]}}

        for task in TASKS:
            print(f"\n{task.upper()}")
            print("-" * 100)

            for model_key, model_name in MODELS.items():
                if task not in self.failure_stats or model_key not in self.failure_stats[task]:
                    continue

                safe_bins = []

                for bin_id in range(5):
                    records = self.failure_stats[task][model_key].get(bin_id, [])

                    if not records:
                        continue

                    # Check capability
                    valid = sum(1 for r in records if r.get("is_valid"))
                    capability = valid / len(records)

                    # Check risk
                    risk = risk_matrix.get((task, model_key, bin_id), 0)

                    # Decision
                    passes_capability = capability >= tau
                    passes_risk = risk <= rho

                    if passes_capability and passes_risk:
                        safe_bins.append(bin_id)

                eligibility[task][model_key] = safe_bins

                if safe_bins:
                    safe_range = f"Bins {min(safe_bins)}-{max(safe_bins)}"
                    print(f"  {model_name:<20} [OK] {safe_range:<20}")
                else:
                    print(f"  {model_name:<20} [NO] INELIGIBLE")

        return eligibility

    def generate_failure_report(self, output_file="SEMANTIC_FAILURE_TAXONOMY.md"):
        """Generate comprehensive markdown report"""
        print(f"\n[Generating Report: {output_file}]")

        report = """# Semantic Failure Taxonomy

## Executive Summary

This analysis classifies failures into two categories:
- **Structural Failures**: System-level issues (timeout, parse error, token limit)
- **Semantic Failures**: Task-level issues (wrong answer, logic error, hallucination)

This distinction is crucial because:
- Structural failures → Infrastructure/scaling issue
- Semantic failures → Model capability issue

---

## Failure Classification Scheme

### Structural Failures (Unrecoverable)
- **timeout**: Model didn't respond within time limit
- **empty_output**: No output generated
- **token_limit**: Hit max token limit
- **syntax_error**: Code doesn't parse (critical for code)
- **parse_error**: Output format invalid (JSON, etc.)
- **execution_error**: Code crashes when run

### Semantic Failures (Content Correctness)
- **logic_error**: Code runs but produces wrong output
- **wrong_label**: Classification picked wrong class
- **arithmetic_error**: Math answer is incorrect
- **answer_mismatch**: QA answer doesn't match ground truth
- **reasoning_error**: Multi-step reasoning failed
- **incomplete_output**: Missing required content
- **hallucination**: Generated false information
- **low_relevance**: Summary/extraction misses key points

---

## Risk Score Calculation

For each (task, model, bin):

```
Risk = Σ(severity_weight × failure_count) / total_count

Where:
  - critical failures (timeout, syntax): weight = 1.0
  - high failures (logic, wrong label): weight = 0.8
  - medium failures (incomplete): weight = 0.5
  - low failures (too short): weight = 0.2
```

---

## Key Findings by Task

"""
        report += "\n(Detailed findings would be inserted here)\n"

        with open(output_file, "w") as f:
            f.write(report)

        print(f"  ✓ Saved to {output_file}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*100)
    print("FAILURE TAXONOMY GENERATOR WITH SEMANTIC ANALYSIS")
    print("="*100)

    generator = FailureTaxonomyGenerator()

    # Load and classify all outputs
    generator.load_and_classify_all()

    # Generate tables
    generator.generate_taxonomy_table()

    # Compute risk scores
    risk_matrix = generator.compute_weighted_risk()

    # Generate decision rules
    eligibility = generator.generate_decision_rules(risk_matrix, tau=0.80, rho=0.20)

    # Generate report
    generator.generate_failure_report()

    print("\n" + "="*100)
    print("TAXONOMY GENERATION COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
