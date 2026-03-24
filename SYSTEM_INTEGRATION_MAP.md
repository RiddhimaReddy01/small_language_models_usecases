# SYSTEM INTEGRATION MAP: How Everything Connects
## Complete Data Flow and Dependencies

---

## 🔑 The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        3 PHASES SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 0: ANALYSIS (One-time)                                  │
│  ════════════════════════════════════════════════════════      │
│  Raw Benchmarks → [SDDF Framework] → AnalysisResult JSON       │
│                                                                 │
│  PHASE 1: PRODUCTION (Per-request)                             │
│  ════════════════════════════════════════════════════════      │
│  Input → [ProductionRouter] → (Model, Decision)                │
│                                                                 │
│  PHASE 2: MONITORING (Daily)                                   │
│  ════════════════════════════════════════════════════════      │
│  Logs → [ProductionRouter] → Alerts                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  examples/example_code_generation.py                          │
│  (Demonstrates how to use the system)                        │
│                                                               │
└────────────────────┬─────────────────────────────────────────┘
                     │ imports
                     ↓
┌──────────────────────────────────────────────────────────────┐
│                   PRODUCTION LAYER                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ProductionRouter (src/routing/production_router.py)         │
│  ├─ Phase 0: add_analysis_result()                           │
│  ├─ Phase 1: route() ← MAIN METHOD                           │
│  └─ Phase 2: daily_monitoring_check()                        │
│                                                               │
│  Uses: AnalysisResult (data class)                           │
│                                                               │
└────────────┬──────────────────────────────┬──────────────────┘
             │                              │
             │ uses                         │ uses
             ↓                              ↓
  ┌────────────────────────┐  ┌──────────────────────────┐
  │ GeneralizedRouting     │  │ FailureTaxonomy         │
  │ Framework              │  │ (optional)               │
  │ (framework.py)         │  └──────────────────────────┘
  │                        │
  │ Methods:               │
  │ ├─ bin_by_difficulty()│
  │ ├─ compute_capability_│
  │ │  curve()            │
  │ ├─ compute_risk_curve│
  │ ├─ detect_tipping_  │
  │ │  points()          │
  │ ├─ classify_quadrant│
  │ └─ analyze_task()   │
  └────────┬──────────────┘
           │ uses
           ↓
  ┌────────────────────────┐
  │ Utils                  │
  ├────────────────────────┤
  │ stats.py:              │
  │ ├─ wilson_interval()  │
  └────────────────────────┘
```

---

## 🔄 PHASE 0: ANALYSIS PIPELINE

### Complete Data Flow

```
STEP 1-2: DATA INGESTION & NORMALIZATION
═══════════════════════════════════════════════════════════
Raw Benchmark Outputs
│ (outputs.jsonl for each task/model)
├─ code_generation/qwen/outputs.jsonl
├─ classification/phi3/outputs.jsonl
├─ summarization/llama/outputs.jsonl
└─ ... (8 tasks × N models)
│
└─→ framework/sddf/ingest.py
    ├─ Load raw outputs
    ├─ Normalize to standard format
    └─ Compute primary_metric per task
        │
        └─→ Output: [normalized_sample, ...]
            ├─ raw_input: str
            ├─ raw_output: str
            ├─ primary_metric: float [0,1]
            ├─ bin: int (from raw data or computed)
            ├─ task: str
            └─ model: str


STEP 3: DIFFICULTY SCORING
═══════════════════════════════════════════════════════════
[normalized_sample, ...]
│
└─→ GeneralizedRoutingFramework.bin_by_difficulty()
    │ (calls framework/sddf/difficulty.py)
    │
    ├─ For each sample:
    │  └─ extract raw_input
    │
    ├─ Call difficulty_metric(raw_input)
    │  └─ Task-specific computation:
    │     ├─ Code: analyze keywords + syntax complexity
    │     ├─ Text: length / max_length
    │     ├─ Classification: ambiguity score
    │     └─ Summarization: document length
    │
    └─→ Output: difficulty_score ∈ [0.0, 1.0]


STEP 4: BIN ASSIGNMENT
═══════════════════════════════════════════════════════════
[sample with difficulty_score, ...]
│
└─→ GeneralizedRoutingFramework.difficulty_to_bin_probabilities()
    │ (Soft probabilistic assignment)
    │
    ├─ bin_position = difficulty × (num_bins - 1)
    ├─ lower_bin = int(bin_position)
    ├─ fraction = bin_position - lower_bin
    │
    └─→ Output: bin_probs = {0: p0, 1: p1, 2: p2, 3: p3, 4: p4}
        (probabilities sum to 1.0)
