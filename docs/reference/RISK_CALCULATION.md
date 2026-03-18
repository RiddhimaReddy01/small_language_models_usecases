# Risk Calculation Redesign: From Severity-Weighted to Quality-Degradation

## Problem with Old Approach

The original framework used **binary severity-weighted failures**:
- Failures classified as critical (1.0), high (0.8), medium (0.5), low (0.2)
- Risk computed as: weighted sum of failures / total samples
- Issue: Doesn't align with your codebase's continuous quality metrics

## New Approach: Continuous Quality Degradation

Your framework already computes **task-specific quality metrics** as continuous scores [0, 1]:

```python
# From sddf/ingest.py - your actual quality computation

Classification:  primary_metric = float(valid and prediction == reference)
                # Binary: 0 (wrong) or 1 (correct)

Text Generation:  primary_metric = constraint_satisfaction_rate
                  # Continuous: 0-1, how well constraints met

Summarization:    primary_metric = rouge_1_f1
                  # Continuous: 0-1, F1 score

Instruction Fol:  primary_metric = constraints_satisfied / constraints_total
                  # Continuous: 0-1, fraction of constraints

Code Generation:  primary_metric = float(int(bool(passed)))
                  # Binary: 0 (tests fail) or 1 (pass)

Maths:            primary_metric = float(int(bool(correct)))
                  # Binary: 0 (wrong) or 1 (correct)

Retrieval:        primary_metric = float(exact_match)
                  # Binary: 0 (wrong) or 1 (exact match)

Info Extraction:  primary_metric = f1_score
                  # Continuous: 0-1, F1 score
```

## New Risk Calculation

**Risk = Fraction of outputs failing to meet quality threshold**

```
Risk_m(d) = (Count where primary_metric < quality_threshold) / Total samples in bin

Example:
  Bin 0 (easy): 100 samples
  - 90 have primary_metric >= 0.80 (pass)
  - 10 have primary_metric < 0.80 (fail)
  - Risk = 10/100 = 0.10 (10% risk)

  Bin 3 (hard): 100 samples
  - 60 have primary_metric >= 0.80 (pass)
  - 40 have primary_metric < 0.80 (fail)
  - Risk = 40/100 = 0.40 (40% risk)
```

## Thresholds by Task

Based on your gates.py evaluation (line 13: `primary_metric >= quality_threshold`):

| Task | Type | Quality Threshold | Rationale |
|------|------|-------------------|-----------|
| Classification | Binary | 1.0 | Pass/fail only, must be correct |
| Text Generation | Continuous | 0.80 | Must satisfy 80%+ of constraints |
| Summarization | Continuous | 0.80 | ROUGE F1 >= 0.80 is good quality |
| Code Generation | Binary | 1.0 | Tests must pass, no partial credit |
| Maths | Binary | 1.0 | Must be correct, no partial credit |
| Instruction Following | Continuous | 0.80 | Must satisfy 80%+ of constraints |
| Retrieval Grounded | Binary | 1.0 | Must match reference exactly |
| Information Extraction | Continuous | 0.80 | F1 >= 0.80 is acceptable |

## Implementation

### Step 1: Define Quality Metric Function

```python
# Example for text_generation task
def get_text_generation_quality(sample: dict) -> float:
    """Extract primary_metric from sample"""
    return sample.get('primary_metric', 0.0)

# Example for code_generation task
def get_code_quality(sample: dict) -> float:
    """Extract primary_metric from sample"""
    return sample.get('primary_metric', 0.0)
```

### Step 2: Create Task Specification with Quality Threshold

```python
from generalized_routing_framework import TaskSpec, GeneralizedRoutingFramework

# Old approach (severity-weighted)
task_spec_old = TaskSpec(
    name="text_generation",
    validation_fn=lambda output: len(output) > 0,
    difficulty_metric=lambda text: min(len(text) / 1000, 1.0),
    quality_metric=None,  # Will use severity weights as fallback
    quality_threshold=0.80
)

# NEW approach (continuous quality)
def get_text_quality(sample):
    return sample.get('primary_metric', 0.0)

task_spec_new = TaskSpec(
    name="text_generation",
    validation_fn=lambda output: len(output) > 0,
    difficulty_metric=lambda text: min(len(text) / 1000, 1.0),
    quality_metric=get_text_quality,  # Use continuous quality scores
    quality_threshold=0.80  # Risk = fraction < 0.80
)

# Run framework
router = GeneralizedRoutingFramework(
    capability_threshold=0.80,
    risk_threshold=0.20
)

decision = router.analyze_task(task_spec_new, outputs_by_model)
```

