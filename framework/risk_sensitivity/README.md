# SDDF Risk Sensitivity & Tau-Based Routing Framework

**Status**: ✅ Production Ready | **Validation**: ✅ Complete (100% across all configs) | **Version**: 1.0

A complete framework for cost-optimized model routing based on task complexity analysis and validated risk sensitivity measurements.

## Overview

This system analyzes how model performance degrades with task complexity using SDDF difficulty vectors:

```
d(x) = (n_in, H, R̂, |Γ|, α, D)
```

Where each component captures a distinct aspect of task complexity:
- **n_in**: Input token count (Pre-inference)
- **H**: Shannon entropy (Information density)
- **R̂**: Estimated reasoning depth (Post-hoc)
- **|Γ|**: Output constraint count (Structural complexity)
- **α**: Parametric dependence (Knowledge demand)
- **D**: Dependency distance (Syntactic complexity)

## Architecture

### 1. SDDF Complexity Calculator (`sddf_complexity_calculator.py`)

Calculates the 6-component difficulty vector for each sample:

```python
from sddf_complexity_calculator import SDDFComplexityCalculator

calculator = SDDFComplexityCalculator()
results = calculator.analyze_task('text_generation', 'qwen2.5_1.5b')

# Each result contains:
# {
#   'composite_complexity': 0.45,  # Aggregate [0-1]
#   'sddf_vector': {
#     'n_in': 0.3,       # Input size
#     'H': 0.67,         # Entropy
#     'R': 0.4,          # Reasoning depth
#     'constraint_count': 0.2,  # Output constraints
#     'alpha': 0.5,      # Knowledge demand
#     'D': 0.35          # Syntactic complexity
#   }
# }
```

**Features:**
- Extracts SDDF components from benchmark data
- Normalizes to [0, 1] scale
- Computes composite complexity score
- Task-aware heuristics for R̂, |Γ|, α

### 2. SDDF Risk Analyzer (`sddf_risk_analyzer.py`)

Computes P(semantic_failure | complexity) and detects spike points:

```python
from sddf_risk_analyzer import SDDFRiskAnalyzer

analyzer = SDDFRiskAnalyzer()
result = analyzer.analyze_task_model('text_generation', 'qwen2.5_1.5b')

# Output:
# {
#   'total_samples': 100,
#   'total_failures': 15,
#   'failure_rate': 0.15,
#   'avg_risk': 0.12,
#   'avg_capability': 0.88,
#   'risk_curve': {0: 0.05, 1: 0.08, 2: 0.12, 3: 0.18, 4: 0.25},
#   'spike_bin': 3,  # Risk spikes at bin 3
#   'samples': [...]
# }
```

**Risk Curve Computation:**
1. Map complexity score → difficulty bin [0-4]
2. Group samples by bin
3. Count semantic failures per bin (validation checks)
4. Risk[bin] = failures / total in bin

**Spike Detection:**
- Uses second derivative (curvature) analysis
- Finds inflection point where risk increases sharply
- τ_risk = bin with maximum slope increase

### 3. SDDF Capability Analyzer (`sddf_capability_analyzer.py`)

Measures task-specific accuracy degradation with complexity:

```python
from sddf_capability_analyzer import SDDFCapabilityAnalyzer

analyzer = SDDFCapabilityAnalyzer()
result = analyzer.analyze_task_model('code_generation', 'phi3_mini')

# Output:
# {
#   'total_samples': 75,
#   'avg_accuracy': 0.551,
#   'min_accuracy': 0.222,
#   'max_accuracy': 0.879,
#   'accuracy_range': 0.657,
#   'capability_curve': {0: None, 1: None, 2: 0.879, 3: 0.222, 4: None},
#   'tau_capability': 3  # Accuracy degrades at bin 3
# }
```

**Capability Curve Computation:**
1. Extract task-specific accuracy metric from validation checks
2. Group samples by difficulty bin
3. Calculate mean accuracy per bin
4. Find inflection point (τ_capability) where accuracy drops

**Task-Specific Metrics:**
- **text_generation**: ROUGE-L (content matching)
- **code_generation**: Pass@1 (functional correctness)
- **classification**: F1 score (precision + recall)
- **maths**: Exact match (numerical correctness)
- **summarization**: ROUGE-L (compression quality)
- **retrieval_grounded**: Exact match (information retrieval)
- **instruction_following**: Constraint satisfaction rate
- **information_extraction**: Field-level accuracy

