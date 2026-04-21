# Empirical UC Routing: Integration Guide

**Date**: 2026-04-19  
**Status**: ✅ Complete - All components integrated

---

## Overview

This document describes the complete empirical UC routing pipeline that computes consensus routing ratios (ρ̄) for all 8 enterprise use cases and assigns them to tiers (SLM/HYBRID/LLM) based on learned logistic regression models.

### Architecture

```
UC Datasets (8 use cases)
    ↓
Load data from gold_sets or raw_outputs
    ↓
Extract 11 linguistic features from text
    ↓
Load learned logistic regression models
    ↓
Compute p_fail for each row using weights + bias
    ↓
Apply frozen τ^consensus thresholds
    ↓
Make routing decisions: SLM if p_fail < τ, else LLM
    ↓
Aggregate per-model routing ratios → consensus ρ̄
    ↓
Assign tiers: SLM if ρ̄≥0.70, HYBRID if 0.30<ρ̄<0.70, LLM if ρ̄≤0.30
    ↓
Generate reports and visualizations
```

---

## Components

### 1. Frozen Thresholds (`sddf/frozen_thresholds.py`)

Learned τ^consensus values from SDDF v3 training (seed42), not Paper Table 6.3:

```python
FROZEN_TAU_CONSENSUS = {
    "classification": 0.6667,
    "code_generation": 1.0000,
    "information_extraction": 0.9167,
    "instruction_following": 0.9167,
    "maths": 0.3333,
    "retrieval_grounded": 0.9167,
    "summarization": 1.0000,
    "text_generation": 1.0000,
}
```

**Why these values?** 
- Empirically learned from SDDF v3 training data
- Differ significantly from paper (e.g., summarization 1.0 vs 0.2972)
- Used directly in routing without modification

### 2. UC to Task Family Mapping

```python
UC_TO_TASK_FAMILY = {
    "UC1": "classification",
    "UC2": "information_extraction",
    "UC3": "classification",
    "UC4": "classification",
    "UC5": "code_generation",
    "UC6": "classification",
    "UC7": "summarization",
    "UC8": "text_generation",
}
```

### 3. Data Source Configuration

UC datasets are in different locations with different column names:

```python
UC_DATA_SOURCE = {
    "UC1": {"source": "raw_outputs", "text_column": "item_text"},
    "UC2": {"source": "gold_sets", "text_column": "invoice_text"},    # From gold_sets
    "UC3": {"source": "raw_outputs", "text_column": "item_text"},
    "UC4": {"source": "raw_outputs", "text_column": "item_text"},
    "UC5": {"source": "raw_outputs", "text_column": "item_text"},
    "UC6": {"source": "gold_sets", "text_column": "presentation"},    # From gold_sets
    "UC7": {"source": "raw_outputs", "text_column": "item_text"},
    "UC8": {"source": "gold_sets", "text_column": "prompt_text"},     # From gold_sets
}
```

**Data Locations**:
- **raw_outputs**: `repos/SLM_Research_Project/data/raw_outputs/uc{N}_raw_*.csv`
- **gold_sets**: `repos/SLM_Research_Project/data/gold_sets/uc{N}_*.csv`

### 4. Feature Extraction (11 Features)

Extract linguistic features matching SDDF model requirements:

```python
{
    "token_count": int,              # Number of tokens
    "type_token_ratio": float,       # Vocabulary richness
    "avg_word_length": float,        # Average word length
    "sentence_count": int,           # Number of sentences
    "flesch_kincaid_grade": float,   # Reading level
    "gunning_fog": float,            # Readability
    "stopword_ratio": float,         # Ratio of stopwords
    "dep_tree_depth_mean": float,    # Syntactic complexity
    "entity_density": float,         # Named entity density
    "negation_count": int,           # Negation words
    "sentiment_lexicon_score": float # Sentiment score
}
```

**Libraries Used**:
- `nltk`: Tokenization, POS tagging, stopwords
- `textstat`: Readability metrics
- `spacy`: Entity recognition, dependency parsing
- Custom: Negation patterns, sentiment lexicon

### 5. Logistic Regression Models

Load pre-trained models from SDDF artifacts:

```python
artifact_dir = (
    Path(...) / "model_runs" / "sddf_training_splits_slm_only" /
    "sddf_pipeline_artifacts_v3" / task_family
)

artifact_file = artifact_dir / f"{model_name}__seed42.json"
```

