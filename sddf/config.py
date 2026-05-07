"""
SDDF Configuration - Centralized Parameters for Reproducibility

This file documents all critical parameters for ML reproducibility.
All hyperparameters, seeds, and thresholds are defined here.
"""

# ============================================================================
# RANDOM SEED (for reproducibility)
# ============================================================================
RANDOM_SEED = 42


# ============================================================================
# TASK FAMILIES (8 classification tasks)
# ============================================================================
TASK_FAMILIES = [
    "classification",
    "code_generation",
    "information_extraction",
    "instruction_following",
    "maths",
    "retrieval_grounded",
    "summarization",
    "text_generation",
]

NUM_TASKS = len(TASK_FAMILIES)


# ============================================================================
# SLM MODELS (3 Qwen variants)
# ============================================================================
SLM_MODELS = [
    "qwen2.5_0.5b",
    "qwen2.5_3b",
    "qwen2.5_7b",
]

NUM_MODELS = len(SLM_MODELS)


# ============================================================================
# FEATURE ENGINEERING (Difficulty prediction)
# ============================================================================
DIFFICULTY_FEATURES = [
    "n_in",
    "entropy",
    "reasoning_proxy",
    "constraint_count",
    "parametric_dependence",
    "dependency_distance",
    "reasoning_x_constraint",
    "length_x_entropy",
    "knowledge_x_reasoning",
    "classification_ambiguity",
    "classification_negation_density",
    "classification_domain_shift",
    "math_numeric_density",
    "math_symbol_density",
    "math_precision_cues",
    "instruction_format_strictness",
    "instruction_prohibition_count",
    "instruction_step_count",
    "instruction_conflict_cues",
]

NUM_FEATURES = len(DIFFICULTY_FEATURES)


# ============================================================================
# LOGISTIC REGRESSION (Train Phase)
# ============================================================================
LR_SOLVER = "lbfgs"
LR_MAX_ITER = 1000
LR_RANDOM_STATE = RANDOM_SEED

# Training target: binary classification
# y = 1 if SLM fails on query q
# y = 0 if SLM succeeds on query q


# ============================================================================
# FROZEN THRESHOLDS (Test Phase - seed42, empirically learned)
# ============================================================================
FROZEN_TAU_CONSENSUS = {
    "classification": 0.6667,           # consensus of [1.00, 0.50, 0.50]
    "code_generation": 1.0000,          # consensus of [1.00, 1.00, 1.00]
    "information_extraction": 0.9167,   # consensus of [0.75, 1.00, 1.00]
    "instruction_following": 0.9167,    # consensus of [0.75, 1.00, 1.00]
    "maths": 0.3333,                    # consensus of [1.00, 0.00, 0.00]
    "retrieval_grounded": 0.9167,       # consensus of [0.75, 1.00, 1.00]
    "summarization": 1.0000,            # consensus of [1.00, 1.00, 1.00]
    "text_generation": 1.0000,          # consensus of [1.00, 1.00, 1.00]
}


# ============================================================================
# RUNTIME ROUTING (Default tier thresholds - optimized via sensitivity analysis)
# ============================================================================
# These are DEFAULT values; use sensitivity analysis to find optimal thresholds
# that maximize weighted accuracy for your deployment data

TIER_SLM_THRESHOLD = 0.50      # Paper band: rho_bar >= 0.50 -> SLM tier
TIER_LLM_THRESHOLD = 0.30      # Paper band: rho_bar < 0.30 -> LLM tier
# HYBRID tier: 0.30 <= rho_bar < 0.50


# ============================================================================
# THRESHOLD SENSITIVITY ANALYSIS (SelectiveNet-inspired)
# ============================================================================
SENSITIVITY_THRESHOLD_RANGE = (0.2, 0.9)    # Min, max thresholds to sweep
SENSITIVITY_THRESHOLD_STEP = 0.05            # Grid resolution
SENSITIVITY_OBJECTIVE = "weighted_accuracy"  # Optimization criterion


# ============================================================================
# USE CASES (8 enterprise use cases mapped to task families)
# ============================================================================
USE_CASES = {
    "UC1": {"name": "SMS Threat Detection", "task_family": "classification", "domain": "cybersecurity"},
    "UC2": {"name": "Invoice Field Extraction", "task_family": "information_extraction", "domain": "finance"},
    "UC3": {"name": "Support Ticket Routing", "task_family": "classification", "domain": "customer_service"},
    "UC4": {"name": "Product Review Sentiment", "task_family": "classification", "domain": "customer_service"},
    "UC5": {"name": "Automated Code Review", "task_family": "code_generation", "domain": "developer_tools"},
    "UC6": {"name": "Clinical Triage", "task_family": "classification", "domain": "healthcare"},
    "UC7": {"name": "Legal Contract Risk", "task_family": "summarization", "domain": "legal"},
    "UC8": {"name": "Financial Report Drafting", "task_family": "text_generation", "domain": "finance"},
}

NUM_USE_CASES = len(USE_CASES)


# ============================================================================
# DATA PATHS (model runs and artifacts)
# ============================================================================
TRAINING_DATA_ROOT = "model_runs/sddf_training_splits"
VALIDATION_TEST_DATA_ROOT = "model_runs/clean_deterministic_splits"
OUTPUT_DIR = "model_runs/test_with_frozen_thresholds"


# ============================================================================
# REPRODUCIBILITY CHECKLIST
# ============================================================================
"""
To reproduce experiments:

1. Set environment:
   - Random seed: RANDOM_SEED = 42
   - Python version: 3.10+ (see requirements.txt)
   - Dependencies: pip install -r requirements.txt

2. Train phase:
   - Input: model_runs/sddf_training_splits/{task}/{model}/{split}.jsonl
   - Features: DIFFICULTY_FEATURES (19 features)
   - Model: LogisticRegression(solver=LR_SOLVER, max_iter=LR_MAX_ITER, random_state=RANDOM_SEED)
   - Output: Learned weights + frozen thresholds (FROZEN_TAU_CONSENSUS)

3. Validation phase:
   - Input: model_runs/clean_deterministic_splits/{task}/{model}/val.jsonl
   - Apply: frozen thresholds to compute ρ per model
   - Aggregate: ρ̄ = mean(ρ_0.5b, ρ_3b, ρ_7b)
   - Output: Per-task capability/risk curves, consensus metrics

4. Test phase:
   - Input: model_runs/clean_deterministic_splits/{task}/{model}/test.jsonl
   - Apply: frozen thresholds τ from FROZEN_TAU_CONSENSUS
   - Routing: if p_fail < τ → SLM, else → LLM
   - Aggregate: ρ̄ per task family
   - Output: Test phase results (tier assignments, accuracies)

5. Threshold optimization:
   - Sweep: SENSITIVITY_THRESHOLD_RANGE, SENSITIVITY_THRESHOLD_STEP
   - Objective: Maximize SENSITIVITY_OBJECTIVE (weighted_accuracy)
   - Output: Optimal slm_threshold, llm_threshold

6. Runtime deployment:
   - Use optimal thresholds from step 5 (or defaults if not computed)
   - Route queries: compare p_fail < τ per task family
   - Assign tiers: based on ρ̄ and optimal thresholds

Expected outputs:
- model_runs/test_with_frozen_thresholds/validation_with_frozen.json
- model_runs/test_with_frozen_thresholds/test_with_frozen.json
- model_runs/test_with_frozen_thresholds/usecase_tiers_with_frozen.json
- model_runs/test_with_frozen_thresholds/threshold_sensitivity.json
"""
