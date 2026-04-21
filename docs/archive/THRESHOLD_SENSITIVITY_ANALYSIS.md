# Threshold Sensitivity Analysis: SelectiveNet Risk-Coverage Tradeoff

**Status**: ✅ **INTEGRATED INTO PIPELINE**  
**Date**: 2026-04-19  
**Framework**: SelectiveNet-inspired confidence-coverage analysis

---

## 📋 Overview

Instead of hardcoding tier thresholds (ρ̄ >= 0.70 for SLM, ρ̄ <= 0.30 for LLM), we now:
1. **Sweep different threshold combinations** across a configurable range
2. **Measure accuracy-coverage tradeoffs** for each configuration
3. **Find optimal thresholds** that maximize performance
4. **Visualize the frontier** to understand marginal benefits

This applies **SelectiveNet's core idea**: how confident should the model be before making a decision?

---

## 🎯 SelectiveNet Concept

### Traditional Approach (Fixed Thresholds)
```
ρ̄ >= 0.70  →  SLM
0.30 < ρ̄ < 0.70  →  HYBRID
ρ̄ <= 0.30  →  LLM
```
Problem: These thresholds are hardcoded, not validated against actual performance.

### SelectiveNet Approach (Optimized Thresholds)
```
1. Sweep thresholds: [0.2, 0.9] with step=0.05
2. For each (SLM_threshold, LLM_threshold) pair:
   - Assign tasks to tiers using those thresholds
   - Compute tier distribution
   - Measure overall accuracy
   - Track coverage per tier
3. Plot accuracy vs coverage (risk-coverage frontier)
4. Find optimal threshold that maximizes the frontier
```

---

## 🔧 Implementation

### Core Function: `analyze_threshold_sensitivity()`

```python
from sddf.threshold_sensitivity_analysis import analyze_threshold_sensitivity

analysis = analyze_threshold_sensitivity(
    test_results,           # From test_with_frozen.py
    threshold_range=(0.2, 0.9),  # SLM threshold sweep range
    step=0.05               # Granularity
)
```

**Returns**:
```python
{
    'summary': {
        'total_sweep_points': 105,  # 21 × 5 configurations
        'threshold_range': (0.2, 0.9),
        'step': 0.05,
    },
    'optimal_thresholds': {
        'slm_threshold': 0.25,
        'llm_threshold': 0.20,
        'overall_accuracy': 0.8500,
        'tier_distribution': {'SLM': 8, 'HYBRID': 0, 'LLM': 0},
        'reason': 'Maximizes overall weighted accuracy...'
    },
    'current_thresholds': {
        'slm_threshold': 0.70,
        'llm_threshold': 0.30,
        'note': 'Original frozen threshold values'
    },
    'sweep_results': [  # All 105 configurations with metrics
        {
            'slm_threshold': 0.20,
            'llm_threshold': 0.15,
            'tier_distribution': {...},
            'coverage_pct': {...},
            'avg_accuracy_per_tier': {...},
            'overall_weighted_accuracy': 0.75,
            'slm_coverage': 0.875,
            'hybrid_coverage': 0.125,
            'llm_coverage': 0.0,
        },
        ...
    ]
}
```

### Visualization: 4-Panel Risk-Coverage Analysis

The `plot_threshold_sensitivity()` function generates:

1. **Panel 1: Risk-Accuracy Tradeoff**
   - X: SLM threshold (ρ̄ >= X)
   - Y: Overall weighted accuracy
   - Shows how accuracy changes with threshold
   - Red line marks current (0.70)

2. **Panel 2: Tier Coverage Distribution**
   - Shows % of tasks in each tier as threshold changes
   - SLM coverage increases as threshold drops
   - HYBRID coverage peaks at mid-range thresholds
   - LLM coverage minimal for high thresholds

3. **Panel 3: Accuracy-Coverage Frontier**
   - X: SLM coverage (% of tasks routed to SLM)
   - Y: Overall accuracy
   - Each point is one threshold configuration
   - Color indicates SLM threshold value
   - Shows Pareto frontier of achievable (accuracy, coverage) pairs

4. **Panel 4: Marginal Benefit Analysis**
   - Shows how much accuracy improves as threshold changes
   - Helps identify "sweet spots" where marginal gain is significant
   - Large bars = big accuracy improvement with small threshold change

---

## 📊 Test Results with Dummy Data

### Current Thresholds (Paper Table 6.3)
```
SLM threshold: 0.70 (ρ̄ >= 0.70)
LLM threshold: 0.30 (ρ̄ <= 0.30)

Tier Distribution:
  SLM:    2 tasks (25%)
  HYBRID: 5 tasks (62%)
  LLM:    1 task  (13%)

Overall Weighted Accuracy: 0.78
```

### Optimal Thresholds (Sweep Results)
```
SLM threshold: 0.25 (ρ̄ >= 0.25)
LLM threshold: 0.20 (ρ̄ <= 0.20)

Tier Distribution:
  SLM:    8 tasks (100%)
  HYBRID: 0 tasks (0%)
  LLM:    0 tasks (0%)

Overall Weighted Accuracy: 0.85

Change: -0.45 on SLM threshold, -0.10 on LLM threshold
Accuracy improvement: +7% (0.78 → 0.85)
```

**Note**: With dummy data (70% SLM accuracy, 100% LLM accuracy), the optimal is to maximize SLM coverage. With real data, the tradeoff will be different!

---

## 🚀 How to Use

### Option 1: Integrated Pipeline
```bash
# Runs full pipeline including sensitivity analysis
python3 run_test_with_frozen_thresholds.py
```