### Step 3: Interpret Results

```
OLD APPROACH (binary severity):
Risk_m(0) = 0.33  →  33% of failures are severe
                      (e.g., 1 critical + 1 medium = (1.0 + 0.5) / 3)

NEW APPROACH (quality degradation):
Risk_m(0) = 0.33  →  33% of outputs fail quality threshold
                      (e.g., 33 outputs have primary_metric < 0.80)

Interpretation is clearer:
- OLD: "Failures are weighted at 0.33" (unclear what this means)
- NEW: "1 in 3 outputs don't meet acceptable quality" (actionable)
```

## Key Differences

| Aspect | Old Approach | New Approach |
|--------|-------------|--------------|
| **Data Used** | Severity labels on failures | Continuous quality scores |
| **Interpretation** | Weighted severity per bin | Fraction of unacceptable outputs |
| **Threshold** | risk > 0.20 | failure_rate > 0.20 (20% unacceptable) |
| **Task Alignment** | Generic (any task) | Specific (uses task's quality metric) |
| **Gates.py Alignment** | No direct mapping | Direct: `primary_metric >= threshold` |

## Migration from Old to New

Your codebase measures quality as **continuous primary_metric**, so:

### Old (Generic Severity):
```python
# Any task, weight failures by category
Risk = (1.0 * critical_count + 0.8 * high_count + ...) / total
```

### New (Task-Specific Quality):
```python
# Your actual metric, simple failure count
Risk = (count where primary_metric < 0.80) / total
```

## Why This Matters

1. **Alignment**: Uses the same quality metric your gates.py uses (primary_metric >= threshold)
2. **Clarity**: "33% of outputs below quality threshold" is clearer than "weighted severity 0.33"
3. **Actionability**: Direct feedback on acceptable output rate
4. **Extensibility**: Works for any task that has a primary_metric

## Examples

### Example 1: Text Generation (Continuous)
```
Input: 100 samples, threshold=0.80 (constraint satisfaction)

Model Output Distribution:
- 60 outputs: primary_metric >= 0.80 (acceptable)
- 40 outputs: primary_metric < 0.80 (below threshold)

Risk = 40/100 = 0.40 (40% fail to meet constraint requirement)

Interpretation:
- 2 in 5 text generations don't satisfy constraints well enough
- Actionable: improve constraint handling or use larger model
```

### Example 2: Code Generation (Binary)
```
Input: 100 samples, threshold=1.0 (tests passing)

Model Output Distribution:
- 65 outputs: primary_metric = 1.0 (pass)
- 35 outputs: primary_metric = 0.0 (fail)

Risk = 35/100 = 0.35 (35% tests fail)

Interpretation:
- 7 in 20 generated solutions are broken
- Actionable: unacceptable risk, use LLM instead
```

### Example 3: Classification (Binary)
```
Input: 100 samples, threshold=1.0 (exact correctness)

Model Output Distribution:
- 100 outputs: primary_metric = 1.0 (correct)
- 0 outputs: primary_metric = 0.0 (incorrect)

Risk = 0/100 = 0.0 (0% fail)

Interpretation:
- Perfect accuracy on classification
- Actionable: safe to deploy SLM
```

## API Usage

```python
# The framework now accepts quality_metric in TaskSpec:

task = TaskSpec(
    name="my_task",
    validation_fn=lambda output: output != "",
    difficulty_metric=lambda text: len(text) / 1000,
    quality_metric=lambda sample: sample.get('primary_metric', 0.0),  # NEW
    quality_threshold=0.80  # NEW
)

# During analyze_task(), risk curve is computed as:
# Risk = fraction where quality_metric(sample) < quality_threshold

# If quality_metric is None, falls back to old severity-weighted approach
```

## Summary

The new approach replaces binary severity-weighted failures with your codebase's continuous quality metrics, making risk calculation more aligned with your actual quality evaluation and easier to interpret.

**Key Change**: Risk now directly represents "fraction of outputs failing to meet task-specific quality threshold" instead of "weighted severity of failures".
