# Complete Codebase Structure Map
## What Each Folder and File Does

**Purpose**: Understand the architecture before fixing the issues
**Last Updated**: 2026-03-24

---

## 📁 Directory Structure Overview

```
SLM use cases/
├── src/                          ← Core production code
├── framework/                    ← Analysis pipeline components
├── tasks/                        ← Task-specific implementations (8 tasks)
├── tests/                        ← Unit and integration tests
├── examples/                     ← Example usage and demonstrations
├── docs/                         ← Documentation
├── scripts/                      ← Utility scripts
├── data/                         ← Data directories
├── outputs/                      ← Analysis and benchmark outputs
└── archive/                      ← Old/deprecated code
```

---

## 🎯 CORE PRODUCTION CODE: `src/`

### `src/routing/` - Main Routing System

#### **production_router.py** (680 lines)
**Purpose**: Production-ready routing system (Phase 0 → 1 → 2)

**Key Classes**:
- `AnalysisResult`: Stores one-time analysis (capability curves, risk curves, tipping points)
- `RoutingDecisionRecord`: Records per-request routing decision
- `MonitoringMetric`: Stores daily monitoring results
- `ProductionRouter`: Main router class

**Key Methods**:
- `__init__()`: Initialize with verification function (optional)
- `add_analysis_result()`: Register Phase 0 analysis
- `load_from_analysis()`: Load frozen policies from JSON
- `route()`: **MAIN METHOD** - Route a single request (Phase 1)
  - Computes difficulty → bin → curves → zone → applies policy
- `daily_monitoring_check()`: Detect degradation (Phase 2)
- `_classify_zone()`: Classify into Q1/Q2/Q3/Q4 based on capability/risk
- `_apply_zone_policy()`: **PROBLEMATIC** - Returns routing decision
  - **ISSUE**: Zone Q2 returns `"SLM_with_verification"` string ← BUG HERE

**Code Locations**:
- Zone classification: lines 287-296
- Zone Q2 policy: lines 312-314 ← ISSUE #2 IS HERE
- Verification logic: lines 237-247

---

#### **framework.py** (670 lines)
**Purpose**: Generalized, task-agnostic analysis framework

**Key Classes**:
- `TaskSpec`: Task specification with validation and difficulty metrics
- `RoutingDecision`: Routing decision per model
- `GeneralizedRoutingFramework`: Main analysis engine

**Key Methods**:
- `difficulty_to_bin_probabilities()`: Convert difficulty to soft bin probabilities
- `bin_by_difficulty()`: Group samples into difficulty bins
- `compute_capability_curve()`: **PROBLEMATIC** - Computes validity curve
  - Uses `validation_fn()` (structural validity check)
  - **ISSUE**: Misnamed as "capability" but measures validity ← ISSUE #3
- `compute_risk_curve()`: Computes quality-based risk
  - Uses `quality_metric()` (functional quality check)
  - **ISSUE**: Different from capability (not complementary) ← ISSUE #1
- `compute_expected_capability()`: Interpolate capability using soft bins
- `compute_expected_risk()`: Interpolate risk using soft bins
- `detect_tipping_points()`: **PROBLEMATIC** - Detects τ_cap and τ_risk
  - Uses Wilson CI instead of raw values
  - **ISSUE**: τ_risk logic differs from documentation ← ISSUE 1.2
- `classify_quadrant()`: Classify into Q1/Q2/Q3/Q4
- `analyze_task()`: Run complete analysis for a task

**Code Locations**:
- Capability computation: lines 191-219 ← ISSUE #3
- Risk computation: lines 221-275 ← ISSUE #1, #4
- Tipping point detection: lines 337-385 ← ISSUE 1.2

---

#### **failure_taxonomy.py** (150 lines)
**Purpose**: Analyze failure types and severity

**Key Classes**:
- `FailureTaxonomy`: Categorize failures by type and severity

**Key Methods**:
- `analyze_failures_by_bin()`: Categorize failures per bin
- `compute_weighted_risk_by_bin()`: Weight failures by severity

**Severity Levels**:
- Critical (1.0): timeout, empty_output, syntax_error
- High (0.8): logic_error, execution_error, wrong_label
- Medium (0.5): incomplete_output, reasoning_error
- Low (0.2): too_short, formatting issues

---

#### `__init__.py`
**Purpose**: Export public API

