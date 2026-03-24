# SLM/LLM Hybrid Routing Pipeline - Complete Walkthrough

## Overview: The Problem Being Solved

**Goal**: Intelligently route requests between:
- **SLM** (Small Language Model): 1.5B-4B parameters (fast, cheap, runs locally)
- **LLM** (Large Language Model): 70B+ parameters (accurate, expensive, cloud API)

**Decision**: For each incoming request, should we use the fast/cheap SLM or the slow/expensive LLM?

**Answer**: Depends on task **difficulty**. Easy tasks → SLM. Hard tasks → LLM.

---

## THE THREE-PHASE PIPELINE

### PHASE 0: ONE-TIME ANALYSIS (Offline, Run Once)
**Purpose**: Learn what the SLM can and can't do
**Input**: Benchmark dataset (100-1000 samples per task)
**Output**: Frozen routing policy

#### Step-by-Step Flow:

```
PHASE 0: ONE-TIME ANALYSIS

STEP 1: Data Normalization
├─ Standardize outputs into canonical schema
├─ Extract: input, output, success/failure
└─ Normalize across 8 different task formats

STEP 2: Compute Difficulty Vector
├─ For each sample, compute 6-dimensional difficulty:
├─ n_in: input length
├─ H: entropy of vocabulary
├─ R: reasoning required
├─ |Γ|: constraint count
├─ α: stylistic requirements
└─ D: output diversity

STEP 3: Bin Samples by Difficulty
├─ Group samples into 5 buckets:
├─ Bin 0: Very easy (0.0-0.25)
├─ Bin 1: Easy (0.25-0.5)
├─ Bin 2: Medium (0.5)
├─ Bin 3: Hard (0.75)
└─ Bin 4: Very hard (0.875-1.0)

STEP 4: Compute Capability Curve
├─ For each bin: P(SLM succeeds) = successes / total
├─ Result: {0: 0.95, 1: 0.85, 2: 0.60, 3: 0.30, 4: 0.10}
└─ Shows: SLM is good at easy, bad at hard

STEP 5: Compute Risk Curve
├─ For each bin: P(SLM fails badly) = bad_outputs / total
├─ Result: {0: 0.02, 1: 0.05, 2: 0.15, 3: 0.40, 4: 0.70}
└─ Shows: Risk increases with difficulty

STEP 6: Detect Tipping Points (THE KEY INNOVATION)
├─ τ_cap = Last bin where capability >= 0.80
│          = Bin 1 (0.85 >= 0.80)
│          = "SLM is capable up to Bin 1"
│
└─ τ_risk = First bin where risk > 0.20
           = Bin 2 (0.15 < 0.20, so check Bin 3)
           = Bin 3 (0.40 > 0.20)
           = "Risk becomes unacceptable at Bin 3"

STEP 7: Classify into 4 Quadrants
├─ Q1: Capable & Safe (Bins 0-1)
│      Strategy: Use SLM directly
│
├─ Q2: Capable but Risky (Bin 2)
│      Strategy: Use SLM but verify output
│
├─ Q3: Incapable but Safe (empty in this example)
│      Strategy: Use hybrid (SLM + escalate if needed)
│
└─ Q4: Incapable & Risky (Bins 3-4)
       Strategy: Use LLM

STEP 8: Freeze Policy
└─ Save routing decision to policy file (production-ready)
```

**PHASE 0 OUTPUT**: 16 routing policy files (8 tasks × 2 models)

---

### PHASE 1: PER-REQUEST ROUTING (Online, ~100ms per request)
**Purpose**: For each incoming request, decide SLM vs LLM in real-time
**Input**: Single user request
**Output**: Selected model + decision

#### Step-by-Step Example:

Request: "Generate a Python sorting algorithm"

