# UC Tier Threshold Metrics: Complete Guide

**Date**: 2026-04-19  
**Focus**: 5 Key Metrics (No Ground Truth Needed)

---

## Overview: 5 Metrics That Matter

Instead of "accuracy" (which requires ground truth), we use these **5 structural metrics** to evaluate tier threshold configurations:

| Metric | Measures | Scale | What's Good? |
|--------|----------|-------|--------------|
| **Tier Diversity Score** | Balance across tiers | 0 to 1.0 | Higher = more balanced |
| **Robustness Score** | Stability of assignments | 0 to 1.0 | Higher = more stable |
| **Mean Confidence** | Average certainty | 0 to 100% | Higher = more certain |
| **Min Confidence** | Risk indicator | 0 to 100% | Higher = safer |
| **Gap** | Tier separation width | 0 to 1.0 | Context-dependent |

---

## METRIC 1: Tier Diversity Score (Balance)

### What It Measures

**How evenly are UCs distributed across SLM/HYBRID/LLM tiers?**

```
Perfect Balance (Score = 1.0):
  SLM:    2.67 UCs
  HYBRID: 2.67 UCs
  LLM:    2.67 UCs

Imbalanced (Score = 0.0):
  SLM:    8 UCs
  HYBRID: 0 UCs
  LLM:    0 UCs
```

### Why It Matters

**Balanced tiers** = Fair allocation of UCs across cost/safety spectrum  
**Imbalanced tiers** = Bunching into one category (maybe too strict or too loose)

### Results from Our Analysis

```
Paper (0.70/0.30):
  Tiers: SLM=5, HYBRID=2, LLM=1
  Diversity Score: 0.594 (moderately balanced)

Cost Opt (0.50/0.10):
  Tiers: SLM=6, HYBRID=1, LLM=1
  Diversity Score: 0.219 (imbalanced - too many SLM)

Clarity Opt (0.50/0.35):
  Tiers: SLM=6, HYBRID=0, LLM=2
  Diversity Score: 0.125 (most imbalanced - no HYBRID)
```

### Interpretation

**Paper is most balanced** - closest to 3-3-2 split  
**Cost optimization bunches UCs into SLM** - cheaper but less balanced  
**Clarity optimization has no HYBRID** - cleanest decision, no ambiguity

**Decision**: Do you want balanced tiers or clear decisions?

---

## METRIC 2: Robustness Score (Stability)

### What It Measures

**How much can thresholds move before tier assignments flip?**

```
High Robustness (Score = 1.0):
  UC is far from tier boundary
  Threshold can move ±0.20 without flipping
  Safe and stable

Low Robustness (Score = 0.0):
  UC is near tier boundary
  Small threshold move (±0.01) flips the tier
  Fragile and risky
```

### Why It Matters

**Robust assignments** = Reliable, won't change with small adjustments  
**Fragile assignments** = Unstable, easily disrupted

### How We Calculate It

```
For each UC, measure distance to nearest tier boundary:

UC1 (rho_bar=0.6940) with threshold 0.70:
  Distance = 0.6940 - 0.70 = -0.006 (very close!)
  Robustness = LOW (fragile)

UC1 (rho_bar=0.6940) with threshold 0.50:
  Distance = 0.6940 - 0.50 = 0.194 (far away!)
  Robustness = HIGH (stable)

Average across all UCs = Robustness Score
```

### Results from Our Analysis

```
Paper (0.70/0.30):
  Robustness Score: 1.000 (excellent)
  BUT: UC1 is dangerously fragile (1.5% confidence!)

Cost Opt (0.50/0.10):
  Robustness Score: 1.000 (excellent)
  UC1 is safer (38.8% confidence)

Clarity Opt (0.50/0.35):
  Robustness Score: 1.000 (excellent)
  UC2 is fragile (4.8% confidence)
```

### Interpretation

**All configurations score 1.0 because most UCs are far from boundaries**  
**But Paper's fragile UC1 (1.5%) is concerning**  
**Cost optimization fixes UC1, but creates new UC2 risk (4.8%)**

**Decision**: Which UC's risk can you accept?

---

## METRIC 3: Mean Confidence (Certainty)

### What It Measures

**On average, how confident are the tier assignments?**