│
└─→ GeneralizedRoutingFramework.bin_by_difficulty()
    │ (Deterministic assignment via argmax)
    │
    ├─ bin_id = argmax(bin_probs)
    │
    └─→ Output: binned = {0: [samples], 1: [samples], ...}


STEP 5: CAPABILITY CURVE COMPUTATION
═══════════════════════════════════════════════════════════
binned = {0: [samples], 1: [samples], ..., 4: [samples]}
│
└─→ GeneralizedRoutingFramework.compute_capability_curve()
    │ (Called from analyze_task)
    │
    ├─ For each bin:
    │  │
    │  ├─ Call validation_fn(sample['raw_output'])
    │  │  └─ Returns: True (valid) or False (invalid)
    │  │
    │  ├─ Count valid outputs
    │  │
    │  └─ capability[bin] = valid_count / total
    │
    └─→ Output: capability_curve = {
            0: 0.90,  ← 90% of easy samples are valid
            1: 0.85,  ← 85% of medium samples are valid
            2: 0.80,  ← etc.
            3: 0.75,
            4: 0.70
        }

    📌 ISSUE #3: This measures VALIDITY (structural)
       not QUALITY (functional)


STEP 6: RISK CURVE COMPUTATION
═══════════════════════════════════════════════════════════
binned = {0: [samples], 1: [samples], ..., 4: [samples]}
│
└─→ GeneralizedRoutingFramework.compute_risk_curve()
    │ (Called from analyze_task)
    │
    ├─ For each bin:
    │  │
    │  ├─ IF quality_metric provided:
    │  │  │
    │  │  ├─ Call quality_metric(sample)
    │  │  │  └─ Returns: float [0.0, 1.0] (continuous quality score)
    │  │  │     • Code: tests_passed / total_tests
    │  │  │     • Text: constraint_satisfaction_rate
    │  │  │     • Classification: float(prediction == reference)
    │  │  │     • Summarization: rouge_1_f1
    │  │  │
    │  │  ├─ Compare to quality_threshold (0.80 or 1.0)
    │  │  │
    │  │  └─ if quality_score < threshold:
    │  │     └─ failure_count += 1
    │  │
    │  ├─ ELSE (fallback, if quality_metric is None):
    │  │  │
    │  │  ├─ Use severity-weighted failures
    │  │  │  └─ weight = SEVERITY_WEIGHTS[sample['severity']]
    │  │  │
    │  │  └─ total_weight += weight
    │  │
    │  └─ risk[bin] = failure_count / total (or total_weight / total)
    │
    └─→ Output: risk_curve = {
            0: 0.10,  ← 10% of easy samples below quality bar
            1: 0.15,  ← 15% of medium samples below quality bar
            2: 0.20,  ← etc.
            3: 0.25,
            4: 0.30
        }

    📌 ISSUE #1: This measures QUALITY (functional)
       NOT the complement of VALIDITY
       So: capability + risk ≠ 1.0


STEP 7: EXPECTED CURVES (Soft Interpolation)
═══════════════════════════════════════════════════════════
capability_curve = {0: ..., 1: ..., ..., 4: ...}
risk_curve = {0: ..., 1: ..., ..., 4: ...}
│
└─→ GeneralizedRoutingFramework.compute_expected_capability()
    │ (For reporting/analysis)
    │
    ├─ For each bin_id:
    │  │
    │  ├─ difficulty_mid = bin_id / (num_bins - 1)
    │  │
    │  ├─ bin_probs = difficulty_to_bin_probabilities(difficulty_mid)
    │  │  └─ Soft assignment near boundaries
    │  │
    │  └─ expected_capability[bin] = Σ bin_probs[i] × capability[i]
    │     └─ Weighted average of adjacent bins
    │
    └─→ Output: expected_capability = {interpolated values}

(Same for expected_risk)


STEP 8: TIPPING POINT DETECTION
═══════════════════════════════════════════════════════════
capability_curve = {...}
risk_curve = {...}
capability_counts = {...}  ← Sample counts per bin
risk_counts = {...}
│
└─→ GeneralizedRoutingFramework.detect_tipping_points()
    │ (Called from analyze_task)
    │
    ├─ For τ_cap (CAPABILITY TIPPING POINT):
    │  │
    │  ├─ τ_cap = max{d : P̂_m(d) ≥ 0.80}
    │  │  └─ Last bin where capability >= 80%
    │  │
    │  ├─ Loop through bins and update tau_cap
    │  │  │
    │  │  ├─ Compute Wilson CI lower bound
    │  │  │  └─ Uses wilson_interval(capability, count)
    │  │  │
    │  │  └─ If lower ≥ 0.80: tau_cap = current_bin
    │  │
    │  └─ Result: tau_cap = 2 (capable through bin 2)
    │
    ├─ For τ_risk (RISK TIPPING POINT):
    │  │
    │  ├─ τ_risk = min{d : Risk_m(d) > 0.20}
    │  │  └─ First bin where risk > 20%
    │  │
    │  ├─ Loop through bins, STOP at first match
    │  │  │
    │  │  ├─ Compute Wilson CI lower bound
    │  │  │  └─ Uses wilson_interval(risk, count)
    │  │  │
    │  │  └─ If lower ≥ 0.20: tau_risk = current_bin, BREAK
    │  │
    │  └─ Result: tau_risk = 0 (risky from bin 0)
    │
    └─→ Output: (tau_cap, tau_risk)

    📌 ISSUE 1.2: Uses CI instead of raw values
       τ_risk logic differs from documentation


