# Issue Fixes - Detailed Solutions

---

## Issue 12: Gamma & Alpha Task-Constants Fix

### Problem
```python
# CURRENT (BAD): Task-constant values
def calculate_constraint_count(self, sample, task_type):
    if task_type == 'code_generation':
        return 0.2  # Same for ALL code samples!
    elif task_type == 'maths':
        return 0.1  # Same for ALL math samples!
```

Result: Zero variance → correlation = NaN

### Solution: Sample-Specific Extraction

**For Gamma (Output Constraint Count):**

Extract actual structural complexity from output:

```python
def calculate_constraint_count(self, sample, task_type):
    """
    Output constraint count |Γ| - infer from actual output structure
    Count: number of structural rules/slots required in output
    """
    parsed_output = sample.get('parsed_output', {})

    if task_type == 'code_generation':
        # Number of code blocks = number of functions/classes to implement
        code_blocks = parsed_output.get('code_blocks', [])
        num_functions = len(code_blocks)
        # Typical: 1-3 functions per task
        return min(num_functions / 3.0, 1.0)

    elif task_type == 'maths':
        # Math outputs with multiple operations = higher constraint
        numbers_found = parsed_output.get('numbers_found', [])
        num_values = len(numbers_found)
        # Typical: 3-10 intermediate values extracted
        return min(num_values / 10.0, 1.0)

    elif task_type == 'classification':
        # Classification has binary constraint (one label)
        return 0.2

    elif task_type in ['summarization', 'text_generation']:
        # Length constraint + style constraint
        return 0.3

    else:
        # Default fallback
        return 0.3

def calculate_alpha(self, sample, task_type):
    """
    Parametric dependence ᾱ - infer from output content
    How much external world knowledge is needed (vs context-only)
    """
    raw_output = sample.get('raw_output', '').lower()
    raw_input = sample.get('raw_input', '').lower()

    if task_type == 'code_generation':
        # External dependencies = libraries/APIs needed
        external_indicators = [
            'import ', 'from ', 'numpy', 'pandas', 'scipy',
            'requests', 'torch', 'tensorflow', 'sklearn'
        ]
        num_external = sum(1 for ind in external_indicators if ind in raw_output)
        # 0-5 external libraries possible
        return min(num_external / 5.0, 1.0)

    elif task_type == 'maths':
        # Math typically low alpha (uses only context)
        # Unless references external constants (pi, e, etc)
        has_constants = any(c in raw_output for c in ['pi', 'euler', 'sqrt'])
        return 0.2 if not has_constants else 0.4

    elif task_type == 'retrieval_grounded':
        # Should be low alpha (QA from context only)
        answer_in_input = raw_output[:50] in raw_input or \
                         raw_input in raw_output
        return 0.1 if answer_in_input else 0.3

    elif task_type == 'classification':
        # Label depends on training knowledge
        return 0.5

    elif task_type == 'summarization':
        # Summary uses mostly input, some knowledge
        return 0.2

    else:
        return 0.4
```

### Maths Verification

**For Gamma in Code Generation:**
- Sample 1: 1 code block → Gamma = 1/3 = 0.33 ✓
- Sample 2: 2 code blocks → Gamma = 2/3 = 0.67 ✓
- Sample 3: 3 code blocks → Gamma = 3/3 = 1.0 ✓
**Variance**: 0.33 → 0.67 → 1.0 ✅ NOW HAS VARIANCE

**For Alpha in Code Generation:**
- Sample 1: No imports → Alpha = 0/5 = 0.0 ✓
- Sample 2: Uses numpy → Alpha = 1/5 = 0.2 ✓
- Sample 3: Uses numpy+pandas → Alpha = 2/5 = 0.4 ✓
**Variance**: 0.0 → 0.2 → 0.4 ✅ NOW HAS VARIANCE

---

## Issue 13: Explain Weak Correlations (r = ±0.11)

### Why Correlations Are Weak

**Evidence**:
- Code Gen: r = -0.115 (p = 0.44, not significant)
- Math: r = +0.114 (p = 0.39, not significant)

### Root Causes (5 Factors)

#### 1. Small Sample Size
```
Current: 47-60 verifiable samples per task
Needed: ~200-300 for correlation confidence
Impact: Large standard errors, weak significance
```

#### 2. High Noise in Component Extraction
```
R (reasoning depth) extraction is heuristic:
├─ Code: Count nesting depth (proxy for complexity)
├─ Math: Count input length (proxy for steps)
└─ Problem: These proxies are rough approximations
```

#### 3. Single-Component Analysis
```
Problem: Analyzing components in isolation
├─ Reality: Multiple components affect failure
├─ Example: High R + Low Alpha might = high failure
│          but High R + High Alpha might = low failure
└─ Solution: Multi-component regression (not implemented)
```