**Exports**:
- `ProductionRouter`
- `GeneralizedRoutingFramework`
- `TaskSpec`
- `AnalysisResult`
- `RoutingDecisionRecord`
- `RoutingDecision`

---

### `src/utils/` - Utility Functions

#### **stats.py** (27 lines)
**Purpose**: Statistical utilities

**Key Functions**:
- `wilson_interval(p, n, z=1.96)`: Compute Wilson score confidence interval
  - Used for τ_cap and τ_risk detection with uncertainty quantification

#### **hardware_logger.py**
**Purpose**: Log hardware/environment information

---

### `src/benchmark_inference_pipeline.py`
**Purpose**: Run inference and collect benchmark results
**Status**: Legacy/supporting code

---

## 📊 ANALYSIS FRAMEWORK: `framework/`

### `framework/sddf/` - Scale-Difficulty-Driven Framework

**Purpose**: Core analysis pipeline (SDDF pattern)

#### Core Modules:

**`ingest.py`** - Data ingestion
- Load benchmark outputs
- Normalize to standard format
- Compute primary metrics per task

**`difficulty.py`** - Difficulty scoring
- Compute difficulty scores from raw inputs
- Task-specific difficulty metrics

**`gates.py`** - Quality metrics & thresholds
- Define quality thresholds per task
- Compute quality/validity metrics

**`curves.py`** - Capability and risk curves
- Compute C_m(b) capability curves
- Compute Risk_m(b) risk curves

**`tipping.py`** - Tipping point detection
- Detect τ_cap (capability tipping point)
- Detect τ_risk (risk tipping point)

**`zones.py`** - Zone classification
- Classify into Q1/Q2/Q3/Q4
- Implement zone-specific policies

**`routing.py`** - Production routing
- Route individual requests
- Apply zone policies

**`uncertainty.py`** - Confidence intervals
- Wilson score intervals
- Statistical gating

**`matching.py`** - Pair matching (for comparisons)

**`validator.py`** - Validate analysis consistency

**`pipeline.py`** - Orchestrate full analysis

**`reporting.py`** - Generate analysis reports

**`setup_reporting.py`** - Setup reporting infrastructure

**`plots.py`** - Generate visualizations

**`schema.py`** - Data schema definitions

---

### `framework/risk_sensitivity/` - Risk Sensitivity Analysis

**Purpose**: Analyze how zone assignments change with different thresholds

**Key Components**:

**`src/core/`**:
- `sddf_capability_analyzer.py`: Analyze capability curves
- `sddf_risk_analyzer.py`: Analyze risk curves
- `sddf_complexity_calculator.py`: Compute complexity metrics

**`src/analysis/`**:
- `component_learner.py`: Learn components from data
- `semantic_component_learner.py`: Semantic component analysis
- `failure_analyzer.py`: Analyze failure patterns
- `semantic_verifier.py`: Verify semantic correctness
- `threshold_learner.py`: Learn optimal thresholds

**`src/metrics/`**:
- `metric_calculators.py`: Calculate metrics
- `metric_aggregators.py`: Aggregate metrics

---

### `framework/benchmarking/` - Benchmarking Infrastructure

**Purpose**: Standard benchmarking interface

**Modules**:
- `interface.py`: Define benchmarking interface
- `standardize.py`: Standardize benchmark outputs

---

## 📚 TASKS: `tasks/`

**Purpose**: Task-specific implementations

### 8 Tasks Implemented:

1. **`tasks/code_generation/`** - Code generation task
2. **`tasks/classification/`** - Text classification
3. **`tasks/maths/`** - Mathematical problem solving
4. **`tasks/text_generation/`** - Free-form text generation
5. **`tasks/Summarization/`** - Text summarization
6. **`tasks/instruction_following/`** - Instruction following
7. **`tasks/Retrieval_grounded/`** - Retrieval-grounded QA
8. **`tasks/Information Extraction/`** - Information extraction

### Typical Task Structure:

```
task_name/
├── README.md           - Task description and results
├── src/               - Task-specific code
├── configs/           - Task configurations
├── benchmarks/        - Benchmark problems
├── runs/              - Run outputs and logs
├── results/           - Final results
└── data/              - Dataset information
```

---

## 🧪 TESTS: `tests/`

**Purpose**: Unit and integration testing

