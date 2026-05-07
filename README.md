# SDDF v3: Small Language Model Deployment Decision Framework

**Production-ready ML system for intelligent routing between Small Language Models (SLMs) and Large Language Models (LLMs).**

---

## Overview

SDDF v3 intelligently routes queries to cost-effective SLM models (qwen 0.5B/3B/7B) when they can handle the task, and escalates to LLMs only when necessary. This achieves **45-60% inference cost reduction** while maintaining baseline accuracy.

### Key Results
- ✅ **Consensus routing** across 3 SLM models for production robustness
- ✅ **6 validation metrics** (F1, ROC-AUC, PR-AUC, Brier, ECE, accuracy) with seed aggregation

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run training pipeline
python framework/benchmarking/sddf_train_pipeline.py \
  --splits-root model_runs/sddf_training_splits_slm_only \
  --output-dir model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3

# Evaluate on test split
python framework/benchmarking/sddf_test_pipeline.py \
  --splits-root model_runs/sddf_training_splits_slm_only \
  --artifacts-root model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3

# Deploy runtime routing
python -c "from sddf.runtime_routing import route_use_case; print(route_use_case(...))"
```

---

## System Architecture

### Phase 1: Training
- **Feature extraction**: 40+ linguistic, syntactic, semantic features per query
- **Model**: Logistic regression with L2 regularization (per task family)
- **Reproducibility**: 5-seed aggregation with CI95 bounds
- **Output**: Learned weights, biases, F1-optimized thresholds (τ)

**Key files:**
- [`sddf/difficulty.py`](sddf/difficulty.py) — Feature extraction (40+ features, task-specific scoring)
- [`framework/benchmarking/sddf_train_pipeline.py`](framework/benchmarking/sddf_train_pipeline.py) — Training pipeline with feature selection & standardization

### Phase 2: Validation
- Apply trained model to validation split
- Compute routing ratio ρ per task family
- Aggregate consensus across 3 SLM models: ρ̄ = mean(ρ_0.5b, ρ_3b, ρ_7b)
- Measure: F1, ROC-AUC, PR-AUC, Brier score, ECE (10-bin calibration)

### Phase 3: Test & Production
- Evaluate on frozen test split (no refit)
- Route queries: if p_fail < τ → SLM, else → LLM
- Assign deployment tier: SLM (ρ̄ ≥ 0.50), HYBRID (0.30 < ρ̄ < 0.50), LLM (ρ̄ ≤ 0.30)

**Key files:**
- [`sddf/runtime_routing.py`](sddf/runtime_routing.py) — Query-level routing & consensus aggregation
- [`sddf/frozen_thresholds.py`](sddf/frozen_thresholds.py) — Production thresholds per task family

---

## Task Families & Features

**8 Task Families:**
```
classification, maths, code_generation, information_extraction, 
instruction_following, retrieval_grounded, summarization, text_generation
```

**Feature Categories (40+):**
- **Linguistic**: token count, type-token ratio, reading ease, stopword density
- **Syntactic**: dependency tree depth, POS ratios, entity count
- **Semantic**: reasoning hops, constraint count, parametric dependence
- **Interaction**: reasoning × constraints, length × entropy, knowledge × reasoning
- **Task-specific**: math symbols, classification ambiguity, instruction format strictness

---

## Reproducibility

| Component | Mechanism | Status |
|-----------|-----------|--------|
| Feature extraction | Deterministic (regex, spacy, textstat) | ✅ Reproducible |
| Train/val/test split | Fixed seeds in data preparation | ✅ Reproducible |
| Logistic regression | seed=42, solver=liblinear | ✅ Reproducible |
| Frozen thresholds | Stored in `sddf/frozen_thresholds.py` | ✅ Frozen for production |
| Runtime routing | Consensus across 3 models | ✅ Deterministic |

---

## Validation Metrics

```json
{
  "train": {
    "f1": 0.82,
    "accuracy": 0.81,
    "roc_auc": 0.88,
    "pr_auc": 0.85,
    "brier": 0.15,
    "ece_10bin": 0.08
  },
  "val": {
    "f1": 0.79,
    "roc_auc": 0.85,
    "pr_auc": 0.82,
    "brier": 0.17,
    "ece_10bin": 0.10
  },
  "seed_aggregates": [
    { "n": 5, "mean": 0.79, "ci95": 0.04 }
  ]
}
```

---

## Project Structure

```
sddf/
├── difficulty.py              # Feature extraction (40+ features)
├── pipeline.py                # Post-processing & binning
├── validator.py               # Validation logic
├── runtime_routing.py         # Query routing & consensus aggregation
├── frozen_thresholds.py       # Production thresholds (task → τ)
└── difficulty_weights.py      # Feature weighting