#### 4. Missing Confounding Factors
```
Factors NOT captured by SDDF that affect failure:
├─ Model training data (Qwen trained on code, Math trained on text)
├─ Model architecture biases
├─ Prompt format matching (better if similar to training)
├─ Randomness in model outputs
└─ Example: Model A fails code despite low complexity (training gap)
```

#### 5. Ceiling Effects in Easy Tasks
```
Example - Maths task:
├─ Samples with R=0.1 (easy math): 100% pass rate
├─ Samples with R=0.2 (medium math): 95% pass rate
├─ Samples with R=0.3 (hard math): 60% pass rate
└─ BUT: Most samples are easy (R=0.1)
   Result: Weak overall correlation despite strong trend
```

### Expected Improvement After Fix

**Current (with Gamma/Alpha constants)**:
- Only R has variance
- r ≈ ±0.11 (weak, p > 0.1)

**After Fix (with sample-specific Gamma/Alpha)**:
- All 3 components have variance
- Can capture: "High Gamma + High R = failure"
- Expected: r ≈ ±0.25 to ±0.45 (moderate, likely p < 0.05)

**Further improvement needs**:
- Multi-component regression (combine R, Gamma, Alpha)
- Larger sample sizes (300+ samples)
- Model-specific analysis (Qwen vs Phi vs TinyLlama)

---

## Issue 7: Learned Thresholds (Not Hard-Coded)

### Current Problem
```python
def find_capability_threshold(self, capability_curve):
    for bin_id in valid_bins:
        if capability_curve[bin_id] < 0.8:  # HARD-CODED 0.8
            return bin_id
    return None
```

**Issue**: 0.8 same for all tasks
- Text Gen might need 0.85 (harder task)
- Classification might accept 0.75 (easier task)
- Not data-driven

### Solution: Learn Per-Task Thresholds

**Step 1: Compute threshold from data**
```python
def learn_task_thresholds(self, all_results):
    """
    Compute task-specific thresholds from model performance

    Threshold = capability level where models start struggling
    = mean(tau_cau across all models for this task)
    """
    thresholds = {}

    for task, models_data in all_results.items():
        tau_values = []

        for model, analysis in models_data.items():
            capability_curve = analysis.get('capability_curve', {})

            # Find where THIS model's capability drops below 0.8
            for bin_id, cap in sorted(capability_curve.items()):
                if cap is not None and cap < 0.8:
                    tau_values.append(bin_id)
                    break

        if tau_values:
            # Learned threshold = mean bin where models struggle
            mean_tau = statistics.mean(tau_values)
            learned_capability_threshold = 0.8 - (mean_tau * 0.05)  # Scale
            thresholds[task] = {
                'tau_cau': mean_tau,
                'capability_threshold': learned_capability_threshold
            }
        else:
            # Default if all models pass all bins
            thresholds[task] = {
                'tau_cau': 4,  # No failure
                'capability_threshold': 0.8
            }

    return thresholds
```

**Step 2: Store learned thresholds**
```python
# In config.py or learned_thresholds.json
LEARNED_THRESHOLDS = {
    'code_generation': {'tau_cau': 2, 'capability_threshold': 0.8},
    'maths': {'tau_cau': 3, 'capability_threshold': 0.85},
    'text_generation': {'tau_cau': 1, 'capability_threshold': 0.75},
    'classification': {'tau_cau': 4, 'capability_threshold': 0.9},
    # ... etc
}
```

**Step 3: Use learned thresholds in plotting**
```python
def plot_capability_curves(self, task_type, results, learned_thresholds):
    threshold = learned_thresholds.get(task_type, {}).get('capability_threshold', 0.8)

    for model, analysis in results.items():
        capability_curve = analysis.get('capability_curve', {})

        # Find threshold using LEARNED value, not hard-coded 0.8
        for bin_id in sorted(capability_curve.keys()):
            if capability_curve[bin_id] < threshold:
                # Mark this bin
                break
```

---

## Issue 14: Silent Exception Handling Fix

### Current Problem
```python
# BAD: Silently swallows errors
try:
    outputs.append(json.loads(line))
except:
    continue  # Silent failure!
```

Problems:
- Don't know what failed
- Can't debug
- Could hide data corruption

### Solution: Proper Error Logging

**Option 1: Add logging**
```python
import logging

logger = logging.getLogger(__name__)

def load_outputs(self, task_type: str, model: str) -> List[Dict]:
    """Load JSONL output file"""
    benchmark_dir = self.get_benchmark_dir(task_type)
    output_file = benchmark_dir / task_type / model / "outputs.jsonl"

    if not output_file.exists():
        logger.warning(f"Output file not found: {output_file}")
        return []

    outputs = []
    try:
        with open(output_file) as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        outputs.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse line {line_num} in {output_file}: {str(e)}"
                        )
                        continue
    except IOError as e:
        logger.error(f"Failed to read {output_file}: {str(e)}")
        return []

    return outputs
```