STEP 9: ZONE CLASSIFICATION
═══════════════════════════════════════════════════════════
tau_cap = 2
tau_risk = 0
capability_curve = {...}
risk_curve = {...}
│
└─→ GeneralizedRoutingFramework.classify_quadrant()
    │ (Called from analyze_task)
    │
    ├─ Classify entire task/model pair into Q1/Q2/Q3/Q4
    │
    ├─ Based on: tau_cap vs 4, tau_risk vs 4
    │  │
    │  ├─ If tau_cap == 4 AND tau_risk == None:
    │  │  └─ Q1 (capable everywhere, safe everywhere)
    │  │
    │  ├─ If tau_cap == 4 AND tau_risk < 4:
    │  │  └─ Q2 (capable everywhere, but risky somewhere)
    │  │
    │  ├─ If tau_cap < 4 AND tau_risk > tau_cap:
    │  │  └─ Q3 (capable up to tau_cap, then weak)
    │  │
    │  └─ If tau_cap < 4 AND tau_risk <= tau_cap:
    │     └─ Q4 (both fail early)
    │
    └─→ Output: zone = "Q4"


STEP 10: ZONE-SPECIFIC POLICIES
═══════════════════════════════════════════════════════════
zone = "Q4"
tau_cap = 2
tau_risk = 0
│
└─→ Routing policy defined in ROUTING_POLICIES.md:
    │
    ├─ Q1: USE SLM (always safe)
    ├─ Q2: SLM + VERIFY + ESCALATE ← MISSING IN CODE
    ├─ Q3: HYBRID (SLM for easy, LLM for hard)
    └─ Q4: USE LLM (always)
    │
    └─→ Output: routing_policy = "LLM only"


FINAL OUTPUT: AnalysisResult
═══════════════════════════════════════════════════════════
{
    "task": "code_generation",
    "model": "qwen",
    "capability_curve": {0: 0.67, 1: 0.80, 2: 0.80, 3: 0.67, 4: 0.73},
    "risk_curve": {0: 0.33, 1: 0.20, 2: 0.20, 3: 0.33, 4: 0.27},
    "expected_capability": {...},     ← Interpolated
    "expected_risk": {...},           ← Interpolated
    "tau_cap": 2,
    "tau_risk": 0,
    "zone": "Q4",
    "empirical_tau_c": 0.80,
    "empirical_tau_r": 0.20,
    "failure_analysis": {...},        ← From FailureTaxonomy
    "weighted_risks": {...}           ← From FailureTaxonomy
}

└─→ Saved as: analysis_results.json
    (Loaded by ProductionRouter for Phase 1)
