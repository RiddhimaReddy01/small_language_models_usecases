# Empirical UC Tier Assignments from SLM Research Project Data

**Date**: 2026-04-19  
**Status**: ✅ Complete - All 8 UCs processed

---

## Summary

Computed empirical consensus routing ratios (ρ̄) for each of 8 enterprise use cases using:
1. Learned logistic regression models from SDDF v3 training
2. Frozen τ^consensus values (Paper Table 6.3, corrected with learned values)
3. 11 linguistic features extracted from UC input texts
4. Per-model p_fail computation and aggregation

### Tier Distribution

| Tier | Count | UCs |
|------|-------|-----|
| **SLM** | 5 | UC3, UC4, UC5, UC7, UC8 |
| **HYBRID** | 2 | UC1, UC2 |
| **LLM** | 1 | UC6 |

---

## Detailed Results

### SLM Tier (ρ̄ ≥ 0.70)

**UC3: Support Ticket Routing** (Classification)
- ρ̄ = 0.9407
- Per-model: [1.00, 0.894, 0.928]
- Per-model routing: 100% → SLM (0.5b), 89.4% → SLM (3b), 92.8% → SLM (7b)
- Interpretation: Strong consensus across all 3 SLM models for routing to SLM tier

**UC4: Product Review Sentiment** (Classification)
- ρ̄ = 0.8760
- Per-model: [1.00, 0.934, 0.694]
- Per-model routing: 100% → SLM (0.5b), 93.4% → SLM (3b), 69.4% → SLM (7b)
- Interpretation: Moderate-to-strong consensus, mostly SLM tier

**UC5: Automated Code Review** (Code Generation)
- ρ̄ = 1.0000
- Per-model: [1.00, 1.00, 1.00]
- Per-model routing: 100% → SLM across all models
- Interpretation: Perfect consensus - all models route all samples to SLM

**UC7: Legal Contract Risk** (Summarization)
- ρ̄ = 1.0000
- Per-model: [1.00, 1.00, 1.00]
- Per-model routing: 100% → SLM across all models
- Interpretation: Perfect consensus - legal text is well-handled by SLM models

**UC8: Financial Report Drafting** (Text Generation)
- ρ̄ = 1.0000
- Per-model: [1.00, 1.00, 1.00]
- Per-model routing: 100% → SLM across all models
- Interpretation: Perfect consensus - financial text generation is SLM-capable

---

### HYBRID Tier (0.30 < ρ̄ < 0.70)

**UC1: SMS Threat Detection** (Classification)
- ρ̄ = 0.6940 (boundary case - very close to SLM threshold of 0.70)
- Per-model: [1.00, 0.592, 0.49]
- Per-model routing: 100% → SLM (0.5b), 59.2% → SLM (3b), 49.0% → SLM (7b)
- Interpretation: Divergence across model sizes - smaller model (0.5b) is overconfident, larger models (3b/7b) are more conservative

**UC2: Invoice Field Extraction** (Information Extraction)
- ρ̄ = 0.3333
- Per-model: [1.00, 0.0, 0.0]
- Per-model routing: 100% → SLM (0.5b), 0% → SLM (3b), 0% → SLM (7b)
- Interpretation: Extreme divergence - smallest model routes all to SLM, larger models route all to LLM, suggesting high variance in model capability for invoice extraction

---

### LLM Tier (ρ̄ ≤ 0.30)

**UC6: Clinical Triage** (Classification)
- ρ̄ = 0.0033 (extremely low - nearly all routed to LLM)
- Per-model: [0.01, 0.0, 0.0]
- Per-model routing: 1% → SLM (0.5b), 0% → SLM (3b), 0% → SLM (7b)
- Interpretation: Clinical triage is beyond SLM capability - requires LLM

---

## Key Insights

### Model Size Effects

1. **0.5b (Smallest model)**: Most confident in routing to SLM
   - UC1: 100%, UC2: 100%, UC3: 100%, UC4: 100%, UC5: 100%, UC6: 1%, UC7: 100%, UC8: 100%
   - Tendency to overestimate capability

2. **3b (Medium model)**: More conservative routing
   - UC1: 59.2%, UC2: 0%, UC3: 89.4%, UC4: 93.4%, UC5: 100%, UC6: 0%, UC7: 100%, UC8: 100%
   - More selective than 0.5b

3. **7b (Larger model)**: Most conservative routing
   - UC1: 49%, UC2: 0%, UC3: 92.8%, UC4: 69.4%, UC5: 100%, UC6: 0%, UC7: 100%, UC8: 100%
   - Most aligned with actual capability

### Task-Specific Patterns

**High SLM Confidence (ρ̄ ≥ 0.99)**:
- UC5 (Code Review): τ=1.00, ρ̄=1.00
- UC7 (Legal Risk): τ=1.00, ρ̄=1.00
- UC8 (Financial Drafting): τ=1.00, ρ̄=1.00
- Pattern: All have τ=1.00, meaning SLMs never route to LLM

**Moderate SLM Confidence (0.50 ≤ ρ̄ < 0.99)**:
- UC1 (SMS Threat): τ=0.6667, ρ̄=0.6940
- UC3 (Support Routing): τ=0.6667, ρ̄=0.9407
- UC4 (Review Sentiment): τ=0.6667, ρ̄=0.8760

**Low SLM Confidence (ρ̄ < 0.50)**:
- UC2 (Invoice Extraction): τ=0.9167, ρ̄=0.3333 - high τ but divergent models
- UC6 (Clinical Triage): τ=0.6667, ρ̄=0.0033 - consistently routed to LLM

---

## Data Processing Details

| UC | Source | Text Column | Task Family | Rows | Models |
|----|--------|-------------|-------------|------|--------|
| UC1 | raw_outputs | item_text | classification | 500 | 3/3 |
| UC2 | gold_sets | invoice_text | information_extraction | 100 | 3/3 |
| UC3 | raw_outputs | item_text | classification | 500 | 3/3 |
| UC4 | raw_outputs | item_text | classification | 500 | 3/3 |
| UC5 | raw_outputs | item_text | code_generation | 500 | 3/3 |
| UC6 | gold_sets | presentation | classification | 100 | 3/3 |
| UC7 | raw_outputs | item_text | summarization | 500 | 3/3 |
| UC8 | gold_sets | prompt_text | text_generation | 100 | 3/3 |

---

## Output Files

- **UC_empirical_routing.json**: Complete results with per-model breakdown and tier explanations
- **This summary**: Analysis and insights

---

## Next Steps

1. ✅ **Compute empirical ρ̄ for all 8 UCs** - DONE
2. **Compare with Paper Table 7.4** - If available, validate tier distribution
3. **Analyze convergence patterns** - Why high divergence in UC2?
4. **Integrate into main pipeline** - Use empirical routing for S³ policy
5. **Generate visualization** - Tier distribution and per-model comparisons

---

**Status**: Ready for validation against paper results and integration with frozen threshold pipeline ✅