```
High Confidence (80%):
  Most UCs are far from tier boundaries
  Tier assignments are clearly justified
  Few borderline cases

Low Confidence (40%):
  Many UCs are near boundaries
  Assignments are ambiguous
  Many borderline cases
```

### Why It Matters

**High confidence** = Assignments are clear and defensible  
**Low confidence** = Many "borderline" UCs need human review

### How We Calculate It

```
For each UC, compute confidence as:
  Distance to nearest boundary / Total zone width

UC1 in HYBRID zone (0.30 to 0.70):
  Position: 0.6940
  Distance to boundary: min(0.6940-0.30, 0.70-0.6940) = 0.0060
  Confidence = 0.0060 / 0.40 = 1.5% (VERY LOW!)

UC3 in SLM zone (>= 0.70):
  Position: 0.9407
  Distance to boundary: 0.9407 - 0.70 = 0.2407
  Confidence = 0.2407 / 0.30 = 80.2% (HIGH!)

Average across all 8 UCs = Mean Confidence
```

### Results from Our Analysis

```
Paper (0.70/0.30):
  Mean Confidence: 68.5%
  Interpretation: On average, 68.5% confident in assignments

Cost Opt (0.50/0.10):
  Mean Confidence: 80.1%
  Interpretation: More confident overall

Clarity Opt (0.50/0.35):
  Mean Confidence: 75.7%
  Interpretation: Moderate-to-high confidence
```

### Interpretation

**Cost optimization (80.1%) is more confident than Paper (68.5%)**  
**This is because it moves UC1 far from boundary** (fixes the fragility)  
**Clarity optimization (75.7%) is middle ground**

**Decision**: Do you want higher overall confidence?

---

## METRIC 4: Min Confidence (Risk Indicator)

### What It Measures

**What's the riskiest (most fragile) UC?**

```
High Min Confidence (40%):
  Even the riskiest UC is reasonably safe
  Good buffer against threshold changes

Low Min Confidence (1.5%):
  The riskiest UC is dangerously close to boundary
  Tiny threshold change flips its tier
```

### Why It Matters

**High min confidence** = No single UC is a problem  
**Low min confidence** = You have a "problem UC" that's fragile

### Results from Our Analysis

```
Paper (0.70/0.30):
  Min Confidence: 1.5%
  Riskiest UC: UC1
  Problem: UC1 is 0.006 below the SLM threshold (dangerously close!)

Cost Opt (0.50/0.10):
  Min Confidence: 38.8%
  Riskiest UC: UC1
  Solution: UC1 is now far from boundary (safe!)

Clarity Opt (0.50/0.35):
  Min Confidence: 4.8%
  Riskiest UC: UC2
  Trade-off: Fixed UC1, but UC2 is now fragile
```

### Interpretation

**Paper has a serious problem: UC1 at 1.5% confidence is risky**  
**Cost optimization solves UC1 completely (38.8%)**  
**Clarity optimization trades UC1 risk for UC2 risk**

**Decision**: Can you accept UC1's fragility, or should you fix it?

---

## METRIC 5: Gap (Tier Separation)

### What It Measures

**How wide is the HYBRID zone?**

```
Large Gap (0.75):
  HYBRID zone spans 0.75 width (0.10 to 0.85)
  Lots of room for nuance
  More UCs stay in HYBRID

Small Gap (0.15):
  HYBRID zone spans 0.15 width (0.35 to 0.50)
  Tight classification
  Fewer UCs in HYBRID
```

### Why It Matters

**Large gap** = Conservative (more HYBRID, requires high confidence for SLM)  
**Small gap** = Aggressive (fewer HYBRID, quick decision)

### Results from Our Analysis

```
Paper (0.70/0.30):
  Gap: 0.40
  HYBRID zone: 0.30 to 0.70
  UCs in HYBRID: 2 (UC1, UC2)

Cost Opt (0.50/0.10):
  Gap: 0.40
  HYBRID zone: 0.10 to 0.50
  UCs in HYBRID: 1 (UC2 only)

Clarity Opt (0.50/0.35):
  Gap: 0.15
  HYBRID zone: 0.35 to 0.50
  UCs in HYBRID: 0 (none!)

Maximum Gap (0.85/0.10):
  Gap: 0.75
  HYBRID zone: 0.10 to 0.85 (huge!)
  UCs in HYBRID: 2
```

