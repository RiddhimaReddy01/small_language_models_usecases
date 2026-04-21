# UC Tier Assignments: All 8 UCs Under Different Configurations

**Date**: 2026-04-19

---

## Empirical rho_bar Values

```
UC1: 0.6940  (SMS Threat Detection)        ← Close to boundaries!
UC2: 0.3333  (Invoice Extraction)          ← In middle ground
UC3: 0.9407  (Support Ticket Routing)      ← High confidence
UC4: 0.8760  (Product Review Sentiment)    ← High confidence
UC5: 1.0000  (Automated Code Review)       ← Perfect
UC6: 0.0033  (Clinical Triage)             ← Extremely low (LLM required)
UC7: 1.0000  (Legal Contract Risk)         ← Perfect
UC8: 1.0000  (Financial Report Drafting)   ← Perfect
```

---

## CONFIGURATION 1: PAPER (0.70 / 0.30)

### Tier Ranges
- **SLM**: rho_bar >= 0.70
- **HYBRID**: 0.30 < rho_bar < 0.70
- **LLM**: rho_bar <= 0.30

### Tier Assignments

| UC | rho_bar | Tier | Reason |
|---|---|---|---|
| UC1 | 0.6940 | **HYBRID** | 0.30 < 0.6940 < 0.70 |
| UC2 | 0.3333 | **HYBRID** | 0.30 < 0.3333 < 0.70 |
| UC3 | 0.9407 | **SLM** | 0.9407 >= 0.70 |
| UC4 | 0.8760 | **SLM** | 0.8760 >= 0.70 |
| UC5 | 1.0000 | **SLM** | 1.0000 >= 0.70 |
| UC6 | 0.0033 | **LLM** | 0.0033 <= 0.30 |
| UC7 | 1.0000 | **SLM** | 1.0000 >= 0.70 |
| UC8 | 1.0000 | **SLM** | 1.0000 >= 0.70 |

**Summary**: SLM=5, HYBRID=2, LLM=1  
**Problem**: UC1 is dangerously close (0.6940 vs 0.70 boundary, only 0.006 away!)

---

## CONFIGURATION 2: COST OPTIMIZATION (0.50 / 0.10)

### Tier Ranges
- **SLM**: rho_bar >= 0.50
- **HYBRID**: 0.10 < rho_bar < 0.50
- **LLM**: rho_bar <= 0.10

### Tier Assignments

| UC | rho_bar | Tier | Reason |
|---|---|---|---|
| UC1 | 0.6940 | **SLM** | 0.6940 >= 0.50 ← MOVED FROM HYBRID! |
| UC2 | 0.3333 | **HYBRID** | 0.10 < 0.3333 < 0.50 |
| UC3 | 0.9407 | **SLM** | 0.9407 >= 0.50 |
| UC4 | 0.8760 | **SLM** | 0.8760 >= 0.50 |
| UC5 | 1.0000 | **SLM** | 1.0000 >= 0.50 |
| UC6 | 0.0033 | **LLM** | 0.0033 <= 0.10 |
| UC7 | 1.0000 | **SLM** | 1.0000 >= 0.50 |
| UC8 | 1.0000 | **SLM** | 1.0000 >= 0.50 |

**Summary**: SLM=6, HYBRID=1, LLM=1  
**Benefit**: UC1 moved from HYBRID to SLM (fixes fragility!)  
**Cost**: 75% SLM coverage (vs 62% in Paper)

---

## CONFIGURATION 3: CLARITY OPTIMIZATION (0.50 / 0.35)

### Tier Ranges
- **SLM**: rho_bar >= 0.50
- **HYBRID**: [NONE - no middle ground]
- **LLM**: rho_bar <= 0.35

### Tier Assignments

| UC | rho_bar | Tier | Reason |
|---|---|---|---|
| UC1 | 0.6940 | **SLM** | 0.6940 >= 0.50 |
| UC2 | 0.3333 | **LLM** | 0.3333 <= 0.35 ← MOVED FROM HYBRID! |
| UC3 | 0.9407 | **SLM** | 0.9407 >= 0.50 |
| UC4 | 0.8760 | **SLM** | 0.8760 >= 0.50 |
| UC5 | 1.0000 | **SLM** | 1.0000 >= 0.50 |
| UC6 | 0.0033 | **LLM** | 0.0033 <= 0.35 |
| UC7 | 1.0000 | **SLM** | 1.0000 >= 0.50 |
| UC8 | 1.0000 | **SLM** | 1.0000 >= 0.50 |

**Summary**: SLM=6, HYBRID=0, LLM=2  
**Benefit**: ZERO ambiguity (no HYBRID tier at all!)  
**Cost**: UC2 becomes LLM-only (higher cost, but more decisive)

---

## CONFIGURATION 4: MAXIMUM NUANCE (0.85 / 0.10)

### Tier Ranges
- **SLM**: rho_bar >= 0.85
- **HYBRID**: 0.10 < rho_bar < 0.85
- **LLM**: rho_bar <= 0.10

### Tier Assignments

