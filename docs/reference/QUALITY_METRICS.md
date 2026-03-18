# Computing Quality-Based Risk Curves: Practical Implementation

## Overview

Instead of manually computing severity-weighted failures, use your existing `primary_metric` values to calculate risk directly from benchmark outputs.

## Per-Task Implementation

### Task 1: Text Generation

**Data Location**: `text_generation/results/runs/*/sddf/outputs.jsonl`

**Quality Metric**: `constraint_satisfaction_rate` (continuous [0, 1])

**Quality Threshold**: 0.80

```python
def compute_text_generation_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where constraint_satisfaction_rate < 0.80
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        quality_scores = []

        for sample in samples:
            # Extract constraint satisfaction from metrics
            metrics = sample.get('metrics', {})
            framework = metrics.get('framework', {})
            instruction = framework.get('instruction_following', {})
            csr = instruction.get('constraint_satisfaction_rate', 0.0)
            quality_scores.append(csr)

        # Count failures (below threshold)
        failures = sum(1 for q in quality_scores if q < 0.80)
        risk = failures / len(quality_scores) if quality_scores else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Low risk (0-7%) for all models on text generation (constraint satisfaction is easy)

---

### Task 2: Code Generation

**Data Location**: `code_generation/archive/runs/*/outputs.jsonl`

**Quality Metric**: `int(bool(passed))` (binary: 0=fail, 1=pass)

**Quality Threshold**: 1.0

```python
def compute_code_generation_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where tests_passed == False

    Note: For binary metric, this directly gives failure rate
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        test_passed = []

        for sample in samples:
            # Check if code passed tests
            passed = sample.get('passed', False)
            test_passed.append(passed)

        # Count failures
        failures = sum(1 for p in test_passed if not p)
        risk = failures / len(test_passed) if test_passed else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: High risk (18-54%) for SLMs on code generation (tests failing is common)

---

### Task 3: Classification

**Data Location**: `classification/results/*/outputs.jsonl` or equivalent

**Quality Metric**: `int(prediction == reference)` (binary: 0=wrong, 1=correct)

**Quality Threshold**: 1.0

```python
def compute_classification_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where prediction != reference
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        correct = []

        for sample in samples:
            prediction = sample.get('prediction')
            reference = sample.get('reference')
            correct.append(prediction == reference)

        # Count failures
        failures = sum(1 for c in correct if not c)
        risk = failures / len(correct) if correct else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Near-zero risk (0%) for all models on classification

---

### Task 4: Maths

**Data Location**: `maths/results/*/outputs.json`

**Quality Metric**: `int(bool(correct))` (binary: 0=wrong, 1=correct)

**Quality Threshold**: 1.0

```python
def compute_maths_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where answer is incorrect
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        correct_flags = []

        for sample in samples:
            # Get correctness from base.correct or similar
            base = sample.get('base', {})
            correct = bool(base.get('correct', False))
            correct_flags.append(correct)

        # Count failures
        failures = sum(1 for c in correct_flags if not c)
        risk = failures / len(correct_flags) if correct_flags else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Near-zero risk (0%) for all models on maths

---

### Task 5: Summarization

**Data Location**: `Summarization/results/*/outputs.json`

**Quality Metric**: `rouge_1_f1` (continuous [0, 1])

**Quality Threshold**: 0.80

```python
def compute_summarization_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where ROUGE F1 < 0.80
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        rouge_scores = []

        for sample in samples:
            # Extract ROUGE F1 score
            rouge_1_f1 = sample.get('rouge_1_f1', 0.0)
            rouge_scores.append(rouge_1_f1)

        # Count failures
        failures = sum(1 for r in rouge_scores if r < 0.80)
        risk = failures / len(rouge_scores) if rouge_scores else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Low risk (0%) for all models on summarization

---

### Task 6: Retrieval Grounded QA

**Data Location**: `Retrieval_grounded/results/*/outputs.jsonl`

**Quality Metric**: `int(exact_match)` (binary: 0=wrong, 1=exact match)

**Quality Threshold**: 1.0

```python
def compute_retrieval_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where answer doesn't exactly match reference
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        exact_matches = []

        for sample in samples:
            prediction = str(sample.get('prediction', '')).strip()
            reference = str(sample.get('reference', '')).strip()
            exact_matches.append(prediction == reference)

        # Count failures
        failures = sum(1 for em in exact_matches if not em)
        risk = failures / len(exact_matches) if exact_matches else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Low risk (0%) for all models on retrieval

---

### Task 7: Instruction Following

**Data Location**: `instruction_following/results/*/outputs.json`

**Quality Metric**: `constraints_satisfied / constraints_total` (continuous [0, 1])

**Quality Threshold**: 0.80

