# SDDF Capability & Risk Sensitivity Curves

**Date**: March 19, 2026
**Status**: ✅ Ready for Generation

---

## Overview

The visualization system generates **two graphs per task** (16 total graphs) showing all models on the same plot:

1. **Capability Curves** - Shows model capability degradation across difficulty bins
2. **Risk Sensitivity Curves** - Shows risk increase across difficulty bins

---

## Graph Types

### 1. Capability Curves (8 graphs)
**File**: `outputs/plots/{task}_capability_curves.png`

**What it shows**:
- X-axis: Difficulty Bins (0-4) based on SDDF complexity
- Y-axis: Capability = 1 - Risk (0 = complete failure, 1 = perfect)
- Multiple lines: One per model
- Color-coded for easy distinction

**Key Features**:
- **τ_cau (Capability Threshold)**: Marked with RED ✕ symbol
  - Indicates bin where capability drops below 0.8 (80%)
  - Shows where model starts to struggle
- All models compared on same plot
- Legend with model names
- Grid for easy reading

**Example**:
```
Capability on Code Generation Task:
- Qwen 1.5B: 0.95 (Bin 0) → 0.20 (Bin 4), tau_cau = Bin 2
- Phi-3 Mini: 0.92 (Bin 0) → 0.15 (Bin 4), tau_cau = Bin 2
- Mistral 7B: 0.98 (Bin 0) → 0.35 (Bin 4), tau_cau = Bin 3
```

---

### 2. Risk Sensitivity Curves (8 graphs)
**File**: `outputs/plots/{task}_risk_curves.png`

**What it shows**:
- X-axis: Difficulty Bins (0-4) based on SDDF complexity
- Y-axis: Risk = P(semantic_failure | bin) (0 = safe, 1 = always fails)
- Multiple lines: One per model
- Color-coded for easy distinction

**Key Features**:
- **τ_risk (Risk Threshold)**: Marked with STAR ★ symbol
  - Indicates bin where risk exceeds 0.3 (30%)
  - Shows where model becomes unreliable
- **Red Dashed Line**: Risk = 0.3 threshold reference
- All models compared on same plot
- Legend with model names
- Grid for easy reading

**Example**:
```
Risk on Text Generation Task:
- Qwen 1.5B: 0.05 (Bin 0) → 0.85 (Bin 4), tau_risk = Bin 2
- Phi-3 Mini: 0.08 (Bin 0) → 0.80 (Bin 4), tau_risk = Bin 2
- Mistral 7B: 0.02 (Bin 0) → 0.60 (Bin 4), tau_risk = Bin 3
```

---

## Tasks Covered (8 Total)

1. **Text Generation** - Open-ended content generation
2. **Code Generation** - Programming task completion
3. **Classification** - Label prediction task
4. **Maths** - Mathematical reasoning and problem solving
5. **Summarization** - Document compression with preservation
6. **Retrieval Grounded** - QA grounded in provided context
7. **Instruction Following** - Multi-constraint command execution
8. **Information Extraction** - Structured field extraction

---

## Model Configuration

**Models tracked** (6 total):
- Qwen 2.5 1.5B (SLM)
- Qwen 2.5 7B (SLM)
- Phi-3 Mini (SLM)
- Phi-3 Medium (SLM)
- Mistral 7B (SLM)
- Llama 2 7B (SLM)