### Interpretation

**Paper and Cost Opt have same gap (0.40)** but different HYBRID UCs  
**Clarity Opt has smallest gap (0.15)** - eliminates HYBRID entirely  
**Maximum Gap (0.75)** creates huge HYBRID zone for nuance

**Decision**: Do you want nuance (large gap) or clarity (small gap)?

---

## Side-by-Side Metric Comparison

```
Configuration          Diversity  Robustness  Confidence  Min Risk  Gap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paper (0.70/0.30)      0.594      1.000       68.5%       1.5%     0.40
  └─ Balanced, but UC1 is dangerously fragile

Cost Opt (0.50/0.10)   0.219      1.000       80.1%       38.8%    0.40
  └─ High confidence, fixes UC1, most UCs go SLM

Clarity Opt (0.50/0.35) 0.125     1.000       75.7%       4.8%     0.15
  └─ Zero ambiguity (no HYBRID), but UC2 fragile

Conservative (0.85/10) 0.594      1.000       65.0%       8.1%     0.75
  └─ Large HYBRID zone, same distribution as Paper
```

---

## How to Choose: Decision Framework

### If Balance Matters Most
→ **Paper (0.70/0.30)** wins  
✅ Most balanced tier distribution (5-2-1)  
❌ But UC1 is dangerously fragile (1.5%)

### If Confidence Matters Most
→ **Cost Opt (0.50/0.10)** wins  
✅ Highest mean confidence (80.1%)  
✅ Fixes UC1 fragility (38.8%)  
✅ Highest min confidence  
❌ Imbalanced (6-1-1 distribution)

### If You Want Zero Ambiguity
→ **Clarity Opt (0.50/0.35)** wins  
✅ No HYBRID tier (every UC has clear decision)  
✅ No ambiguous cases  
❌ UC2 becomes fragile (4.8%)  
❌ Most imbalanced (6-0-2)

### If You Want Maximum Nuance
→ **Conservative (0.85/0.10)** wins  
✅ Largest HYBRID zone (0.75)  
✅ Same distribution as Paper (5-2-1)  
❌ Lower confidence (65%)

---

## Key Takeaway: The UC1 Problem

```
Paper's 0.70 threshold puts UC1 RIGHT AT THE BOUNDARY:

UC1: rho_bar = 0.6940
     Paper threshold = 0.70
     Distance = 0.0060 (tiny!)
     Confidence = 1.5% (dangerous!)

Question: Is UC1 really HYBRID, or should it be SLM?

Answer 1 (Conservative): "UC1 is below 0.70, so HYBRID" (Paper's choice)
  → Accept the risk (1.5% confidence)

Answer 2 (Practical): "UC1 is close enough, move it to SLM" (Cost Opt)
  → Lower threshold to 0.50, gain confidence (38.8%)

Answer 3 (Extreme): "No HYBRID at all" (Clarity Opt)
  → Use 0.50/0.35, but creates UC2 risk (4.8%)
```

---

## Recommendation

**Use these metrics to evaluate thresholds:**

1. **Check Metric 4 (Min Confidence)** first - do you have fragile UCs?
2. **Check Metric 3 (Mean Confidence)** - is overall certainty acceptable?
3. **Check Metric 1 (Diversity)** - are tiers reasonably balanced?
4. **Check Metric 5 (Gap)** - how much nuance do you want?
5. **Metric 2 (Robustness)** is always high - less critical

**Our recommendation**: **Cost Opt (0.50/0.10)**  
✅ Fixes the UC1 fragility problem (38.8% vs 1.5%)  
✅ Higher overall confidence (80.1% vs 68.5%)  
✅ Same gap as Paper (0.40)  
❌ Accept that 75% of UCs will use SLM (vs 62%)

---

## Output Files

- `model_runs/uc_tier_metrics_v2.json` - All metrics for all 48 configurations
- `model_runs/uc_tier_metrics_v2.png` - 6-panel visualization showing how metrics change across thresholds

---

**Status**: ✅ Analysis complete with 5 meaningful, ground-truth-free metrics
