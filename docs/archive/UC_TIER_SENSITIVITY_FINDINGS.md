# UC Tier Threshold Sensitivity Analysis: Findings

**Date**: 2026-04-19  
**Status**: ✅ Complete

---

## Executive Summary

We analyzed **optimal tier thresholds** for UC classification using empirical ρ̄ values. The analysis tested **48 different (SLM_threshold, LLM_threshold) combinations** and compared them against the Paper's baseline of **(0.70, 0.30)**.

### Key Finding

**Paper uses (0.70/0.30) but data suggests (0.50/0.35) or (0.50/0.10)** depending on deployment objective.

---

## The Data: 8 Empirical ρ̄ Values

```
UC1: 0.6940  (SMS Threat Detection)        ← Close to SLM boundary
UC2: 0.3333  (Invoice Extraction)          ← In HYBRID zone
UC3: 0.9407  (Support Ticket Routing)      ← Confident SLM
UC4: 0.8760  (Product Review Sentiment)    ← Confident SLM
UC5: 1.0000  (Automated Code Review)       ← Perfect SLM
UC6: 0.0033  (Clinical Triage)             ← Confident LLM
UC7: 1.0000  (Legal Contract Risk)         ← Perfect SLM
UC8: 1.0000  (Financial Report Drafting)   ← Perfect SLM
```

---

## Paper Baseline: (0.70, 0.30)

```
Configuration:     0.70 / 0.30
Gap (HYBRID zone): 0.40 (range where ρ̄ falls into HYBRID)

Tier Distribution:
  SLM:    5 UCs  (62.5%)  → UC3, UC4, UC5, UC7, UC8
  HYBRID: 2 UCs  (25.0%)  → UC1, UC2
  LLM:    1 UC   (12.5%)  → UC6
```

### Visual: Which UCs Fall Where?

```
      0.00        0.30    0.50    0.70        1.00
       |-----------|-----------|-----------|
 LLM   |←UC6 (0.0033)      UC2 (0.3333)  UC1 (0.6940) UC3,4,5,7,8
       |                   HYBRID ZONE            SLM ZONE
```

**Problem**: UC1 (0.6940) is VERY CLOSE to the SLM threshold (0.70). Just 1% away!

---

## Sensitivity Analysis Results

Tested 48 configurations across ranges:
- **SLM threshold**: 0.50 to 0.85
- **LLM threshold**: 0.10 to 0.35
- **Step**: 0.05

### Objective 1: MINIMIZE HYBRID TIER (Clearest Classification)

**Optimal: (0.50, 0.35)**

```
Distribution:
  SLM:    6 UCs  (75%)   → Gain: UC1
  HYBRID: 0 UCs  (0%)    ← Remove: UC1, UC2
  LLM:    2 UCs  (25%)   → Gain: UC2

Impact: UC1 → SLM, UC2 → LLM (no ambiguity)
```

**Why this works**:
- UC1 (ρ̄=0.6940 > 0.50) → confident enough for SLM
- UC2 (ρ̄=0.3333 < 0.35) → falls below LLM threshold
- Zero UCs in HYBRID: Clear yes/no decision for every UC

**Trade-off**: UC2 moves to LLM (requires LLM even though some routing was SLM)

---

### Objective 2: MAXIMIZE SLM COVERAGE (Lowest Cost)

**Optimal: (0.50, 0.10)**

```
Distribution:
  SLM:    6 UCs  (75%)   → Gain: UC1
  HYBRID: 1 UC   (12.5%) → UC2 (in middle)
  LLM:    1 UC   (12.5%) → UC6 (still LLM)

Impact: UC1 → SLM (cheaper), UC2 stays HYBRID (careful review)
```

**Why this works**:
- Lower SLM threshold (0.50) pulls UC1 into SLM tier
- Still uses 75% SLM coverage
- UC2 stays in HYBRID for careful review (ρ̄=0.3333 is in the 0.10-0.50 gap)

**Benefit**: Save money on UC1 (use SLM instead of HYBRID) while keeping UC2 safe

**Trade-off**: UC1 uses SLM exclusively (no LLM fallback option)

---

### Objective 3: MAXIMIZE GAP (Clearest Tier Separation)

**Optimal: (0.85, 0.10)**

```
Configuration:     0.85 / 0.10
Gap:              0.75 (huge gap - Paper has 0.40)

Distribution:
  SLM:    5 UCs  (62.5%) → UC3, UC4, UC5, UC7, UC8
  HYBRID: 2 UCs  (25%)   → UC1, UC2
  LLM:    1 UC   (12.5%) → UC6

Same as Paper!
```

**Why this works**:
- Much wider HYBRID zone (0.10 to 0.85)
- More room for nuance and exceptions
- "Strong confidence needed before SLM" (threshold=0.85)
- "Only certain LLM if very low confidence" (threshold=0.10)

**Benefit**: Conservative approach - requires very high confidence for SLM tier

**Trade-off**: Only the most confident UCs use SLM (UC3,4,5,7,8 with ρ̄≥0.85)

---

## Side-by-Side Comparison