```

---

## 🚀 PHASE 1: PRODUCTION ROUTING

### Per-Request Flow

```
INPUT
═════════════════════════════════════════════════════════════
user_input = "Write a function to reverse a list"
task = "code_generation"
preferred_model = "qwen"
│
└─→ ProductionRouter.route(input_text, task, difficulty_metric, preferred_model)
    │ (Production Router in production_router.py)
    │
    │
    ├─ STEP 12: COMPUTE DIFFICULTY
    │  │
    │  ├─ Call difficulty_metric(input_text)
    │  │  └─ Task-specific difficulty function
    │  │     ├─ Code: len(input) / 1000 (example)
    │  │     ├─ Text: len(input) / max_length
    │  │     └─ etc.
    │  │
    │  └─ difficulty = 0.2 (easy problem)
    │
    │
    ├─ STEP 13: GET ANALYSIS & BIN
    │  │
    │  ├─ analysis = self.get_analysis(task, preferred_model)
    │  │  └─ Look up pre-computed AnalysisResult
    │  │     (loaded during __init__)
    │  │
    │  ├─ num_bins = analysis.num_bins
    │  │
    │  └─ bin_id = int(difficulty × (num_bins - 1))
    │     └─ bin_id = int(0.2 × 4) = 0
    │
    │
    ├─ STEP 14: GET CURVES FOR BIN
    │  │
    │  ├─ Call self._expected_metric(difficulty, capability_curve, num_bins)
    │  │  └─ GeneralizedRoutingFramework._expected_metric()
    │  │
    │  ├─ Interpolate between adjacent bins:
    │  │  │
    │  │  ├─ bin_position = 0.2 × 4 = 0.8
    │  │  ├─ lower_bin = 0, upper_bin = 1
    │  │  ├─ fraction = 0.8
    │  │  │
    │  │  └─ capability = (1-0.8)×cap[0] + 0.8×cap[1]
    │  │     = 0.2×0.67 + 0.8×0.80
    │  │     = 0.134 + 0.640 = 0.774
    │  │
    │  └─ Same for risk
    │     risk = 0.2×0.33 + 0.8×0.20 = 0.226
    │
    │
    ├─ STEP 15: CLASSIFY ZONE
    │  │
    │  ├─ tau_c = analysis.empirical_tau_c = 0.80
    │  ├─ tau_r = analysis.empirical_tau_r = 0.20
    │  │
    │  └─ Call self._classify_zone(capability, risk, tau_c, tau_r)
    │     │
    │     └─ if capability ≥ 0.80 and risk ≤ 0.20:
    │        └─ return "Q1"
    │
    │        elif capability ≥ 0.80 and risk > 0.20:
    │        └─ return "Q2"
    │
    │        elif capability < 0.80 and risk ≤ 0.20:
    │        └─ return "Q3"
    │
    │        else:
    │        └─ return "Q4"
    │
    │  With our values:
    │  ├─ 0.774 ≥ 0.80? NO
    │  └─ 0.226 ≤ 0.20? NO
    │  └─ → zone = "Q4"
    │
    │
    ├─ STEP 16: APPLY ZONE POLICY ⚠️ ISSUE #2 HERE
    │  │
    │  ├─ Call self._apply_zone_policy(zone, model, bin_id, tau_cap, ...)
    │  │  │
    │  │  ├─ if zone == "Q1":
    │  │  │  └─ return model  ← Use SLM directly
    │  │  │
    │  │  ├─ elif zone == "Q2":
    │  │  │  └─ return "SLM_with_verification"  ⚠️ BUG: Just a string!
    │  │  │
    │  │  ├─ elif zone == "Q3":
    │  │  │  │
    │  │  │  ├─ if bin_id <= tau_cap:
    │  │  │  │  └─ return model  ← Use SLM on easy
    │  │  │  └─ else:
    │  │  │     └─ return "llama"  ← Use LLM on hard
    │  │  │
    │  │  └─ else (zone == "Q4"):
    │  │     └─ return "llama"  ← Use LLM
    │  │
    │  └─ In our case: zone = "Q4"
    │     └─ routed_model = "llama"
    │
    │
    ├─ STEP 16b: VERIFICATION (Q2 only) ⚠️ OPTIONAL
    │  │
    │  └─ if zone == "Q2" and self.verification_fn:
    │     │
    │     ├─ Call verification_fn(...)
    │     │  └─ User-provided verification function
    │     │     • Checks confidence of output
    │     │     • Returns: bool (verified or not)
    │     │
    │     └─ If not verified:
    │        └─ routed_model = "llama"  ← Escalate
    │
    │  Note: If verification_fn is None, Q2 breaks!
    │
    │
    ├─ STEP 17: COMPUTE EXPECTED SUCCESS RATE
    │  │
    │  └─ if routed_model == preferred_model:
    │     └─ expected_success = max(0.0, capability × (1 - risk))
    │     └─ = 0.774 × (1 - 0.226) = 0.774 × 0.774 = 0.599
    │  else:
    │     └─ expected_success = 0.95  ← LLM baseline
    │
    │
    └─ CREATE DECISION RECORD & RETURN
       │
       └─ decision = RoutingDecisionRecord(
           timestamp=now(),
           task="code_generation",
           input_text="Write a function...",
           difficulty=0.2,
           bin_id=0,
           capability=0.774,
           risk=0.226,
           zone="Q4",
           routed_model="llama",
           expected_success_rate=0.95,
           verification_status="not_applicable"
       )
       │
       └─ return ("llama", decision)