```python
def compute_instruction_following_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where (constraints_satisfied / constraints_total) < 0.80
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        constraint_rates = []

        for sample in samples:
            total = sample.get('total_constraints', 0) or 0
            satisfied = sample.get('constraints_satisfied', 0) or 0

            if total > 0:
                rate = satisfied / total
            else:
                rate = 1.0  # If no constraints, assume success

            constraint_rates.append(rate)

        # Count failures
        failures = sum(1 for r in constraint_rates if r < 0.80)
        risk = failures / len(constraint_rates) if constraint_rates else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Low risk (0-7%) for all models on instruction following

---

### Task 8: Information Extraction

**Data Location**: `Information Extraction/results/*/outputs.jsonl`

**Quality Metric**: F1 score (continuous [0, 1])

**Quality Threshold**: 0.80

```python
def compute_information_extraction_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where F1 < 0.80
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        f1_scores = []

        for sample in samples:
            # Compute F1 from predictions vs reference
            prediction = sample.get('prediction', {})
            reference = sample.get('reference', {})

            # Simple F1: count matching fields
            target_fields = ['field1', 'field2']  # Adjust per your task
            correct = 0
            predicted = 0
            truth = 0

            for field in target_fields:
                pred_val = str(prediction.get(field, '')).strip()
                ref_val = str(reference.get(field, '')).strip()

                if pred_val:
                    predicted += 1
                if ref_val:
                    truth += 1
                if pred_val == ref_val:
                    correct += 1

            precision = correct / predicted if predicted > 0 else 0
            recall = correct / truth if truth > 0 else 0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            f1_scores.append(f1)

        # Count failures
        failures = sum(1 for f in f1_scores if f < 0.80)
        risk = failures / len(f1_scores) if f1_scores else 0
        risks[bin_id] = risk

    return risks
```

**Expected Pattern**: Low risk (0%) for all models on information extraction

---

## Unified Implementation

Create a single function that computes risk for all tasks:

```python
def compute_quality_risk_curves(task_name, outputs_by_bin, quality_threshold=0.80):
    """
    Compute quality-based risk curves for any task

    Args:
        task_name: One of the 8 tasks
        outputs_by_bin: {bin_id: [samples]}
        quality_threshold: Threshold for acceptable quality

    Returns:
        {bin_id: risk_0_to_1}
    """
    QUALITY_METRICS = {
        'text_generation': lambda s: s.get('metrics', {}).get('framework', {})
                                     .get('instruction_following', {})
                                     .get('constraint_satisfaction_rate', 0.0),
        'code_generation': lambda s: float(bool(s.get('passed', False))),
        'classification': lambda s: float(s.get('prediction') == s.get('reference')),
        'maths': lambda s: float(bool(s.get('base', {}).get('correct', False))),
        'summarization': lambda s: s.get('rouge_1_f1', 0.0),
        'retrieval_grounded': lambda s: float(
            str(s.get('prediction', '')).strip() == str(s.get('reference', '')).strip()
        ),
        'instruction_following': lambda s: (
            s.get('constraints_satisfied', 0) / s.get('total_constraints', 1)
            if s.get('total_constraints', 0) > 0 else 1.0
        ),
        'information_extraction': lambda s: s.get('f1_score', 0.0),
    }

    QUALITY_THRESHOLDS = {
        'text_generation': 0.80,
        'code_generation': 1.0,
        'classification': 1.0,
        'maths': 1.0,
        'summarization': 0.80,
        'retrieval_grounded': 1.0,
        'instruction_following': 0.80,
        'information_extraction': 0.80,
    }

    quality_fn = QUALITY_METRICS.get(task_name)
    threshold = QUALITY_THRESHOLDS.get(task_name, quality_threshold)

    if not quality_fn:
        raise ValueError(f"Unknown task: {task_name}")

    risks = {}
    for bin_id, samples in sorted(outputs_by_bin.items()):
        if not samples:
            risks[bin_id] = None
            continue

        # Compute quality scores
        qualities = []
        for sample in samples:
            try:
                q = quality_fn(sample)
                qualities.append(q)
            except:
                qualities.append(0)  # Treat errors as failure

        # Count failures (below threshold)
        failures = sum(1 for q in qualities if q < threshold)
        risk = failures / len(qualities) if qualities else 0
        risks[bin_id] = risk

    return risks
```

## Integration with Framework

Update `two_tipping_point_framework.py`:

```python
def load_risk_curves_from_outputs(self):
    """Compute risk curves from actual outputs using quality metrics"""
    print("\n[Computing Risk Curves from Quality Metrics]")

    for task in TASKS:
        for model_key, model_name in MODELS.items():
            # Load outputs
            path = BENCHMARK_DIR / task / model_key / "outputs.jsonl"
            if not path.exists():
                continue

            # Bin by difficulty
            binned = self._load_and_bin_outputs(path)

            # Compute quality-based risk
            risks = compute_quality_risk_curves(task, binned)
            self.risk_curves[(task, model_key)] = risks

            risk_str = [f'{r:.1%}' if r is not None else 'N/A' for r in risks.values()]
            print(f"  {task:25s} × {model_name:20s}: {risk_str}")

def _load_and_bin_outputs(self, path):
    """Load outputs and bin by difficulty"""
    binned = defaultdict(list)
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            bin_id = record.get('bin', 0)
            binned[bin_id].append(record)
    return dict(binned)
```

## Comparison: Old vs New Values

**Before (Severity-Weighted)**:
```
code_generation, Qwen: [0.333, 0.200, 0.200, 0.333, 0.267]
                        (weighted severity of failures)
```

**After (Quality Threshold)**:
```
code_generation, Qwen: [0.333, 0.200, 0.200, 0.333, 0.267]
                        (fraction of tests that fail)
```

For binary metrics (code, maths, classification), both approaches give similar numbers because severity of a failure = 1.0 when it fails the binary test.

For continuous metrics (text gen, summarization), the new approach captures "below quality threshold" instead of "failure with weighted severity".

## Testing

```bash
# Compute new risk curves and compare to old
python compute_quality_risks.py --task code_generation --model qwen2.5_1.5b

# Should output:
# Bin 0: 33.3% of samples have primary_metric < 1.0 (tests fail)
# Bin 1: 20.0% of samples have primary_metric < 1.0
# Bin 2: 20.0% of samples have primary_metric < 1.0
# Bin 3: 33.3% of samples have primary_metric < 1.0
# Bin 4: 26.7% of samples have primary_metric < 1.0
```

This replaces the old "0.333 weighted severity" with "33.3% failure rate", which is more actionable.