### Test Files:

**`conftest.py`** - Pytest configuration and fixtures

**`test_complete_pipeline_integration.py`** (250+ lines)
- Tests full Phase 0 → 1 → 2 pipeline
- Tests all 4 zones (Q1/Q2/Q3/Q4)
- **IMPORTANT**: These tests show expected behavior

**`test_execution.py`** - Execution flow tests

**`test_benchmark_*.py`** - Benchmark contract tests
- `test_benchmark_governance_contract.py`: Governance contracts
- `test_benchmark_inference_contract.py`: Inference contracts
- `test_benchmark_pipeline_contract.py`: Pipeline contracts
- `test_benchmark_structure.py`: Benchmark structure validation

**`test_sddf_*.py`** - SDDF framework tests
- `test_sddf_core.py`: Core SDDF tests
- `test_sddf_ingest_pipeline.py`: Data ingestion tests
- `test_sddf_reporting.py`: Reporting tests
- `test_sddf_setup_reporting.py`: Setup tests
- `test_sddf_validator.py`: Validation tests

---

## 📖 DOCUMENTATION: `docs/`

### `docs/guides/` - How-To Guides

**`README.md`** - Quick start guide

**`COMPLETE_PIPELINE.md`** (420 lines)
- **CRITICAL REFERENCE**: Documents all 3 phases
- Step-by-step walkthrough
- Expected vs actual implementations
- **NOTE**: Theory documented here conflicts with code

**`IMPLEMENTATION.md`** - Deployment and implementation guide

**`EXECUTION_WALKTHROUGH.md`** - Detailed execution walkthrough with examples

**`DECISION_TREE.md`** - Visual decision flowcharts

**`ROUTING_POLICIES.md`** (300+ lines)
- Zone 1 policy: Pure SLM
- Zone 2 policy: SLM + Verify + Escalate ← MISSING IN CODE
- Zone 3 policy: Hybrid (SLM for easy, LLM for hard)
- Zone 4 policy: Pure LLM

### `docs/architecture/` - System Design

**`SYSTEM_OVERVIEW.md`** - High-level system design
**`DELIVERY_CHECKLIST.md`** - Delivery checklist

### `docs/reference/` - Technical Reference

**`RISK_CURVES.md`** (400 lines)
- Visual guide to risk curves
- Mathematical foundations
- **ISSUE**: States `C = 1 - R` which conflicts with code

**`QUALITY_METRICS.md`** (460 lines)
- Per-task quality metrics and thresholds
- **ISSUE**: Documents 3 different risk computation methods

**`HYBRID_ROUTING.md`** - Hybrid routing guidance
**`RISK_CALCULATION.md`** - Risk calculation methods

### `docs/api/` - API Documentation

**`docs/templates/`** - Benchmark templates

---

## 🔧 SCRIPTS: `scripts/`

**Purpose**: Utility scripts for analysis and reporting

Typical scripts:
- Data preparation
- Benchmark running
- Result aggregation
- Report generation

---

## 📁 DATA: `data/`

### `data/benchmark/`
- Benchmark datasets and problems

### `data/results/`
- Computed results from analysis

---

## 📊 OUTPUTS: `outputs/`

### `outputs/analysis/`
- Analysis results and curves

### `outputs/benchmark/`
- Per-task, per-model benchmark outputs

### `outputs/plots/`
- Generated visualizations

### `outputs/results/`
- Final aggregated results

---

## 💡 EXAMPLES: `examples/`

### `example_code_generation.py` (85 lines)
**Purpose**: Complete working example

**Demonstrates**:
- Phase 0: Analysis (simulate with sample data)
- Phase 1: Production routing (route 3 test inputs)
- Phase 2: Monitoring (check for degradation)

**Shows**:
- How to create AnalysisResult
- How to call ProductionRouter.route()
- How to check routing_summary
- How to run daily_monitoring_check()

**IMPORTANT**: This example shows the EXPECTED behavior

---

## 🗃️ ARCHIVE: `archive/`

**Purpose**: Deprecated/old code

**Contains**: Previous implementations and abandoned approaches

---

## 🔗 Key Data Flow

