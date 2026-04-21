# UC Empirical Routing: Quick Start Guide

**Status**: ✅ Complete (2026-04-19)

## What Is This?

A **data-driven framework** for assigning enterprise use cases (UCs) to routing tiers:
- **SLM Tier** (5 UCs): Use small language models (Qwen 2.5)
- **HYBRID Tier** (2 UCs): Mixed routing with human review
- **LLM Tier** (1 UC): Use large language models

## Key Results

```
UC1  SMS Threat Detection          → HYBRID  (ρ̄=0.6940)
UC2  Invoice Field Extraction      → HYBRID  (ρ̄=0.3333)
UC3  Support Ticket Routing        → SLM     (ρ̄=0.9407)
UC4  Product Review Sentiment      → SLM     (ρ̄=0.8760)
UC5  Automated Code Review         → SLM     (ρ̄=1.0000)
UC6  Clinical Triage               → LLM     (ρ̄=0.0033)
UC7  Legal Contract Risk Analysis  → SLM     (ρ̄=1.0000)
UC8  Financial Report Drafting     → SLM     (ρ̄=1.0000)
```

## How to Use

### 1. Generate Results
```bash
python compute_uc_routing_decisions.py
```
Outputs: `model_runs/uc_empirical_routing.json`

### 2. Visualize Results
```bash
python plot_uc_empirical_routing.py
```
Outputs: `model_runs/uc_empirical_routing.png`

### 3. Load Results in Code
```python
import json
from pathlib import Path

with open(Path("model_runs/uc_empirical_routing.json")) as f:
    results = json.load(f)

# Get UC3 tier assignment
tier = results["UC3"]["tier"]  # "SLM"
rho_bar = results["UC3"]["rho_bar"]  # 0.9407
confidence = "High" if rho_bar > 0.85 else "Moderate"
```

## Documentation

**Start Here**:
- `EMPIRICAL_ROUTING_EXECUTIVE_SUMMARY.md` - Business overview

**Technical Details**:
- `EMPIRICAL_UC_ROUTING_INTEGRATION.md` - Architecture & implementation
- `UC_EMPIRICAL_TIER_SUMMARY.md` - Detailed results analysis
- `COMPLETION_STATUS.md` - Progress tracking

**Code**:
- `compute_uc_routing_decisions.py` - Main pipeline
- `plot_uc_empirical_routing.py` - Visualization

**Output**:
- `model_runs/uc_empirical_routing.json` - Complete results
- `model_runs/uc_empirical_routing.png` - 4-panel visualization

## Key Insights

### ✅ SLM Can Handle (62.5%)
- Code review, legal analysis, financial drafting, support routing, sentiment analysis
- These domains have well-defined tasks and structured data

### ⚠️ Mixed Results (25%)
- SMS threat detection, invoice extraction
- High model divergence suggests inherent difficulty or feature gaps

### ❌ LLM Required (12.5%)
- Clinical triage: Medical domain requires expert knowledge
- High stakes: Liability and domain expertise essential

## What's Inside

### Feature Extraction
11 linguistic features extracted from UC input text:
- Token count, type-token ratio, word length
- Readability (Flesch-Kincaid, Gunning Fog)
- Syntactic complexity, entity density
- Negation count, sentiment score

### Routing Logic
```
For each UC sample:
  1. Extract 11 features from text
  2. Compute p_fail using logistic regression
  3. Compare with frozen τ for that task family
  4. Route: SLM if p_fail < τ, else LLM
  
Aggregate across 3 models (0.5b, 3b, 7b):
  5. Compute per-model routing ratio ρ
  6. Consensus: ρ̄ = mean(ρ models)
  7. Assign tier based on ρ̄
```

### Tier Assignment
- **SLM**: ρ̄ ≥ 0.70 (confident SLM routing)
- **HYBRID**: 0.30 < ρ̄ < 0.70 (mixed routing)
- **LLM**: ρ̄ ≤ 0.30 (confident LLM routing)

## Data Sources

- **UC1, UC3, UC4, UC5, UC7**: `repos/SLM_Research_Project/data/raw_outputs/`
- **UC2, UC6, UC8**: `repos/SLM_Research_Project/data/gold_sets/`

## Next Steps

1. **Validate**: Compare against Paper Table 7.4
2. **Analyze**: Study UC2 divergence and UC1 boundary case
3. **Integrate**: Use empirical tiers in S³ policy routing
4. **Optimize**: Run threshold sensitivity analysis

---

**For questions or more details, see the full documentation above.**