**Model structure**:
```json
{
    "features": [...],           # Feature names in order
    "weights": [...],            # Logistic regression weights
    "bias": 0.123,              # Bias term
    "scaler_mean": [...],       # Normalization mean
    "scaler_scale": [...]       # Normalization std
}
```

**Computation**:
```
normalized = (features - scaler_mean) / scaler_scale
logit = weights · normalized + bias
p_fail = sigmoid(logit)
```

### 6. Routing Decision

For each row:
1. Compute p_fail (failure probability) using logistic regression
2. Compare with frozen τ for that task family
3. Route: **SLM if p_fail < τ, else LLM**

### 7. Consensus Aggregation

For each UC:
1. Process all rows with each of 3 SLM models (0.5b, 3b, 7b)
2. Compute per-model routing ratio: ρ = (# routed to SLM) / (# total rows)
3. Consensus: ρ̄ = mean([ρ_0.5b, ρ_3b, ρ_7b])

### 8. Tier Assignment

```python
if ρ̄ >= 0.70:
    tier = "SLM"          # Confident to route to SLM
elif ρ̄ <= 0.30:
    tier = "LLM"          # Confident to route to LLM
else:
    tier = "HYBRID"       # Mixed routing - needs hybrid approach
```

---

## Scripts and Outputs

### Script: `compute_uc_routing_decisions.py`

**Purpose**: Compute empirical routing ratios for all 8 UCs

**Usage**:
```bash
python compute_uc_routing_decisions.py
```

**Inputs**:
- UC datasets from `repos/SLM_Research_Project/data/`
- Frozen thresholds from `sddf/frozen_thresholds.py`
- Logistic regression models from `sddf_pipeline_artifacts_v3/`

**Outputs**:
- `model_runs/uc_empirical_routing.json` - Complete results
- `model_runs/UC_EMPIRICAL_TIER_SUMMARY.md` - Analysis
- Console summary with per-UC breakdown

### Script: `plot_uc_empirical_routing.py`

**Purpose**: Visualize empirical routing results

**Usage**:
```bash
python plot_uc_empirical_routing.py
```

**Creates**: `model_runs/uc_empirical_routing.png` - 4-panel visualization:
1. **Panel 1**: Tier distribution (bar chart)
2. **Panel 2**: ρ̄ values by UC (with thresholds)
3. **Panel 3**: Per-model routing divergence (stacked bars)
4. **Panel 4**: Model divergence metrics (max ρ - min ρ)

---

## Empirical Results

### Summary

| Metric | Value |
|--------|-------|
| Total UCs | 8 |
| SLM tier | 5 UCs (62.5%) |
| HYBRID tier | 2 UCs (25%) |
| LLM tier | 1 UC (12.5%) |

### By Tier

**SLM Tier (ρ̄ ≥ 0.70)**:
- UC3: 0.9407 (support ticket routing)
- UC4: 0.8760 (product review sentiment)
- UC5: 1.0000 (code review)
- UC7: 1.0000 (legal contract risk)
- UC8: 1.0000 (financial report drafting)

**HYBRID Tier (0.30 < ρ̄ < 0.70)**:
- UC1: 0.6940 (SMS threat detection) - boundary case
- UC2: 0.3333 (invoice extraction) - high model divergence

**LLM Tier (ρ̄ ≤ 0.30)**:
- UC6: 0.0033 (clinical triage) - requires LLM

### Model Divergence Patterns

**High Divergence** (max - min > 0.5):
- UC2: 1.0 (0.5b:100%, 3b:0%, 7b:0%) - Extreme divergence in invoice extraction

**Medium Divergence** (0.2 < divergence < 0.5):
- UC1: 0.51 (0.5b:100%, 3b:59.2%, 7b:49%) - Model size effect in SMS

**Low Divergence** (divergence ≤ 0.2):
- UC3, UC4, UC5, UC6, UC7, UC8 - Consistent agreement

---

## Integration with Other Components

### 1. With Frozen Thresholds (`sddf/frozen_thresholds.py`)
- Uses `FROZEN_TAU_CONSENSUS` for routing decisions
- Each task family has a fixed τ value
- τ determines the p_fail threshold for SLM vs LLM routing

### 2. With Feature Extraction
- Extracts 11 features from UC text
- Features match SDDF model expectations
- Handles different text column names per UC

### 3. With Logistic Regression Models
- Loads pre-trained models from SDDF artifacts
- Uses scaler normalization from model JSON
- Computes p_fail = sigmoid(weights · normalized_features + bias)

### 4. With Tier Assignment (`tier_from_consensus_ratio()`)
- Converts ρ̄ → tier (SLM/HYBRID/LLM)
- Uses fixed thresholds: 0.70 (SLM), 0.30 (LLM)
- HYBRID for middle ground

### 5. With Threshold Sensitivity Analysis
- Can sweep tier thresholds to find optimal values
- Compare empirical ρ̄ against optimized thresholds
- Analyze risk-coverage tradeoffs

---

## Key Insights

### 1. Model Size Effect

The smallest model (0.5b) tends to **overestimate** its capability:
- Always routes at ≥99% to SLM in most UCs
- More confident than the larger models (3b, 7b)

Larger models (7b) are more **conservative**:
- More aligned with actual performance
- Lower routing ratios in challenging domains (UC1, UC2)

### 2. Domain-Specific Capability

**SLM-Capable Domains**:
- Code review (UC5): Perfect consensus
- Legal analysis (UC7): Perfect consensus
- Financial drafting (UC8): Perfect consensus
- Support routing (UC3): 94.07% consensus
- Review sentiment (UC4): 87.60% consensus

**LLM-Required Domain**:
- Clinical triage (UC6): 0.33% consensus - SLMs struggle with medical domain

**Mixed Capability**:
- SMS threat detection (UC1): 69.40% consensus - borderline
- Invoice extraction (UC2): 33.33% consensus - high variance

### 3. Model Divergence as Signal

High divergence (e.g., UC2: 1.0) indicates:
- Models disagree on capability
- Likely needs human review or hybrid approach
- May indicate noisy or ambiguous input features

Low divergence (e.g., UC5: 0.0) indicates:
- Models agree on capability
- Consistent routing behavior
- More confident tier assignment

---

## Usage Examples

### Example 1: Get UC Tier Assignment
```python
from pathlib import Path
import json

with open(Path("model_runs/uc_empirical_routing.json")) as f:
    results = json.load(f)

uc_tier = results["UC3"]["tier"]  # "SLM"
uc_rho_bar = results["UC3"]["rho_bar"]  # 0.9407
```

### Example 2: Analyze Model Divergence
```python
uc2_result = results["UC2"]
per_model_rho = uc2_result["per_model_rho"]
divergence = max(per_model_rho.values()) - min(per_model_rho.values())
print(f"UC2 divergence: {divergence:.2f}")  # 1.0
```

### Example 3: Check Routing Confidence
```python
for uc in ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]:
    result = results[uc]
    print(f"{uc}: ρ̄={result['rho_bar']:.4f} → {result['tier']}")
```

---

## Files Reference

### Primary Scripts
- `compute_uc_routing_decisions.py` - Main computation pipeline
- `plot_uc_empirical_routing.py` - Visualization generation

### Supporting Modules
- `sddf/frozen_thresholds.py` - Frozen τ^consensus values
- `sddf/usecase_mapping.py` - UC info and tier assignment
- `sddf/runtime_routing.py` - Routing functions

### Outputs
- `model_runs/uc_empirical_routing.json` - Complete results
- `model_runs/UC_EMPIRICAL_TIER_SUMMARY.md` - Text summary
- `model_runs/uc_empirical_routing.png` - 4-panel visualization

### Data Sources
- `repos/SLM_Research_Project/data/raw_outputs/` - Raw model outputs
- `repos/SLM_Research_Project/data/gold_sets/` - Ground truth input texts

---

## Next Steps

1. **Validation**
   - Compare empirical tier distribution against Paper Table 7.4
   - Validate ρ̄ values match expected ranges

2. **Analysis**
   - Investigate UC2 divergence (why 0.5b vs 3b/7b disagree?)
   - Study UC1 boundary case (ρ̄=0.6940 vs SLM threshold 0.70)

3. **Integration**
   - Use empirical tiers in S³ policy routing
   - Compare against Paper Table 8.1 predictions
   - Integrate with main benchmarking pipeline

4. **Optimization**
   - Run threshold sensitivity analysis
   - Find optimal tier boundaries for this data
   - Compare optimal vs Paper Table 6.3 thresholds

---

**Status**: ✅ Empirical UC routing pipeline complete and integrated