### Phase 0 Analysis Flow:
```
Raw Outputs
    ↓
Ingest (ingest.py)
    ↓
Compute Difficulty (difficulty.py)
    ↓
Bin Samples (framework.py:bin_by_difficulty)
    ↓
Compute Capability Curve (curves.py / framework.py:compute_capability_curve)
    ↓
Compute Risk Curve (curves.py / framework.py:compute_risk_curve)
    ↓
Detect Tipping Points (tipping.py / framework.py:detect_tipping_points)
    ↓
Classify Zones (zones.py / framework.py:classify_quadrant)
    ↓
AnalysisResult (stored as JSON)
```

### Phase 1 Production Flow:
```
Input Request
    ↓
ProductionRouter.route()
    ├─ Compute Difficulty (difficulty.py)
    ├─ Assign to Bin
    ├─ Get Curves from AnalysisResult
    ├─ Compute Expected Capability/Risk (interpolate)
    ├─ Classify Zone (_classify_zone)
    ├─ Apply Zone Policy (_apply_zone_policy) ← ISSUE #2 HERE
    └─ Return (model, RoutingDecisionRecord)
    ↓
Output + Decision
```

### Phase 2 Monitoring Flow:
```
Daily Routing Logs
    ↓
daily_monitoring_check()
    ├─ Collect yesterday's decisions
    ├─ Recompute τ_cap, τ_risk
    ├─ Compare to baseline
    ├─ Check bin-wise risks
    └─ Generate Alerts
    ↓
Alert List
```

---

## 🐛 Where the Issues Live

### ISSUE #1: Capability ≠ (1 - Risk)
- **Theory**: `docs/reference/RISK_CURVES.md:8`
- **Code**: `src/routing/framework.py:191-275`
- **Problem**: Computed independently, but documented as complementary

### ISSUE #2: Zone Q2 Missing
- **Theory**: `docs/guides/ROUTING_POLICIES.md` (Q2 section)
- **Code**: `src/routing/production_router.py:312-314`
- **Problem**: Returns `"SLM_with_verification"` string instead of model

### ISSUE #3: Capability vs Validity
- **Theory**: `docs/guides/COMPLETE_PIPELINE.md:176`
- **Code**: `src/routing/framework.py:191-219` (validity), `221-275` (quality)
- **Problem**: Different metrics, same name

### ISSUE #4: Risk Variance
- **Theory**: `docs/reference/QUALITY_METRICS.md` (shows 3 methods)
- **Code**: `src/routing/framework.py:244-269` (NEW vs OLD approach)
- **Problem**: 3 different computation methods across tasks

---

## 📋 File Dependency Graph

```
examples/example_code_generation.py
    ↓
src/routing/__init__.py
    ├─ src/routing/production_router.py
    │   ├─ src/utils/stats.py (wilson_interval)
    │   └─ src/routing/framework.py (for AnalysisResult type hints)
    │
    └─ src/routing/framework.py
        ├─ src/utils/stats.py (wilson_interval)
        └─ src/routing/failure_taxonomy.py (optional)

tests/test_complete_pipeline_integration.py
    ├─ src/routing/production_router.py
    └─ src/routing/framework.py

framework/sddf/
    ├─ framework/sddf/ingest.py
    ├─ framework/sddf/difficulty.py
    ├─ framework/sddf/gates.py
    ├─ framework/sddf/curves.py
    ├─ framework/sddf/tipping.py
    └─ ... (many others)
```

---

## ✅ Summary: What to Know Before Fixing

1. **Core System**:
   - `ProductionRouter` in `src/routing/production_router.py` is the main production class
   - `GeneralizedRoutingFramework` in `src/routing/framework.py` is the analysis engine
   - They should work together seamlessly

2. **The Issues**:
   - ISSUE #1 & #3 are in `framework.py` (metric computation)
   - ISSUE #2 is in `production_router.py` (zone Q2 policy)
   - ISSUE #4 is in `framework.py` (risk computation methods)

3. **Tests Matter**:
   - `tests/test_complete_pipeline_integration.py` shows expected behavior
   - Tests will help validate fixes

4. **Documentation is Reference**:
   - `docs/guides/COMPLETE_PIPELINE.md` shows what SHOULD happen
   - `docs/reference/RISK_CURVES.md` explains the math
   - **BUT** they have contradictions with code

5. **Examples are Helpful**:
   - `examples/example_code_generation.py` shows intended usage
   - Can run this to see current behavior

---

**Now you understand the full structure. Ready to fix the issues?**