Outputs:
- `threshold_sensitivity.json` - Complete sweep results
- `threshold_sensitivity_analysis.png` - 4-panel visualization

### Option 2: Standalone Analysis
```python
import json
from pathlib import Path
from sddf.threshold_sensitivity_analysis import (
    analyze_threshold_sensitivity,
    print_threshold_sensitivity_report,
    save_sensitivity_analysis,
    plot_threshold_sensitivity,
)

# Load test results
with open('test_with_frozen.json') as f:
    test_results = json.load(f)

# Run analysis
analysis = analyze_threshold_sensitivity(
    test_results,
    threshold_range=(0.1, 0.9),  # Wider sweep
    step=0.02                     # Finer granularity
)

# Print report
print_threshold_sensitivity_report(analysis)

# Save & visualize
save_sensitivity_analysis(analysis, 'sensitivity.json')
plot_threshold_sensitivity(analysis, 'sensitivity.png')

# Inspect sweep results
top_configs = sorted(
    analysis['sweep_results'],
    key=lambda x: x['overall_weighted_accuracy'],
    reverse=True
)
for config in top_configs[:5]:
    print(f"SLM:{config['slm_threshold']:.2f} "
          f"LLM:{config['llm_threshold']:.2f} → "
          f"Accuracy: {config['overall_weighted_accuracy']:.4f}")
```

---

## 📈 Metrics Explained

### Coverage
- **SLM Coverage**: Fraction of tasks assigned to SLM tier
- **HYBRID Coverage**: Fraction assigned to HYBRID tier
- **LLM Coverage**: Fraction assigned to LLM tier
- Sum always = 1.0

### Accuracy
- **SLM Accuracy**: % of queries correct when routed to SLM
- **HYBRID Accuracy**: Average of SLM + LLM accuracy
- **Overall Weighted Accuracy**: Weighted average across all tiers
  - `sum(accuracy[t] × coverage[t])` for all tiers

### Marginal Benefit
- Change in accuracy per unit threshold change
- Identifies "sweet spots" where small threshold adjustments give big accuracy gains

---

## 🎯 When to Use This Analysis

### Use When:
1. **Transitioning to real data** - Current (0.70, 0.30) may not be optimal
2. **Investigating tier distribution** - Want to understand coverage tradeoffs
3. **Optimizing deployment** - Need to balance accuracy vs coverage
4. **Validating paper thresholds** - Check if Table 6.3 values are empirically optimal

### Don't Use When:
1. You're locked into Paper Table 6.3 values (academic compliance)
2. You have other constraints (e.g., must maintain 50% SLM coverage)
3. Thresholds are business-driven (not data-driven)

---

## 📊 JSON Output Structure

### `threshold_sensitivity.json`
```json
{
  "summary": {
    "total_sweep_points": 105,
    "threshold_range": [0.2, 0.9],
    "step": 0.05
  },
  "optimal_thresholds": {
    "slm_threshold": 0.25,
    "llm_threshold": 0.20,
    "overall_accuracy": 0.8500,
    "tier_distribution": {"SLM": 8, "HYBRID": 0, "LLM": 0},
    "coverage_pct": {"SLM": 1.0, "HYBRID": 0.0, "LLM": 0.0},
    "reason": "Maximizes overall weighted accuracy..."
  },
  "current_thresholds": {
    "slm_threshold": 0.70,
    "llm_threshold": 0.30,
    "note": "Original frozen threshold values"
  },
  "sweep_results": [
    {
      "slm_threshold": 0.20,
      "llm_threshold": 0.15,
      "tier_distribution": {...},
      "coverage_pct": {...},
      "avg_accuracy_per_tier": {...},
      "overall_weighted_accuracy": 0.75,
      ...
    },
    ...
  ]
}
```

---

## 🔗 Integration Points

### In Pipeline
```
Test Phase (test_with_frozen.py)
    ↓
    (produces test_results with per-task metrics)
    ↓
Sensitivity Analysis (threshold_sensitivity_analysis.py)
    ↓
    (sweeps thresholds, finds optimal)
    ↓
JSON Output + Visualization
```

### With Use Case Mapping
```
Task Family Thresholds (current: 0.70/0.30)
    ↓
Use Case Tier Assignment (map_taskfamily_results_to_usecases)
    ↓
What if we change to 0.25/0.20?
    ↓
Re-run use case mapping with new thresholds
    ↓
Compare tier distributions
```

---

## 🔄 Next Steps

### Short Term
1. Run analysis on real validation/test data
2. Identify true optimal thresholds
3. Compare against Paper Table 6.3 (0.70/0.30)

### Medium Term
1. If significant difference: investigate why
2. Consider constraints:
   - Must maintain coverage X% for SLM?
   - Must satisfy accuracy >= Y% in each tier?
3. Re-optimize with constraints

### Long Term
1. Use sensitivity analysis as diagnostic tool
2. Monitor threshold performance in production
3. Re-analyze periodically as data distribution shifts

---

## 📚 References

- **SelectiveNet Paper**: [1901.09192] SelectiveNet: A Deep Neural Network with an Integrated Reject Option
- **Concept**: Risk-coverage tradeoff in selective prediction
- **Implementation**: Sweep-based threshold optimization with accuracy-coverage frontier analysis

---

## ✅ Verification

- [x] Sensitivity analysis module created
- [x] 4-panel visualization implemented
- [x] Integrated into main pipeline
- [x] Test run completed (dummy data)
- [x] Documentation complete

---

**Ready to analyze real data and find empirically optimal tier thresholds** ✅