### 4. SDDF Visualizer (`sddf_visualizer.py`)

Creates publication-quality risk and accuracy plots:

```python
from sddf_visualizer import SDDFVisualizer

visualizer = SDDFVisualizer()

# Pass results with both risk and capability data
visualizer.save_visualizations(results)
```

**Outputs:**
```
plots/
├── risk/                              (Risk/Semantic Failure Curves)
│   ├── all_tasks_risk_curves.png      (2x4 overview of risk curves)
│   └── model_comparison_risk.png      (2x2 model comparison - risk)
│
├── capability/                        (Capability/Accuracy Curves)
│   ├── all_tasks_accuracy_curves.png  (2x4 overview of accuracy curves)
│   ├── model_comparison_accuracy.png  (2x2 model comparison - accuracy)
│   └── task_[name].png                (8 files: both risk & accuracy per task)
│
└── results_from_existing.json         (Numerical data: risk + capability metrics)
```

## Usage

### Run Complete Analysis

```bash
cd risk_sensitivity
python calculate_from_existing_results.py
```

This will:
1. Load 1,138+ existing benchmark samples (no re-running inference)
2. Calculate SDDF vectors for all samples
3. Compute risk curves for 8 tasks × 4 models
4. Detect risk spike points (τ_risk)
5. Compute task-specific accuracy curves
6. Detect accuracy degradation points (τ_capability)
7. Generate 6 publication-quality visualizations (300 DPI)
8. Save all results to `results_from_existing.json`

### Run Individual Components

```python
# Calculate SDDF vectors only
from sddf_complexity_calculator import SDDFComplexityCalculator
calc = SDDFComplexityCalculator()
vector = calc.calculate_sddf_vector(sample, 'text_generation')

# Analyze risk curves (semantic failure rate)
from sddf_risk_analyzer import SDDFRiskAnalyzer
analyzer = SDDFRiskAnalyzer()
analysis = analyzer.analyze_task_model('code_generation', 'phi3_mini')
print(f"Risk spike at: Bin {analysis['spike_bin']}")

# Analyze task-specific accuracy
from sddf_capability_analyzer import SDDFCapabilityAnalyzer
cap_analyzer = SDDFCapabilityAnalyzer()
capability = cap_analyzer.analyze_task_model('code_generation', 'phi3_mini', samples)
print(f"Accuracy degrades at: Bin {capability['tau_capability']}")

# Plot results
from sddf_visualizer import SDDFVisualizer
viz = SDDFVisualizer()
fig = viz.plot_task_risk_curves('classification', results)
fig.savefig('plot.png', dpi=300)
```

## Understanding the Output

### Risk Curve: P(Structural Failure | Difficulty)

Shows conditional probability of OUTPUT STRUCTURE breaking:

```
Risk Curve - Code Generation (Format/Structure Validity)
  Qwen (1.5B):      Bin 0: 0.05, Bin 1: 0.08, Bin 2: 0.10, Bin 3: 0.12, Bin 4: 0.15
  Llama (70B):      Bin 0: 0.02, Bin 1: 0.03, Bin 2: 0.04, Bin 3: 0.05, Bin 4: 0.06
  Phi (3.8M):       Bin 0: 0.10, Bin 1: 0.15, Bin 2: 0.20, Bin 3: 0.78, Bin 4: 0.80
```

**Measured by:**
- ✅ Valid JSON/parseable format?
- ✅ Has all required fields?
- ✅ Correct data types?
- ✅ Non-empty output?