| Aspect | Paper (0.70/0.30) | Minimize HYBRID | Maximize SLM | Maximize GAP |
|--------|------------------|-----------------|--------------|-------------|
| **SLM Threshold** | 0.70 | **0.50** | **0.50** | 0.85 |
| **LLM Threshold** | 0.30 | **0.35** | **0.10** | 0.10 |
| **Gap (HYBRID zone)** | 0.40 | 0.15 | 0.40 | 0.75 |
| **SLM Coverage** | 62.5% | 75% | 75% | 62.5% |
| **HYBRID Count** | 2 | **0** | 1 | 2 |
| **LLM Count** | 1 | 2 | 1 | 1 |
| **Decision Clarity** | Good | **Best** | Good | Conservative |
| **Cost** | Moderate | Low | **Lowest** | Moderate |

---

## Per-UC Impact

### UC1 (SMS Threat Detection, ρ̄=0.6940)

```
Paper (0.70):      HYBRID  (borderline - just below threshold)
Min HYBRID (0.50): SLM     (confident enough)
Max SLM (0.50):    SLM     (confident enough)
Max Gap (0.85):    HYBRID  (requires very high confidence)
```

**Insight**: UC1 is CRITICAL to the choice. At ρ̄=0.6940, it's:
- Just missing the Paper's SLM threshold (needs 0.70)
- Easily clears lower thresholds (0.50)
- Fails strict thresholds (0.85)

**Recommendation**: If UC1 is truly 69.4% SLM-routable, use threshold ≤0.69 to capture it.

### UC2 (Invoice Extraction, ρ̄=0.3333)

```
Paper (0.30):      HYBRID  (just above LLM threshold)
Min HYBRID (0.35): LLM     (crosses LLM boundary)
Max SLM (0.10):    HYBRID  (stays in middle)
Max Gap (0.85):    HYBRID  (stays in middle)
```

**Insight**: UC2 is sensitive to LLM threshold changes:
- Tighten to 0.35 → becomes LLM-only
- Keep at 0.30 or loosen to 0.10 → stays HYBRID

**Recommendation**: UC2 probably deserves HYBRID tier (high model divergence suggests uncertainty).

---

## Key Observations

### 1. UC1 is a Boundary Case (0.6940)

Very close to Paper's 0.70 threshold. Three options:

**Option A: Accept UC1 as HYBRID** (Paper's choice)
- Acknowledgment: UC1 is not quite SLM-confident enough
- Action: Use human review for UC1 outputs
- Threshold: 0.70/0.30

**Option B: Drop threshold slightly to capture UC1**
- Assumption: UC1 is close enough to SLM capability
- Action: Lower SLM threshold to 0.69 or 0.68
- Threshold: ~0.68/0.30

**Option C: Shift to 0.50 (Objective 2)**
- Assumption: UC1 IS SLM-capable despite ρ̄<0.70
- Action: Use SLM, monitor performance
- Threshold: 0.50/0.10

---

### 2. UC2 Needs Human Judgment (0.3333)

The high model divergence (0.5b:100%, 3b/7b:0%) suggests:
- Models genuinely disagree on invoice extraction
- Feature extraction or learned models may be noisy
- UC2 MUST stay in HYBRID tier for review

**Recommendation**: Never move UC2 to SLM-only, keep some LLM option.

---

### 3. Paper's 0.70/0.30 is Conservative

The Paper's thresholds emphasize **clarity over efficiency**:
- UC1 stays HYBRID (uncertain)
- UC2 stays HYBRID (divergent)
- 5 UCs confidently SLM, 1 confidently LLM

**If you want more SLM usage**: Lower to 0.50/0.10 (saves costs, 75% SLM coverage)  
**If you want more certainty**: Raise to 0.85/0.10 (requires higher confidence)

---

## Recommendations

### For Cost-Conscious Deployment

**Use: 0.50 / 0.10**
- SLM coverage: 75% (vs 62.5%)
- Moves UC1 from HYBRID to SLM
- UC2 stays HYBRID (careful review)
- **Benefit**: Save on UC1 SLM+LLM hybrid approach

### For Maximum Clarity

**Use: 0.50 / 0.35**
- No HYBRID tier (all or nothing)
- UC1 → SLM, UC2 → LLM
- **Benefit**: Every UC has a clear tier, no ambiguity
- **Cost**: UC2 fully LLM (more expensive)

### For Maximum Safety

**Use: 0.85 / 0.10**
- Very high SLM threshold
- Same distribution as Paper
- **Benefit**: Conservative, requires strong evidence for SLM
- **Cost**: Only highest-confidence UCs use SLM

### Default Recommendation

**Stick with Paper's 0.70/0.30 UNLESS:**
- ✅ You want to reduce LLM costs → use 0.50/0.10
- ✅ You want maximum clarity → use 0.50/0.35
- ✅ You want maximum safety → use 0.85/0.10

---

## Output Files

- `model_runs/uc_tier_sensitivity.json` - All 48 configurations with metrics
- `model_runs/uc_tier_sensitivity.png` - 4-panel visualization showing:
  - Panel 1: Tier coverage vs SLM threshold
  - Panel 2: HYBRID count vs configuration
  - Panel 3: SLM coverage vs LLM threshold
  - Panel 4: Side-by-side configuration comparison

---

## Next Steps

1. **Validate**: Does empirical data support these thresholds?
2. **Choose**: Which objective matters most for your use case?
3. **Deploy**: Implement chosen thresholds in routing pipeline
4. **Monitor**: Track real-world tier assignment accuracy
5. **Iterate**: Refine based on actual performance data

---

**Status**: ✅ Analysis complete - Ready for deployment decision