```
STEP 1: Extract Input Text
└─ "Generate a Python sorting algorithm"

STEP 2: Compute Difficulty Score
├─ Apply 6-dimensional metric:
├─ Input length: short → n_in = 0.04
├─ Vocabulary entropy: common words → H = 0.3
├─ Reasoning required: minimal → R = 0.2
├─ Constraints: just "Python" → |Γ| = 1
├─ Style sensitivity: low → α = 0.1
├─ Output diversity: many valid answers → D = 1.0
└─ Combined difficulty = 0.25 (easy-to-medium)

STEP 3: Assign to Difficulty Bin
├─ Formula: bin_position = difficulty * 4
├─ bin_position = 0.25 * 4 = 1.0
├─ Probabilistic interpolation:
│  ├─ lower_bin = 1, upper_bin = 1
│  └─ Probabilities: {0: 0, 1: 1.0, 2: 0, 3: 0, 4: 0}
└─ Assign to BIN 1

STEP 4: Look Up Routing Policy
├─ From frozen policy: "Bin 1 is in Q1"
├─ Q1 = "Capable and Safe"
└─ Decision: Use SLM directly

STEP 5: Apply Zone-Specific Strategy
├─ Q1 means no verification needed
├─ Send request to SLM
├─ Get response back
├─ Return to user
└─ Latency: 250ms (SLM only)

STEP 6: Log Decision
└─ Record:
   ├─ Input text
   ├─ Difficulty score: 0.25
   ├─ Assigned bin: 1
   ├─ Zone: Q1
   ├─ Model selected: SLM
   ├─ Cost: $0.001
   └─ Quality will be assessed in Phase 2
```

**PHASE 1 TIMING**: ~100ms total
- Difficulty computation: 1ms
- Policy lookup: <1ms
- SLM inference: 100-500ms
- **Total: 100-501ms**

**PHASE 1 OUTPUT**: Routing decision + model response delivered to user

---

### PHASE 2: DAILY MONITORING (Background, Once Per Day)
**Purpose**: Detect model degradation, alert if something is wrong
**Input**: Logs from all Phase 1 requests (24 hours)
**Output**: Degradation alerts, policy adjustment recommendations

#### Step-by-Step Flow:

```
STEP 1: Collect Data
├─ Aggregate all requests from past 24 hours
└─ Example: 10,000 requests total

STEP 2: Recompute Curves from Real Data
├─ Old curves (Phase 0 benchmark):
│  └─ Bin 1 success rate: 0.85
│
├─ New curves (Phase 2 live data):
│  └─ Bin 1 success rate: 0.80 (slight drop)
│
└─ Alert if drop > 10% (would be critical)

STEP 3: Check for Anomalies
├─ Drop > 10% in capability? NO
├─ Increase > 10% in risk? NO
├─ New failure modes? NO
└─ Result: All systems operational

STEP 4: Optional Threshold Retraining
├─ If distribution shifted significantly:
├─ Recompute τ_cap and τ_risk
└─ Update policy if needed

STEP 5: Generate Report
└─ Output:
   ├─ Daily performance summary
   ├─ Alerts and thresholds
   ├─ Recommendations
   └─ Historical trending
```

**PHASE 2 TIMING**: ~30 seconds (runs once daily, overnight)

**PHASE 2 OUTPUT**: Monitoring report + alerts (if any)

---

## Full Request Journey Example

### Request: "Generate a Python sorting algorithm"

**PHASE 0 (OFFLINE - happens once)**:
```
Benchmark analysis finds:
├─ SLM succeeds 80% on medium code generation
├─ Risk stays low at medium difficulty
├─ Decision: τ_cap = 2, τ_risk = 4
├─ Route bin 1 to Q1 (use SLM)
└─ Policy frozen and saved to disk ✓
```

**PHASE 1 (ONLINE - happens in real-time)**:
```
1. User sends request
2. Compute difficulty = 0.35
3. Assign to bin 1
4. Lookup policy: bin 1 → Q1
5. Q1 = use SLM directly (no verification)
6. Send to SLM
7. SLM returns: "def sort_list(lst): return sorted(lst)"
8. Return to user in 250ms
9. Log decision

Result:
├─ User gets answer in 250ms
├─ Cost: $0.001
└─ Quality logged for monitoring ✓
```