OUTPUT
═════════════════════════════════════════════════════════════
model = "llama"  ← Selected model to use
decision = RoutingDecisionRecord(...)  ← Logged for monitoring
```

---

## 📊 PHASE 2: MONITORING

### Daily Degradation Detection

```
INPUT: Yesterday's Routing Logs
═════════════════════════════════════════════════════════════
self.routing_logs = [
    RoutingDecisionRecord(task="code_gen", zone="Q4", bin_id=0, capability=0.774, risk=0.226, ...),
    RoutingDecisionRecord(task="code_gen", zone="Q3", bin_id=2, capability=0.800, risk=0.150, ...),
    ... (100+ decisions from yesterday)
]
│
│
└─→ ProductionRouter.daily_monitoring_check()
    │
    │
    ├─ For each (task, model) pair:
    │  │
    │  ├─ COLLECT YESTERDAY'S DATA
    │  │  │
    │  │  └─ yesterday_logs = [
    │  │     logs where timestamp.date() == yesterday
    │  │     ]
    │  │
    │  │
    │  ├─ COMPUTE STATISTICS PER BIN
    │  │  │
    │  │  ├─ For bin_id in [0, 1, 2, 3, 4]:
    │  │  │  │
    │  │  │  ├─ bin_logs = [logs where bin_id == this_bin]
    │  │  │  │
    │  │  │  ├─ cap_mean = mean([log.capability for log in bin_logs])
    │  │  │  ├─ cap_count = len(bin_logs)
    │  │  │  │
    │  │  │  ├─ risk_mean = mean([log.risk for log in bin_logs])
    │  │  │  └─ risk_count = len(bin_logs)
    │  │  │
    │  │  └─ cap_stats = {bin: (mean, count), ...}
    │  │     risk_stats = {bin: (mean, count), ...}
    │  │
    │  │
    │  ├─ DETECT NEW TIPPING POINTS
    │  │  │
    │  │  ├─ new_tau_cap = self._detect_tau_cap(cap_stats, ...)
    │  │  │  │
    │  │  │  └─ Loop through bins:
    │  │  │     ├─ If count < min_samples (5): skip
    │  │  │     ├─ Compute wilson_interval(mean, count)
    │  │  │     └─ If lower ≥ threshold: tau_cap = bin
    │  │  │
    │  │  └─ new_tau_risk = self._detect_tau_risk(risk_stats, ...)
    │  │     └─ Similar process
    │  │
    │  │
    │  ├─ COMPARE TO BASELINE
    │  │  │
    │  │  ├─ old_tau_cap = analysis.tau_cap  ← From Phase 0
    │  │  ├─ old_tau_risk = analysis.tau_risk
    │  │  │
    │  │  ├─ if (old_tau_cap - new_tau_cap) >= alert_delta_tau:
    │  │  │  └─ alerts.append("ALERT: Capability degraded")
    │  │  │
    │  │  └─ if (old_tau_risk - new_tau_risk) >= alert_delta_tau:
    │  │     └─ alerts.append("ALERT: Risk escalated")
    │  │
    │  │
    │  └─ CHECK BIN-WISE RISKS
    │     │
    │     ├─ For each bin:
    │     │  │
    │     │  ├─ base_risk = analysis.risk_curve[bin]  ← From Phase 0
    │     │  ├─ new_risk = risk_stats[bin][0]  ← From yesterday
    │     │  │
    │     │  └─ if (new_risk - base_risk) > alert_delta_risk:
    │     │     └─ alerts.append(f"ALERT: Risk increased in bin {bin}")
    │     │
    │     └─ Result: [alert1, alert2, ...]
    │
    │
    └─→ OUTPUT: alerts = [
            "ALERT: code_generation/qwen capability degraded: tau_cap 2 -> 1",
            "ALERT: code_generation/qwen risk increased in bin 0: 0.33 -> 0.45"
        ]
```

---

## 🔗 Module Import Chain

### How Everything Imports

```
examples/example_code_generation.py
│
└─ from src.routing import ProductionRouter, AnalysisResult
   │
   └─ src/routing/__init__.py
      │
      ├─ from .production_router import ProductionRouter, AnalysisResult
      │  │
      │  └─ src/routing/production_router.py
      │     │
      │     ├─ import src.utils.stats (for wilson_interval)
      │     │  │
      │     │  └─ src/utils/stats.py
      │     │     └─ def wilson_interval(p, n, z) → Tuple
      │     │
      │     └─ class ProductionRouter:
      │        │
      │        ├─ Uses: GeneralizedRoutingFramework (internally)
      │        └─ Uses: AnalysisResult (data storage)
      │
      └─ from .framework import GeneralizedRoutingFramework, TaskSpec
         │
         └─ src/routing/framework.py
            │
            ├─ import src.utils.stats (for wilson_interval)
            │
            ├─ Optional: from src.routing.failure_taxonomy import FailureTaxonomy
            │
            └─ class GeneralizedRoutingFramework:
               │
               ├─ Methods use: TaskSpec
               └─ Methods may use: FailureTaxonomy