**NOT measured (see capability curves):**
- ❌ Is the answer correct? (wrong answer doesn't increase risk)
- ❌ Are there hallucinations? (covered by capability)
- ❌ Does code pass tests? (covered by capability)

### Capability Curve: P(Correct Answer | Difficulty)

Shows conditional probability of CONTENT/ANSWER being CORRECT:

```
Capability Curve - Code Generation (Functional Correctness)
  Llama (70B):      Bin 0: 1.00, Bin 1: 1.00, Bin 2: 1.00, Bin 3: 1.00, Bin 4: 1.00
  Qwen (1.5B):      Bin 0: 1.00, Bin 1: 1.00, Bin 2: 0.95, Bin 3: 1.00, Bin 4: 0.95
  Phi (3.8M):       Bin 0: None, Bin 1: None, Bin 2: 0.88, Bin 3: 0.22, Bin 4: None
```

**Measured by task-specific metrics:**
- ✅ **Code:** Does code pass all test cases? (Pass@1)
- ✅ **Math:** Is numerical answer exactly correct? (Exact Match)
- ✅ **Text:** Does output match expected content? (ROUGE-L)
- ✅ **Classification:** Is prediction in correct category? (F1 Score)

**Includes detection of:**
- ✅ Hallucinations (confident but wrong facts)
- ✅ Logical errors (wrong algorithm/approach)
- ✅ Content mistakes (factually incorrect)
- ✅ Functional failures (code runs but wrong output)

**NOT measured (see risk curves):**
- ❌ Is output valid JSON? (covered by risk)
- ❌ Are fields present? (covered by risk)
- ❌ Is format parseable? (covered by risk)

### Comparing Risk vs Accuracy

**Code Generation Example (Phi on Complex Tasks):**
```
At Bin 2 (medium-difficult):
  Risk:     12% (output is structurally valid)
  Accuracy: 88% (code mostly passes tests)

At Bin 3 (complex):
  Risk:     78% (output often malformed)
  Accuracy: 22% (very few tests pass)
  ↓
  Both metrics agree: Phi fails at complexity Bin 3
```

### Spike Points vs Inflection Points

**τ_risk (SPIKE POINT):** Where semantic validity sharply breaks down
```
Risk Curve - Code Generation
100% │              ╱╱  ← Spike: Sudden jump
      │           ╱╱
 80% │         ╱╱       Phi: Sharp spike at Bin 3
      │       ╱╱
      └──────────────────
        Bin 0 1 2 3 4
```
- **What it means:** Output becomes malformed/invalid
- **Visual:** Sharp vertical jump in curve
- **Phi example:** Risk jumps from 12% → 78%

**τ_capability (INFLECTION POINT):** Where task accuracy sharply degrades
```
Accuracy Curve - Code Generation
100% │ ────────       ← Flat: High accuracy
      │
 80% │ ────╱         ← Inflection: Sharp drop
      │     ╱
      │   ╱
 40% │ ╱               Phi: Sharp drop at Bin 3
      │
      └──────────────────
        Bin 0 1 2 3 4
```
- **What it means:** Correct answers drop sharply
- **Visual:** Sharp slope change (curvature inflection)
- **Phi example:** Accuracy drops from 88% → 22%

**Decision Making:**
- Both None → **Safe to deploy** (robust model)
- τ_risk detected → **Output validity fails** beyond this bin
- τ_capability detected → **Task accuracy fails** beyond this bin
- Both at same bin → **Dual failure** (validity AND correctness break)
- Risk @ Bin 3, Capability = None → **Structural issue only** (reformat could help)

## SDDF Components Explained

### 1. n_in (Input Token Count)
- **What**: Number of tokens in input
- **Why**: Larger inputs require more processing
- **Range**: [0, 1] normalized by 1000 tokens
- **Extraction**: `len(raw_input) / 4 / 1000`

### 2. H (Shannon Entropy)
- **What**: Information density of input
- **Why**: High entropy = more diverse/complex content
- **Range**: [0, 1] normalized by max entropy
- **Extraction**: `-Σ P(char) * log2(P(char))`

### 3. R̂ (Estimated Reasoning Depth)
- **What**: Number of intermediate steps needed
- **Why**: More steps = harder problem
- **Range**: [0, 1] estimated per task
- **Task-specific**:
  - Code gen: nesting depth
  - Math: input length
  - QA: multi-hop complexity

### 4. |Γ| (Output Constraint Count)
- **What**: Structural complexity of expected output
- **Why**: More constraints = harder to satisfy
- **Range**: [0, 1] normalized by 10 constraints
- **Task-specific**:
  - Classification: # classes (2-10)
  - Code gen: # test cases (2-5)
  - Extraction: # fields (5-10)

### 5. α (Parametric Dependence)
- **What**: Knowledge demand beyond context
- **Why**: External knowledge requirements increase difficulty
- **Range**: [0, 1]
- **Fixed per task**:
  - Maths: 0.7 (high domain knowledge)
  - Retrieval: 0.1 (context-only)
  - Code: 0.6 (programming knowledge)

### 6. D (Dependency Distance)
- **What**: Syntactic complexity via parse structure
- **Why**: Complex sentence structure = harder to parse
- **Range**: [0, 1] normalized by 20 word distance
- **Extraction**: avg word distance to clause boundary

## Results Interpretation

### Risk Sensitivity Curves

**Type 1: Robust Model**
```
Risk ────────────────── (flat line near 0)
                │
                └─ Low failure rate across all difficulties
```
→ Safe to deploy with minimal guardrails

**Type 2: Graceful Degradation**
```
Risk ────────────── (gentle slope)
        ╱
       ╱
      ╱
     ╱
    ╱
   ╱
  ╱
 ╱
```
→ Add guardrails for high-difficulty inputs

**Type 3: Brittle Model**
```
Risk        ╱╱╱╱╱╱ (steep spike)
         ╱
        ╱
       ╱
      ╱
     ╱
    ╱

```
→ Route to stronger model for difficult inputs

## Decision Matrix

```
Model at Task (task_complexity) → Action

τ_risk > max_complexity        → Use model (safe)
max_complexity - 1 ≤ τ_risk    → Use model + guardrails (acceptable risk)
τ_risk < max_complexity - 1    → Route to stronger model (unsafe)
```

## Performance Notes

- Analysis on 100 samples per task/model ≈ 5-10 minutes
- Increase `max_samples` for more accurate risk curves (slower)
- Visualizations generated automatically

## Files Structure

```
risk_sensitivity/
├── CORE MODULES
├── sddf_complexity_calculator.py         # SDDF 6-component vector extraction
├── sddf_risk_analyzer.py                 # P(semantic_failure | bin) computation
├── sddf_capability_analyzer.py           # P(task_accuracy | bin) computation
├── sddf_visualizer.py                    # Publication-quality visualization
│
├── ENTRY POINTS
├── calculate_from_existing_results.py    # Main: uses 1,138+ existing samples
├── run_sddf_analysis.py                  # Alternative: generates from scratch
│
├── DOCUMENTATION
├── README.md                             # This file
├── CAPABILITY_ANALYSIS_INTEGRATION.md    # Capability analyzer details
├── DECISION_MATRIX.md                    # Decision guide (no spike handling)
│
├── RESULTS
├── results_from_existing.json            # Numerical (risk + capability)
│
└── VISUALIZATIONS (plots/) - organized by analysis type
    ├── risk/                             # Risk/Semantic Failure Analysis
    │   ├── all_tasks_risk_curves.png     # 2x4 overview
    │   └── model_comparison_risk.png     # 2x2 key tasks
    │
    └── capability/                       # Capability/Accuracy Analysis
        ├── all_tasks_accuracy_curves.png # 2x4 overview
        ├── model_comparison_accuracy.png # 2x2 key tasks
        └── task_[name].png               # 8 individual tasks (risk + accuracy)
```

## Quick Start

```bash
# Run complete analysis (1,138+ samples from existing benchmark data)
python calculate_from_existing_results.py

# View results
cat results_from_existing.json | python -m json.tool

# View visualizations
# Open plots/all_tasks_risk_curves.png, all_tasks_accuracy_curves.png, etc.
```

## Output Interpretation

### Key Metrics Per Task-Model Combination

```json
{
  "total_samples": 75,
  "failure_rate": 0.2,           # Semantic failures (output invalid)
  "avg_risk": 0.45,              # P(failure) average
  "avg_accuracy": 0.55,          # Task accuracy average (task-specific)
  "tau_risk": 3,                 # Semantic validity breaks at Bin 3
  "tau_capability": 3,           # Task accuracy degrades at Bin 3
  "spike_type": "curvature",     # Detection method (curvature/threshold/max_risk)
  "accuracy_range": 0.66         # max - min accuracy (sensitivity to difficulty)
}
```

**Interpretation:**
- **τ_risk = None, τ_capability = None** → Robust model (use everywhere)
- **τ_risk detected, τ_capability = None** → Semantic validity issue (add format check)
- **τ_risk = None, τ_capability detected** → Accuracy issue (quality degrades)
- **Both detected at same bin** → Dual failure (route to stronger model)
4. Use spike points to inform routing decisions
5. Compare with operational latency (in COMPREHENSIVE_METRICS_RESULTS.txt)