**Color Scheme** (fixed across all plots):
- Qwen models: Blue (#1f77b4)
- Phi-3 models: Orange (#ff7f0e)
- Mistral: Green (#2ca02c)
- Llama: Red (#d62728)

---

## Threshold Interpretation

### τ_cau (Capability Threshold)

**Definition**: First bin where capability < 0.8

**Interpretation**:
- **τ_cau = Bin 0-1**: Model excellent, handles all complexity levels
- **τ_cau = Bin 2**: Model good, struggles on harder problems
- **τ_cau = Bin 3**: Model limited, only handles easy cases
- **τ_cau = Bin 4+**: Model very limited or always fails

**Decision**: Use SLM only below τ_cau; escalate above

### τ_risk (Risk Threshold)

**Definition**: First bin where risk > 0.3

**Interpretation**:
- **τ_risk = Bin 0-1**: Model very reliable, <30% error rate everywhere
- **τ_risk = Bin 2**: Model reliable on easy tasks, risky on hard ones
- **τ_risk = Bin 3**: Model becomes unreliable on harder tasks
- **τ_risk = Bin 4**: Model unreliable on complex problems

**Decision**: Avoid SLM above τ_risk without mitigation

---

## Usage

### Generate Graphs

```bash
cd framework/risk_sensitivity
python3 scripts/run_sddf_analysis.py
```

This will:
1. Calculate SDDF complexity for all samples
2. Compute risk and capability curves
3. Detect threshold bins (τ_cau, τ_risk)
4. Generate 16 PNG files in `outputs/plots/`

### View Results

All graphs saved to:
```
outputs/plots/
├── text_generation_capability_curves.png
├── text_generation_risk_curves.png
├── code_generation_capability_curves.png
├── code_generation_risk_curves.png
├── ... (6 more tasks, 2 graphs each)
```

---

## Technical Details

### Complexity Binning

Samples assigned to bins based on SDDF composite complexity ξ(x):
- **Bin 0**: ξ ∈ [0.0, 0.2) - Trivial
- **Bin 1**: ξ ∈ [0.2, 0.4) - Easy
- **Bin 2**: ξ ∈ [0.4, 0.6) - Medium
- **Bin 3**: ξ ∈ [0.6, 0.8) - Hard
- **Bin 4**: ξ ∈ [0.8, 1.0] - Very Hard

### Capability Calculation

```
capability(bin) = 1 - risk(bin)
                = 1 - P(semantic_failure | bin)
```

where semantic_failure = any validation check fails (non_empty, parseable, has_expected_fields)

### Risk Calculation

```
risk(bin) = failures(bin) / samples(bin)
          = P(semantic_failure | bin)
```

### Threshold Detection

**τ_cau** (Capability):
```python
for bin in [0, 1, 2, 3, 4]:
    if capability(bin) < 0.8:
        return bin  # First bin below threshold
```

**τ_risk** (Risk):
```python
for bin in [0, 1, 2, 3, 4]:
    if risk(bin) > 0.3:
        return bin  # First bin above threshold
```

---

## Analysis Flow

```
Benchmark Data (JSONL)
    ↓
SDDF Complexity Calculator
    ├─ Input token count (n_in)
    ├─ Shannon entropy (H)
    ├─ Reasoning depth (R_hat)
    ├─ Constraint count (|Γ|)
    ├─ Parametric dependence (α)
    └─ Dependency distance (D)
    ↓
Composite Complexity ξ(x)
    ↓
Bin Assignment (0-4)
    ↓
Risk Analyzer
    ├─ P(failure | bin)
    ├─ Capability = 1 - risk
    ├─ τ_cau detection
    └─ τ_risk detection
    ↓
SDDFCurvePlotter
    ├─ capability_curves.png (16 colors, tau_cau marked)
    └─ risk_curves.png (16 colors, tau_risk marked)
```

---

## Interpretation Guide

### How to Read Capability Curves

**Good Model**:
- Line stays high (>0.8) for Bins 0-2
- Smooth degradation from Bin 2 onwards
- τ_cau ≥ Bin 2

**Struggling Model**:
- Line drops quickly
- τ_cau = Bin 1 or earlier
- Use only for trivial tasks

**Excellent Model**:
- Line stays >0.9 all the way to Bin 3
- τ_cau = Bin 3 or 4

### How to Read Risk Curves

**Low Risk**:
- Curve stays below 0.3 for Bins 0-2
- τ_risk ≥ Bin 2
- Can use SLM safely on easy-medium tasks

**High Risk**:
- Curve crosses 0.3 early (Bin 0-1)
- τ_risk = Bin 0 or 1
- Only for trivial tasks or with mitigation

**Variable Risk**:
- Different models have different τ_risk
- Choose appropriate model per task complexity
- Hybrid routing necessary above τ_risk

---

## Decision Making

Use the curves to decide:

1. **Can we use this model?**
   - Find task complexity → locate bin
   - Check if capability(bin) > 0.8
   - Check if risk(bin) < 0.3
   - Answer: Yes if both true, No otherwise

2. **When to escalate to LLM?**
   - User input complexity > τ_cau → Escalate
   - User input complexity > τ_risk → Escalate
   - Recommendation: Use max(τ_cau, τ_risk) as threshold

3. **Which model to use?**
   - Find lowest τ in your task complexity range
   - Choose model with highest τ_cau/τ_risk
   - Fallback: hybrid (SLM + LLM backup)

---

## Technical Implementation

**Module**: `framework/risk_sensitivity/src/visualization/curve_plotter.py`

**Class**: `SDDFCurvePlotter`

**Methods**:
- `plot_capability_curves(task_type, results)` → PNG file
- `plot_risk_curves(task_type, results)` → PNG file
- `find_capability_threshold(curve)` → bin or None
- `find_risk_threshold(curve)` → bin or None
- `save_all_visualizations(all_results)` → {task: [cap_plot, risk_plot]}

**Dependencies**:
- matplotlib (for plotting)
- numpy (for calculations)
- pandas (for data handling)

---

## Next Steps

1. ✅ Visualization module complete
2. ✅ Integration with analysis pipeline
3. ⏳ Run analysis to generate graphs
4. ⏳ Export for paper/presentation
5. ⏳ Create decision matrix based on thresholds

---

**Status**: Framework ready, awaiting benchmark analysis execution