```

---

## 📈 Data Object Relationships

### Class Diagram

```
┌──────────────────────────────┐
│    AnalysisResult            │
│ (src/routing/production_     │
│  router.py)                  │
├──────────────────────────────┤
│ - task: str                  │
│ - model: str                 │
│ - capability_curve: Dict     │──┐
│ - risk_curve: Dict           │  │ Curves used in
│ - tau_cap: int               │  │ Phase 1 routing
│ - tau_risk: int              │  │
│ - zone: str (Q1/Q2/Q3/Q4)   │  │
│ - empirical_tau_c: float     │  │
│ - empirical_tau_r: float     │  │
│ - num_bins: int              │  │
│ - failure_analysis: Dict     │  │ From FailureTaxonomy
│ - weighted_risks: Dict       │  │
└──────────────────────────────┘  │
                                   │
                                   │
┌──────────────────────────────┐   │
│  ProductionRouter            │   │
│ (src/routing/production_     │   │
│  router.py)                  │   │
├──────────────────────────────┤   │
│ - analyses: Dict[tuple,      │◄──┘
│     AnalysisResult]          │
│ - routing_logs: List[        │
│     RoutingDecisionRecord]   │
├──────────────────────────────┤
│ + route(input, task, ...) →  │
│   (model, RoutingDecision)   │
│ + daily_monitoring_check() → │
│   List[alerts]               │
└──────────────────────────────┘
           │
           │ creates
           ↓
┌──────────────────────────────┐
│  RoutingDecisionRecord       │
│ (src/routing/production_     │
│  router.py)                  │
├──────────────────────────────┤
│ - timestamp: str             │
│ - task: str                  │
│ - difficulty: float          │
│ - bin_id: int                │
│ - capability: float          │
│ - risk: float                │
│ - zone: str (Q1/Q2/Q3/Q4)   │
│ - routed_model: str          │
│ - expected_success_rate: flt │
│ - verification_status: str   │
└──────────────────────────────┘


┌──────────────────────────────┐
│  TaskSpec                    │
│ (src/routing/framework.py)   │
├──────────────────────────────┤
│ - name: str                  │
│ - validation_fn: Callable    │──────┐ Validates structural
│ - difficulty_metric: Callable│──┐   │ validity
│ - quality_metric: Callable   │──┼───┤ Computes quality score
│ - quality_threshold: float   │  │   │
│ - num_bins: int              │  │   │
└──────────────────────────────┘  │   │
                                   │   │
        ┌──────────────────────────┘   │
        │                              │
        ↓                              ↓
┌──────────────────────────────┐
│  FailureTaxonomy             │
│ (src/routing/failure_        │
│  taxonomy.py)                │
├──────────────────────────────┤
│ - STRUCTURAL_SEVERITY: Dict  │
│ - SEMANTIC_SEVERITY: Dict    │
│ - SEVERITY_WEIGHTS: Dict     │
├──────────────────────────────┤
│ + analyze_failures_by_bin()  │
│ + compute_weighted_risk...() │
└──────────────────────────────┘
```

---

## 🌳 Dependency Tree (What Depends on What)

```
examples/example_code_generation.py
│
├─→ ProductionRouter
│   ├─→ AnalysisResult (data storage)
│   ├─→ RoutingDecisionRecord (data storage)
│   ├─→ wilson_interval() from stats.py
│   │
│   └─→ INTERNALLY USES:
│       ├─→ _classify_zone() (method)
│       ├─→ _apply_zone_policy() (method) ⚠️ ISSUE #2
│       ├─→ _expected_metric() (method)
│       │   └─→ Uses interpolation logic
│       │
│       └─→ Can call:
│           └─→ GeneralizedRoutingFramework
│               ├─→ difficulty_to_bin_probabilities() (method)
│               ├─→ compute_capability_curve() (method) ⚠️ ISSUE #3
│               ├─→ compute_risk_curve() (method) ⚠️ ISSUE #1
│               ├─→ compute_expected_capability() (method)
│               ├─→ compute_expected_risk() (method)
│               ├─→ detect_tipping_points() (method) ⚠️ ISSUE 1.2
│               │   └─→ wilson_interval() from stats.py
│               │
│               ├─→ classify_quadrant() (method)
│               │
│               └─→ May use:
│                   └─→ FailureTaxonomy
│                       ├─→ analyze_failures_by_bin() (method)
│                       └─→ compute_weighted_risk_by_bin() (method)
│
└─→ framework/sddf/ (SDDF analysis pipeline)
    ├─→ ingest.py (load raw data)
    ├─→ difficulty.py (compute difficulty)
    ├─→ gates.py (quality thresholds)
    ├─→ curves.py (capability/risk curves)
    ├─→ tipping.py (tipping points)
    ├─→ zones.py (zone classification)
    ├─→ routing.py (production routing)
    ├─→ uncertainty.py (confidence intervals)
    ├─→ validator.py (consistency checks)
    ├─→ reporting.py (generate reports)
    ├─→ plots.py (visualizations)
    └─→ ... (and others)
