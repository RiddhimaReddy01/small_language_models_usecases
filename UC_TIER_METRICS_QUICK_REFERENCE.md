# UC Tier Metrics: Quick Reference Card

---

## The 5 Metrics at a Glance

**METRIC 1: Tier Diversity Score (Balance)**
- What: How balanced are SLM/HYBRID/LLM tiers?
- Scale: 0 (all in one tier) to 1.0 (perfectly balanced)
- Higher: Better (fairer distribution)
- Paper: 0.594 (moderately balanced: 5-2-1 split)
- Best: Paper and Max Gap (both 0.594)

**METRIC 2: Robustness Score (Stability)**
- What: How stable are tier assignments?
- Scale: 0 (fragile) to 1.0 (very stable)
- Higher: Better (tier won't flip with small changes)
- Paper: 1.000 (excellent, but UC1 is fragile!)
- Best: All configs score 1.000 (excellent)
- Problem: Paper has UC1 at risk (1.5% confidence)

**METRIC 3: Mean Confidence (Certainty)**
- What: On average, how confident are assignments?
- Scale: 0% (very uncertain) to 100% (very certain)
- Higher: Better (more confident tier assignments)
- Paper: 68.5% (moderate confidence)
- Best: Cost Opt (80.1%) - highest overall confidence

**METRIC 4: Min Confidence (Risk Indicator)**
- What: What's the riskiest (most fragile) UC?
- Scale: 0% (dangerously fragile) to 100% (very safe)
- Higher: Better (no fragile UCs)
- Paper: 1.5% (UC1 is dangerously close to boundary!)
- Best: Cost Opt (38.8%) - fixes UC1 fragility
- Problem: Clarity Opt (4.8%) - creates new UC2 risk

**METRIC 5: Gap (Tier Separation)**
- What: How wide is the HYBRID zone?
- Scale: 0 (no HYBRID) to 1.0 (maximum separation)
- Higher: More nuance (more UCs in HYBRID middle ground)
- Paper: 0.40 (moderate gap: HYBRID from 0.30 to 0.70)
- Best: Depends on preference:
  - Large gap (0.75) for nuance → Max Gap
  - Small gap (0.15) for clarity → Clarity Opt
  - Medium gap (0.40) for balance → Paper

---

## Configuration Comparison Table

| Configuration | Diversity | Robustness | Confidence | Min Risk | Gap | SLM% |
|---|---|---|---|---|---|---|
| **Paper (0.70/0.30)** | 0.59 (good) | 1.00 | 68.5% | 1.5% ❌ | 0.40 | 62% |
| **Cost Opt (0.50/0.10)** | 0.22 (bad) | 1.00 | 80.1% ✓ | 38.8% ✓✓ | 0.40 | 75% |
| **Clarity (0.50/0.35)** | 0.13 (bad) | 1.00 | 75.7% | 4.8% | 0.15 | 75% |
| **Max Gap (0.85/0.10)** | 0.59 (good) | 1.00 | 65.0% | 8.1% ✓ | 0.75 | 62% |

---

## The UC1 Problem: Paper's Fragility

```
Paper uses threshold 0.70
UC1 has rho_bar = 0.6940

Distance: 0.0060 (6 hundredths!)
Risk: DANGEROUSLY CLOSE TO BOUNDARY

Confidence: 1.5%
Meaning: Tiny threshold change flips UC1's tier

Your choice:
  A) Accept the risk (Paper)           → 1.5% confidence
  B) Lower threshold to 0.50 (Cost)    → 38.8% confidence
  C) Eliminate HYBRID (Clarity)        → 4.8% confidence
```

---

## Quick Decision Guide

**"I want balanced tiers"**
- Use: Paper (0.70/0.30)
- Pro: Most balanced (5-2-1)
- Con: UC1 is fragile (1.5%)

**"I want high confidence"** ← RECOMMENDED
- Use: Cost Opt (0.50/0.10)
- Pro: Highest confidence (80.1%)
- Pro: Fixes UC1 fragility (38.8%)
- Con: Imbalanced (6-1-1)

**"I want zero ambiguity"**
- Use: Clarity Opt (0.50/0.35)
- Pro: No HYBRID tier
- Con: UC2 becomes fragile (4.8%)

**"I want maximum nuance"**
- Use: Max Gap (0.85/0.10)
- Pro: Widest HYBRID zone (0.75)
- Con: Lower confidence (65%)

---

## Top Recommendation

**Use: Cost Opt (0.50/0.10)**

### Why?
✅ Fixes UC1 fragility - 38.8% confidence (vs 1.5% in Paper!)
✅ Highest overall confidence - 80.1% (vs 68.5%)
✅ Same gap as Paper - 0.40 (same nuance level)
✅ All UCs have 5%+ safety margin - no fragile borderline cases

### Trade-off?
❌ More UCs use SLM (75% vs 62%) - saves cost but less balanced

### Bottom Line?
**Paper's 0.70 threshold is risky. UC1 at 0.6940 is too close. Lower to 0.50 for safety.**

---

## Key Insight

**Robustness is not the problem** - all configs score 1.0 (excellent)

**Real differences**:
1. **Min Confidence** - Paper has UC1 at risk (1.5%)
2. **Mean Confidence** - Cost Opt has highest (80.1%)
3. **Diversity** - Paper most balanced (0.59)
4. **Gap** - Cost Opt and Paper both 0.40

**The critical metric: Min Confidence**
- Paper: 1.5% (UC1 fragile) ❌
- Cost Opt: 38.8% (UC1 safe) ✅✅
- Clarity: 4.8% (UC2 fragile) ⚠️

**Choose Cost Opt to fix the UC1 fragility problem.**

---

## Output Files

- `model_runs/uc_tier_metrics_v2.json` - All 5 metrics for all 48 configurations
- `model_runs/uc_tier_metrics_v2.png` - 6-panel visualization