**Option 2: Track error counts**
```python
def load_outputs(self, task_type: str, model: str) -> Dict:
    """Load JSONL output file"""
    benchmark_dir = self.get_benchmark_dir(task_type)
    output_file = benchmark_dir / task_type / model / "outputs.jsonl"

    outputs = []
    errors = []

    if not output_file.exists():
        return {'outputs': [], 'error': f'File not found: {output_file}'}

    try:
        with open(output_file) as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        outputs.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        errors.append({
                            'line': line_num,
                            'error': str(e),
                            'sample': line[:50]
                        })
    except IOError as e:
        return {'outputs': [], 'error': f'IO error: {str(e)}'}

    return {
        'outputs': outputs,
        'total_lines': len(outputs) + len(errors),
        'parsed': len(outputs),
        'failed': len(errors),
        'errors': errors if errors else None
    }
```

**Locations to fix** (6+ places):
- sddf_complexity_calculator.py: line 104, 106
- sddf_complexity_calculator.py: line 444
- sddf_risk_analyzer.py: line 61
- semantic_verifier.py: line ~300
- semantic_component_learner.py: line ~100

---

## Issue 15: Hard-Coded Paths Fix

### Current Problem
```python
# HARD-CODED in multiple files
base_dir = Path(__file__).parent.parent.parent.parent.parent
weights_file = base_dir / "data/config/learned_sddf_weights.json"
```

Problems:
- Path breaks if code moves
- Can't test from different directory
- Not portable across systems

### Solution: Environment Variable + Config File

**Step 1: Create config file**
```python
# config.py - in framework/risk_sensitivity/src/
import os
from pathlib import Path

# Get project root from environment or calculate from code location
PROJECT_ROOT = Path(os.getenv(
    'SLM_PROJECT_ROOT',
    Path(__file__).parent.parent.parent.parent.parent
))

# Validate it exists
if not (PROJECT_ROOT / "data/benchmark").exists():
    raise RuntimeError(
        f"Project root not found at {PROJECT_ROOT}\n"
        "Set SLM_PROJECT_ROOT environment variable"
    )

# All paths relative to root
PATHS = {
    'benchmark_output': PROJECT_ROOT / "data/benchmark/benchmark_output",
    'benchmark_fixed': PROJECT_ROOT / "data/benchmark/benchmark_output_fixed",
    'benchmark_fixed_all': PROJECT_ROOT / "data/benchmark/benchmark_output_fixed_all",
    'config': PROJECT_ROOT / "data/config",
    'learned_weights': PROJECT_ROOT / "data/config/learned_sddf_weights.json",
    'output_plots': PROJECT_ROOT / "framework/risk_sensitivity/outputs/plots",
}

def get_benchmark_dir(task_type: str) -> Path:
    """Get benchmark directory for task"""
    if task_type == 'text_generation':
        return PATHS['benchmark_fixed']
    elif task_type in ['code_generation', 'summarization']:
        return PATHS['benchmark_fixed_all']
    else:
        return PATHS['benchmark_output']
```

**Step 2: Use config in code**
```python
# Instead of: base_dir = Path(__file__).parent.parent.parent.parent.parent
# Use:
from config import PATHS, get_benchmark_dir

class SDDFComplexityCalculator:
    def get_benchmark_dir(self, task_type: str) -> Path:
        return get_benchmark_dir(task_type)

    def _load_learned_weights(self) -> dict:
        weights_file = PATHS['learned_weights']
        # ... rest of code
```

**Step 3: Set environment variable (optional)**
```bash
# In shell or .env file
export SLM_PROJECT_ROOT="/path/to/SLM use cases"

# Then code auto-uses correct root
python script.py
```

**Benefits**:
- ✅ Code works from any directory
- ✅ Works in Docker/CI/CD
- ✅ Easy to override for testing
- ✅ Single source of truth for paths

---

## Summary of Fixes

| Issue | Complexity | Time | Critical? |
|-------|-----------|------|-----------|
| 12. Gamma/Alpha | Medium | 1 hour | ✅ YES |
| 13. Explain | Low | N/A (done) | No |
| 7. Learned Thresholds | Medium | 1 hour | No |
| 14. Error Handling | Low | 30 min | No |
| 15. Hard-coded Paths | Low | 45 min | No |

**Total**: ~3.5 hours for all fixes

**Critical Path**: Issue 12 → Issue 13 improves → Phase 3 runs better