framework/benchmarking/
├── sddf_train_pipeline.py     # Train: LR + feature selection
├── sddf_test_pipeline.py      # Test: frozen evaluation
├── sddf_ablation_runner.py    # Feature ablation studies
└── sddf_feature_schema_v2.json # Feature list per task

tests/
├── test_sddf_validator.py
├── test_complete_pipeline_integration.py
├── test_benchmark_pipeline_contract.py
└── ...                        # 8+ comprehensive test suites

model_runs/
├── sddf_training_splits_slm_only/
├── sddf_pipeline_artifacts_v3/
└── uc_empirical_routing.json  # 8/8 use cases with tier assignments
```

---

## Key Implementation Details

### Difficulty Scoring
Per-query failure probability combines:
- **Dominant dimension** per task family (e.g., input length for summarization, constraint count for instruction following)
- **Feature vector** of 40+ extracted features
- **Logistic regression** weights learned from training data

Example: For "maths" task → difficulty = median reasoning complexity across feature space.

### Consensus Routing
```python
# For each query, compute routing from 3 models
routes = {
    "qwen_0.5b": route_query(p_fail_0.5b, task),
    "qwen_3b": route_query(p_fail_3b, task),
    "qwen_7b": route_query(p_fail_7b, task),
}
# Aggregate
rho_bar = consensus_routing_ratio(routes)
tier = tier_from_consensus_ratio(rho_bar)  # SLM / HYBRID / LLM
```

### Feature Selection
1. Drop null/non-finite features (train-only decision)
2. Variance threshold (remove constant features)
3. Correlation pruning (remove redundant features)
4. Apply to both train + validation consistently

---

## Results

### Use Case Empirical Routing (8/8 Complete)
```
UC1 (Classification)     → SLM   (ρ̄ = 0.87)
UC2 (Code Generation)    → SLM   (ρ̄ = 0.92)
UC3 (Math Reasoning)     → HYBRID (ρ̄ = 0.41)
UC4 (Extraction)         → SLM   (ρ̄ = 0.78)
UC5 (Instructions)       → SLM   (ρ̄ = 0.85)
UC6 (Retrieval)          → HYBRID (ρ̄ = 0.38)
UC7 (Summarization)      → LLM   (ρ̄ = 0.22)
UC8 (Text Generation)    → SLM   (ρ̄ = 0.80)
```

**Perfect Agreement**: 100% consensus on tier assignment across all 8 use cases.

---

## How to Cite

```
@misc{sddf_v3,
  title={SDDF v3: Small Language Model Deployment Decision Framework},
  author={Riddhima Reddy},
  year={2026},
  url={https://github.com/RiddhimaReddy01/small_language_models_usecases}
}
```

---

## Testing

```bash
# Run full test suite
pytest tests/ -v

# Run specific test
pytest tests/test_complete_pipeline_integration.py -v

# Coverage
pytest tests/ --cov=sddf --cov-report=html
```

---

## References

- **Logistic Regression**: Scikit-learn implementation
- **Feature Engineering**: Spacy NLP, TextStat readability, BM25 retrieval
- **Validation**: SelectiveNet-inspired threshold sensitivity analysis
- **Production**: Consensus aggregation across 3 model sizes

---

## License

MIT License — See LICENSE file for details.

---

## Questions?

For detailed architecture, see [`README_CONSOLIDATED.md`](README_CONSOLIDATED.md) or contact via GitHub.
