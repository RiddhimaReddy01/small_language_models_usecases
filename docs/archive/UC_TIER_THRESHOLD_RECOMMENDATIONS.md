# UC Tier Threshold Recommendations

**Analysis Date**: 2026-04-19

---

## Quick Reference: Threshold Options

```
CURRENT (Paper)     Minimize HYBRID    Maximize SLM       Maximize Gap
─────────────────   ─────────────────  ─────────────────  ─────────────
0.70 / 0.30         0.50 / 0.35        0.50 / 0.10        0.85 / 0.10
Gap: 0.40           Gap: 0.15          Gap: 0.40          Gap: 0.75

SLM: 5              SLM: 6             SLM: 6             SLM: 5
HYB: 2              HYB: 0             HYB: 1             HYB: 2
LLM: 1              LLM: 2             LLM: 1             LLM: 1
```

---

## Recommendation by Objective

### 🎯 Objective: Reduce Costs (Most SLM Usage)

**RECOMMENDED: 0.50 / 0.10**

| Metric | Value |
|--------|-------|
| SLM Threshold | 0.50 |
| LLM Threshold | 0.10 |
| SLM Coverage | 75% (vs 62.5%) |
| Cost Reduction | ~12.5% fewer UCs need LLM |
| Decision Type | 6 SLM, 1 HYBRID, 1 LLM |

**How it changes assignments:**
- UC1 (ρ̄=0.6940): HYBRID → **SLM** ✓ (confidence improvement)
- UC2 (ρ̄=0.3333): HYBRID → **HYBRID** (stays carefully reviewed)
- All others: unchanged

**Risk**: UC1 uses SLM without LLM fallback option

---

### 🎯 Objective: Maximum Clarity (No Ambiguity)

**RECOMMENDED: 0.50 / 0.35**

| Metric | Value |
|--------|-------|
| SLM Threshold | 0.50 |
| LLM Threshold | 0.35 |
| HYBRID Count | 0 (zero ambiguity) |
| Decision Type | 6 SLM, 0 HYBRID, 2 LLM |

**How it changes assignments:**
- UC1 (ρ̄=0.6940): HYBRID → **SLM** ✓
- UC2 (ρ̄=0.3333): HYBRID → **LLM** ✗
- All others: unchanged

**Benefit**: Every UC gets a clear decision - no uncertain middle ground

**Risk**: UC2 becomes LLM-only (more expensive) even though some routing was SLM

---

### 🎯 Objective: Conservative Approach (Maximum Safety)

**RECOMMENDED: 0.85 / 0.10**

| Metric | Value |
|--------|-------|
| SLM Threshold | 0.85 |
| LLM Threshold | 0.10 |
| SLM Threshold Requirement | Very high (ρ̄ must be ≥0.85) |
| UCs Meeting Criteria | Only UC3, UC4, UC5, UC7, UC8 |
| Decision Type | 5 SLM, 2 HYBRID, 1 LLM |

**How it changes assignments:**
- All other UCs: unchanged (same as Paper)
- Emphasis: Only strongest SLM candidates get SLM tier

**Benefit**: Maximum confidence before using SLM

**Risk**: UC1 stays HYBRID (costs more than needed?)

---

### 🎯 Objective: Minimal Change from Paper

**RECOMMENDED: 0.70 / 0.30** (stay with Paper)

| Metric | Value |
|--------|-------|
| SLM Threshold | 0.70 |
| LLM Threshold | 0.30 |
| Change from Paper | None - use existing guidance |
| Familiarity | Proven in research |

**Why**: No change means minimal implementation risk

---

## Decision Matrix: Choose Your Objective

### Cost Minimization?
```
Priority: Reduce LLM usage
          ↓
        0.50 / 0.10
          ↓
   SLM: 75% coverage
   Cost savings on UC1
```

### Maximum Clarity?
```
Priority: No ambiguous (HYBRID) UCs
          ↓
        0.50 / 0.35
          ↓
   Zero HYBRID tier
   Every UC clearly SLM or LLM
```

### Maximum Safety?
```
Priority: High confidence before SLM
          ↓
        0.85 / 0.10
          ↓
   Only strong SLM candidates
   Conservative routing
```

### Stick with Paper?
```
Priority: Minimal change, proven approach
          ↓
        0.70 / 0.30
          ↓
   Known results
   No implementation risk
```

---

## The Critical UC: UC1 (ρ̄=0.6940)

UC1 is just **0.006 below the Paper's SLM threshold**. Your choice determines its tier:

```
0.70 threshold: UC1 → HYBRID  (Paper's choice)
0.69 threshold: UC1 → SLM     (barely makes it)
0.68 threshold: UC1 → SLM     (safe margin)
0.50 threshold: UC1 → SLM     (confident)
0.85 threshold: UC1 → HYBRID  (requires higher confidence)
```

**Question for deployment**: Is UC1 "close enough" to be SLM, or should it stay HYBRID?

---

## Implementation Checklist

### If you choose 0.50 / 0.10 (Cost Optimization):
- [ ] Update tier assignment code: `slm_threshold = 0.50`, `llm_threshold = 0.10`
- [ ] Verify UC1 actually succeeds with SLM (monitor accuracy)
- [ ] Adjust UC2 review process (still HYBRID)
- [ ] Measure cost savings vs Paper baseline
- [ ] Track tier assignment misalignment

### If you choose 0.50 / 0.35 (Maximum Clarity):
- [ ] Update tier assignment code: `slm_threshold = 0.50`, `llm_threshold = 0.35`
- [ ] Prepare for UC2 to be LLM-only (budget for it)
- [ ] Remove HYBRID tier handling code (no ambiguity)
- [ ] Simplify deployment (clear routing rules)

### If you choose 0.85 / 0.10 (Conservative):
- [ ] Update tier assignment code: `slm_threshold = 0.85`, `llm_threshold = 0.10`
- [ ] This keeps the same distribution as Paper
- [ ] Minimal change from current approach
- [ ] Verify wider HYBRID zone (0.10 to 0.85) is acceptable

### If you stay with Paper (0.70 / 0.30):
- [ ] No code changes needed
- [ ] Continue monitoring UC1 (borderline case)
- [ ] Accept UC2 HYBRID tier (with review process)
- [ ] Document decision rationale

---

## Sensitivity Analysis Data

Complete sweep tested:
- **48 different threshold combinations**
- **SLM range**: 0.50 to 0.85 (step 0.05)
- **LLM range**: 0.10 to 0.35 (step 0.05)

Results saved:
- `model_runs/uc_tier_sensitivity.json` - All metrics
- `model_runs/uc_tier_sensitivity.png` - Visualization

---

## Summary Table

| Threshold | SLM % | HYBRID | Clarity | Safety | Cost | Recommended For |
|-----------|-------|--------|---------|--------|------|-----------------|
| 0.70/0.30 | 62.5% | 2 | Good | Good | Medium | Paper alignment |
| 0.50/0.10 | 75% | 1 | Good | Good | **Low** | **Cost reduction** |
| 0.50/0.35 | 75% | 0 | **Best** | Medium | Low | **No ambiguity** |
| 0.85/0.10 | 62.5% | 2 | Good | **High** | Medium | **Safety first** |

---

**Choose wisely—your threshold choice directly impacts cost, clarity, and risk!**