```

---

## 🎯 Key Connection Points

### 1. **Phase 0 → Phase 1 Connection**

```
Phase 0 Output (JSON):
{
  "analyses": [
    {
      "task": "code_generation",
      "model": "qwen",
      "capability_curve": {...},
      "risk_curve": {...},
      "tau_cap": 2,
      "tau_risk": 0,
      "zone": "Q4",
      ...
    }
  ]
}

│ Loaded by

ProductionRouter.load_from_analysis(filepath)
│
└─→ For each analysis in JSON:
    └─→ Create AnalysisResult object
        └─→ Store in self.analyses[(task, model)]

│ Used by

ProductionRouter.route(input_text, task, difficulty_metric)
│
└─→ Get analysis from self.analyses[(task, preferred_model)]
    └─→ Use curves for interpolation
    └─→ Use tau_cap, tau_risk for hybrid routing
    └─→ Use empirical_tau_c, empirical_tau_r for zone classification
```

### 2. **Difficulty Metric Coupling**

```
Phase 0: Difficulty computation
├─ difficulty_metric = lambda text: compute_task_difficulty(text)
└─ Applied in: GeneralizedRoutingFramework.bin_by_difficulty()

Phase 1: Same difficulty computation
├─ difficulty_metric = lambda text: compute_task_difficulty(text)
└─ Applied in: ProductionRouter.route()

CRITICAL: Must use the SAME difficulty_metric in both phases!
Otherwise bins don't align and routing is wrong.
```

### 3. **Quality Metric Coupling**

```
Phase 0: Quality metric defined per task
├─ quality_metric = lambda sample: extract_quality(sample)
├─ quality_threshold = 0.80 or 1.0
└─ Applied in: GeneralizedRoutingFramework.compute_risk_curve()

Phase 1: Quality metric is FROZEN in AnalysisResult
├─ risk_curve is pre-computed
└─ Applied in: ProductionRouter.route() (no new quality computation)

IMPORTANT: Quality is computed once in Phase 0, then reused in Phase 1.
Phase 1 doesn't call quality_metric again.
```

### 4. **Verification Function (Q2 Routing)**

```
⚠️ ISSUE #2: Broken Connection

Expected:
ProductionRouter.__init__(verification_fn=my_verify_fn)
│
└─→ ProductionRouter.route()
    └─→ If zone == "Q2":
        └─→ Call verification_fn()
            ├─ If passes: return SLM output
            └─ If fails: escalate to LLM

Actual:
ProductionRouter.__init__(verification_fn=my_verify_fn)  ← OPTIONAL
│
└─→ ProductionRouter.route()
    └─→ If zone == "Q2":
        └─→ _apply_zone_policy() returns "SLM_with_verification"
            └─→ Later: if verification_fn is NOT None:
                └─→ Check verification
                    ├─ If passes: routed_model = "qwen"
                    └─ If fails: routed_model = "llama"
                ELSE:
                └─→ routed_model stays "SLM_with_verification" ✗
```

---

## 📍 Where the Issues Manifest

### ISSUE #1: Capability ≠ (1 - Risk)

```
Manifests in multiple places:

1. Framework level (where computed):
   └─ src/routing/framework.py:191-275
      ├─ compute_capability_curve() ← Measures validity
      └─ compute_risk_curve() ← Measures quality
      └─ No relationship between them

2. Zone classification:
   └─ src/routing/framework.py:387-408
      └─ classify_quadrant() assumes they're related
         but they're actually independent

3. Production routing:
   └─ src/routing/production_router.py:225
      └─ _classify_zone() uses both independently
         as if they were complementary

4. Interpolation:
   └─ src/routing/production_router.py:274-285
      └─ _expected_metric() interpolates independently
         ignoring the assumption they should sum to 1
```

### ISSUE #2: Zone Q2 Missing

```
Manifests in:

1. Policy definition:
   └─ src/routing/production_router.py:312-314
      └─ elif zone == "Q2":
         └─ return "SLM_with_verification"  ← String, not model!

2. Verification logic:
   └─ src/routing/production_router.py:237-247
      └─ if zone == "Q2" and self.verification_fn:  ← Optional!
         └─ Can be skipped if verification_fn is None

3. Return value:
   └─ return routed_model
      └─ Can be "SLM_with_verification" (invalid string)
         OR "qwen"/"llama" (valid model)
         OR undefined if verification_fn not provided

4. Expected vs actual:
   └─ Theory (COMPLETE_PIPELINE.md): Full escalation logic
   └─ Code (production_router.py): Fragmented, optional logic
```

### ISSUE #3: Capability vs Validity

```
Manifests in:

1. Method naming:
   └─ src/routing/framework.py:191
      └─ def compute_capability_curve()
         └─ But it measures validity, not capability