| UC | rho_bar | Tier | Reason |
|---|---|---|---|
| UC1 | 0.6940 | **HYBRID** | 0.10 < 0.6940 < 0.85 |
| UC2 | 0.3333 | **HYBRID** | 0.10 < 0.3333 < 0.85 |
| UC3 | 0.9407 | **SLM** | 0.9407 >= 0.85 |
| UC4 | 0.8760 | **SLM** | 0.8760 >= 0.85 |
| UC5 | 1.0000 | **SLM** | 1.0000 >= 0.85 |
| UC6 | 0.0033 | **LLM** | 0.0033 <= 0.10 |
| UC7 | 1.0000 | **SLM** | 1.0000 >= 0.85 |
| UC8 | 1.0000 | **SLM** | 1.0000 >= 0.85 |

**Summary**: SLM=5, HYBRID=2, LLM=1  
**Benefit**: Same distribution as Paper, but with much wider HYBRID zone (0.75)  
**Tradeoff**: Lower confidence, requires very high confidence for SLM

---

## Quick Comparison Table

| UC | Paper (0.70/0.30) | Cost Opt (0.50/0.10) | Clarity (0.50/0.35) | Max Nuance (0.85/0.10) |
|---|---|---|---|---|
| **UC1** | HYBRID | **SLM** | **SLM** | HYBRID |
| **UC2** | HYBRID | HYBRID | **LLM** | HYBRID |
| **UC3** | SLM | SLM | SLM | SLM |
| **UC4** | SLM | SLM | SLM | SLM |
| **UC5** | SLM | SLM | SLM | SLM |
| **UC6** | LLM | LLM | LLM | LLM |
| **UC7** | SLM | SLM | SLM | SLM |
| **UC8** | SLM | SLM | SLM | SLM |

---

## Visual Tier Ranges

### PAPER (0.70 / 0.30)
```
0.00     0.30          0.70     1.00
 |-------|-------------|---------|
LLM    HYBRID                SLM

UC6    UC1,UC2        UC3,UC4,UC5,UC7,UC8
```

### COST OPT (0.50 / 0.10)
```
0.00  0.10       0.50          1.00
 |-----|----------|-------------|
LLM  HYBRID            SLM

UC6  UC2         UC1,UC3,UC4,UC5,UC7,UC8
```

### CLARITY (0.50 / 0.35)
```
0.00   0.35  0.50              1.00
 |----|------|-----------------|
LLM  (NONE)   SLM

UC6  UC2      UC1,UC3,UC4,UC5,UC7,UC8
```

### MAX NUANCE (0.85 / 0.10)
```
0.00    0.10              0.85   1.00
 |------|----------|------|------|
LLM    HYBRID                SLM

UC6   UC1,UC2            UC3,UC4,UC5,UC7,UC8
```

---

## Key Insights by UC

### UC1 (rho_bar = 0.6940)
**Status**: Boundary UC - moves between HYBRID and SLM depending on threshold

| Config | Assignment | Distance to Boundary | Confidence |
|---|---|---|---|
| Paper (0.70) | HYBRID | 0.006 | 1.5% ❌ |
| Cost (0.50) | SLM | 0.194 | 38.8% ✓ |
| Clarity (0.50/0.35) | SLM | 0.194 | 38.8% ✓ |
| Nuance (0.85) | HYBRID | 0.16 | 21.3% |

**Conclusion**: UC1 is risky in Paper (too close to boundary). Cost Opt fixes it.

### UC2 (rho_bar = 0.3333)
**Status**: Middle-ground UC - moves between HYBRID and LLM depending on threshold

| Config | Assignment | Distance to Boundary | Confidence |
|---|---|---|---|
| Paper (0.70) | HYBRID | 0.033 | 8.3% |
| Cost (0.50) | HYBRID | 0.233 | 58.3% ✓ |
| Clarity (0.50/0.35) | LLM | 0.017 | 4.8% ❌ |
| Nuance (0.85) | HYBRID | 0.233 | 43.8% |

**Conclusion**: UC2 safest in Cost Opt (0.50/0.10). Clarity makes it risky.

### UCs 3-8 (rho_bar >= 0.8760 or <= 0.0033)
**Status**: Stable - no movement across any threshold configuration

- **UC3, UC4, UC7, UC8**: Always SLM (far from any boundary)
- **UC5**: Always SLM (perfect 1.0)
- **UC6**: Always LLM (extremely low 0.0033)

**Conclusion**: These UCs are safe regardless of threshold choice.

---

## Recommendation Summary

### Choose Based on UC Assignments:

**If you want UC1 to be SLM**:
→ Use Cost Opt (0.50/0.10) or Clarity (0.50/0.35)

**If you want UC1 to be HYBRID**:
→ Use Paper (0.70/0.30) or Max Nuance (0.85/0.10)

**If you want UC2 to be HYBRID**:
→ Use Paper (0.70/0.30), Cost Opt (0.50/0.10), or Max Nuance (0.85/0.10)

**If you want UC2 to be LLM**:
→ Use Clarity (0.50/0.35)

**If you want ZERO HYBRID tier**:
→ Use Clarity (0.50/0.35)

---

## RECOMMENDED CHOICE

**Use: Cost Opt (0.50/0.10)**

**Final UC Assignment**:
- SLM: UC1, UC3, UC4, UC5, UC7, UC8 (6 UCs - 75%)
- HYBRID: UC2 (1 UC - 13%)
- LLM: UC6 (1 UC - 13%)

**Why**: Fixes UC1 fragility while keeping UC2 safely in HYBRID for review.