**PHASE 2 (NIGHTLY - happens once per day)**:
```
Next morning, review logs:
├─ 10,000 requests yesterday
├─ 8,000 routed to SLM (cost: $8)
├─ 2,000 routed to LLM (cost: $20)
├─ SLM success rate: 83% (up from 80% benchmark)
├─ No degradation detected
└─ Report: "All systems operational ✓"
```

---

## The Two-Tipping-Point Innovation

This system uses **TWO independent thresholds**:

```
τ_cap (Capability Tipping Point)
├─ Question: Does SLM have the SKILLS?
├─ Based on: Success rate curve
├─ Answers: "SLM is capable up to bin N"
└─ Example: τ_cap = 1 means bins 0-1 are doable

τ_risk (Risk Tipping Point)
├─ Question: Is SLM's output SAFE?
├─ Based on: Risk/failure curve
├─ Answers: "Risk becomes unacceptable at bin N"
└─ Example: τ_risk = 3 means bins 0-2 are safe, 3+ are risky
```

**Why This Matters**:
- SLM might be **capable** at difficulty 0.8 (can solve it)
- But **risky** at difficulty 0.6 (might produce harmful output)
- So use SLM at 0.8 without checking, but add verification at 0.6

---

## Performance Characteristics

| Aspect | Value |
|--------|-------|
| Phase 0 Time | 10 minutes (one-time, offline) |
| Phase 1 Latency | 100ms with SLM vs 2sec with LLM |
| Phase 2 Time | 30 seconds (daily batch) |
| SLM Cost | $0.001 per request |
| LLM Cost | $0.01 per request |
| Average Cost | $0.002/request (80% SLM routing) |
| **Total Savings** | **80% cost reduction** vs always LLM |

---

## Why This Architecture Works

### 1. Offline Learning (Phase 0)
- Expensive analysis happens ONCE
- Frozen policy can't degrade unexpectedly
- Parallelizable (analyze all tasks simultaneously)

### 2. Fast Routing (Phase 1)
- O(1) policy lookup, no ML inference
- 100ms is production-ready
- Difficulty metric is lightweight (text statistics)

### 3. Safety Monitoring (Phase 2)
- Real-world performance tracked continuously
- Degradation caught within 24 hours
- Can adjust policy if distribution shifts

### 4. Two-Tipping-Point Logic
- Separates capability from risk (two different curves)
- Nuanced routing decisions (use SLM but verify)
- Prevents both under-trusting weak models AND over-cautious routing

---

## Summary: What Each Phase Does

| Phase | When | Input | What It Does | Output | Cost |
|-------|------|-------|--------------|--------|------|
| **0** | Once per task | Benchmark dataset | Learns SLM's strengths/weaknesses | Frozen policy | 10 min |
| **1** | For every request | User input | Routes request in real-time | Selected model | 100ms |
| **2** | Once per day | Request logs | Monitors for degradation | Alerts report | 30 sec |

---

## The Math Behind Binning

```
Difficulty Score: 0.0 to 1.0 (computed from difficulty vector)

Convert to bin position:
  bin_position = difficulty_score * (num_bins - 1)

Example with 5 bins:
  difficulty 0.0  → position 0.0   → bin 0
  difficulty 0.1  → position 0.4   → bin 0 (mostly)
  difficulty 0.25 → position 1.0   → bin 1
  difficulty 0.5  → position 2.0   → bin 2
  difficulty 0.75 → position 3.0   → bin 3
  difficulty 1.0  → position 4.0   → bin 4

Probabilistic assignment (linear interpolation):
  If bin_position = 1.4:
    lower_bin = 1, upper_bin = 2, fraction = 0.4
    probabilities: {0: 0, 1: 0.6, 2: 0.4, 3: 0, 4: 0}
    argmax (most likely) = bin 1

This creates smooth transitions between bins.
```