2. Quality metric is separate:
   └─ src/routing/framework.py:221
      └─ def compute_risk_curve()
         └─ Uses quality_metric, not validity

3. Zone logic assumes connection:
   └─ src/routing/framework.py:387-408
      └─ Treats capability and risk as if they measure
         the same sample outcome, but they don't

4. Interpretation confusion:
   └─ Zone Q2: "High capability, high risk"
      └─ But really: "High validity, low quality"
      └─ Different concepts mixed together
```

### ISSUE #4: Risk Computation Variance

```
Manifests in:

1. Three methods in one function:
   └─ src/routing/framework.py:244-269
      ├─ Method 1: Quality threshold based (NEW)
      ├─ Method 2: Severity weighted (OLD)
      └─ Choice depends on whether quality_metric provided

2. Different semantics across tasks:
   └─ docs/reference/QUALITY_METRICS.md
      ├─ Code gen: Binary test pass/fail
      ├─ Text gen: Constraint satisfaction < 0.80
      ├─ Classification: Wrong prediction
      └─ All called "risk" but different meanings

3. Non-comparable risk values:
   └─ Risk = 0.25 in code gen (25% tests fail)
   └─ Risk = 0.25 in text gen (25% below quality bar)
      └─ Same number, different severity
      └─ Monitoring alerts treat them equally ✗

4. Threshold inconsistency:
   └─ framework/sddf/gates.py
      └─ Different quality_threshold per task
         ├─ Binary tasks: 1.0 (must pass all)
         └─ Continuous tasks: 0.80 (80% quality)
```

---

## 🔄 Synchronization Points

### What Must Stay In Sync

```
Between Phase 0 and Phase 1:
═════════════════════════════════════════════════════════════

1. Difficulty Metric
   Phase 0: GeneralizedRoutingFramework.bin_by_difficulty()
   Phase 1: ProductionRouter.route()
   MUST USE: Same function!

2. Quality Threshold
   Phase 0: compute_risk_curve(quality_threshold=...)
   Phase 1: (Frozen in AnalysisResult)
   MUST MATCH: Same value!

3. Bin Count
   Phase 0: num_bins = 5 (default)
   Phase 1: Retrieved from AnalysisResult.num_bins
   MUST MATCH: Same value!

4. Empirical Thresholds
   Phase 0: τ_C = 0.80, τ_R = 0.20
   Phase 1: Retrieved from AnalysisResult.empirical_tau_c, empirical_tau_r
   MUST MATCH: Same values!

5. Model Name
   Phase 0: "qwen", "llama", etc.
   Phase 1: preferred_model parameter
   MUST MATCH: Same name!

If ANY of these diverge, routing breaks silently!
```

---

## 🧩 Complete Integration Checklist

```
✓ Phase 0: Analysis Pipeline
  ├─ ✓ Load raw outputs
  ├─ ✓ Normalize to standard format
  ├─ ✓ Compute difficulty scores
  ├─ ✓ Bin samples into 5 bins
  ├─ ✓ Compute capability curves (ISSUE #3: validates, not quality)
  ├─ ✓ Compute risk curves (ISSUE #1: independent from capability)
  ├─ ✓ Detect tipping points (ISSUE 1.2: uses CI, not raw values)
  ├─ ✓ Classify zones
  └─ ✓ Save AnalysisResult as JSON

✓ Phase 1: Production Routing
  ├─ ✓ Load AnalysisResult from JSON
  ├─ ✓ Receive input request
  ├─ ✓ Compute difficulty
  ├─ ✓ Assign to bin
  ├─ ✓ Get curves from AnalysisResult
  ├─ ✓ Interpolate expected capability/risk
  ├─ ✓ Classify zone
  ├─ ⚠️ Apply zone policy (ISSUE #2: Q2 broken, returns string)
  ├─ ⚠️ Verify output (Q2 only, optional, fragmented logic)
  └─ ✓ Return model + decision

✓ Phase 2: Monitoring
  ├─ ✓ Collect routing logs
  ├─ ✓ Compute statistics per bin
  ├─ ✓ Redetect tipping points
  ├─ ✓ Compare to baseline
  ├─ ⚠️ Generate alerts (inconsistent thresholds, ISSUE #4)
  └─ ✓ Report degradation
```

---

**Now you see how everything connects!**

Key insights:
1. Phase 0 → Phase 1: Frozen policies transferred via JSON
2. Phase 1 → Phase 2: Decisions logged, compared to baseline
3. All phases must use same difficulty metric or routing breaks
4. Issues are at connection points between phases
5. ISSUE #2 is an internal break (Q2 policy not implemented)
6. ISSUES #1,#3,#4 are cross-phase inconsistencies
