# Semantic Ground Truth Summary

**Date**: 2026-03-19
**Status**: ✅ Semantic verification framework implemented and validated

---

## What We Found

### Two Types of Ground Truth Available

**1. Syntactic Ground Truth** (Built-in `valid` field)
- Measures format/parsing correctness
- 95-100% pass rates (mostly perfect format)
- Limited signal for component learning (too few failures)

**2. Semantic Ground Truth** (Task-specific verification - NEW)
- Measures actual correctness: does the answer solve the task?
- Implemented for **Maths** and **Code Generation**
- Real failure signal that varies per model

---

## Semantic Correctness Results

### Task-Specific Verification Coverage

| Task | Verifiable? | Coverage | Semantic Accuracy |
|------|-------------|----------|-------------------|
| **Maths** | ✅ YES | 80% of samples | 80% correct |
| **Code Generation** | ✅ YES | 60% of samples | 46.7% correct |
| **Text Generation** | ❌ Need reference | 0% | N/A |
| **Classification** | ❌ Need reference | 0% | N/A |
| **Summarization** | ❌ Need reference | 0% | N/A |
| **Retrieval Grounded** | ❌ Need reference | 0% | N/A |
| **Instruction Following** | ❌ Need reference | 0% | N/A |
| **Information Extraction** | ❌ Need reference | 0% | N/A |

---

## How We Verify Semantic Correctness

### Maths Verification
- **Method**: Parse math problems and solve independently
- **Coverage**: 80% of samples (problem types: linear equations, arithmetic, square roots)
- **Examples**:
  - `2x + 5 = 13` → Verify extracted answer = 4.0 ✓
  - `(12 + 8) * 3 - 5` → Verify extracted answer = 55.0 ✓
  - `sqrt(144)` → Verify extracted answer = 12.0 ✓
- **Accuracy**: Qwen 2.5 1.5B: 32/40 correct (80%)

### Code Generation Verification
- **Method**: Execute extracted code blocks and run test cases
- **Coverage**: 60% of samples (syntactically valid code)
- **Tests**:
  - String reverse: Pass "hello" → Expect "olleh"
  - Factorial: Pass 5 → Expect 120
  - Custom logic verification
- **Accuracy**: Qwen 2.5 1.5B: 14/30 correct (46.7%)
- **Failure types**:
  - Incorrect algorithm (e.g., bubble sort with bugs)
  - Incomplete implementation
  - Logic errors despite correct syntax

---

## Key Difference: Syntactic vs Semantic

### Syntactic Validation (Current `valid` field)
```
✓ Output is not empty
✓ Output follows expected format (parseable JSON/code blocks)
✓ Required fields are present
```
**Result**: ~99% pass rate (almost no failures)

### Semantic Validation (Task-specific NEW)
```
✓ Math answer is mathematically correct
✓ Code runs and produces correct output
✓ Classification label matches ground truth (if available)
✓ Summary captures key information (if reference available)
```
**Result**: 46-80% pass rate (meaningful variation per task/model)

---

## Component Learning Implications

### NOW we can correlate SDDF components with REAL semantic failures

**Example**: For Code Generation
- Qwen has 46.7% semantic accuracy (46.7% failure rate)
- This gives us signal to learn: which SDDF components predict failure?
- Hypothesis: More complex code (higher R, |Γ|) → more failures
- Can now test: Does reasoning depth (R) correlate with failure?

### Current Status: Qwen 2.5 1.5B

| Task | Syntactic Failure Rate | Semantic Failure Rate | Improvement Needed |
|------|------------------------|----------------------|-------------------|
| Maths | 0% | 20% | Fix answer extraction/computation |
| Code Gen | 5.3% | 53.3% | Fix code logic/algorithms |
| Others | ~0% | Unknown | Need reference data |

---

## To Enable Semantic Verification for All Tasks

We need **reference datasets** with expected outputs:

### Option 1: Reconstructed from Original Datasets
- Maths: Load MATH dataset from HuggingFace → extract reference answers
- Code: Load HumanEval/MBPP → get reference code/test cases
- Classification: Load SST-2/AG News → get reference labels

### Option 2: Manual Annotation
- Select ~20 samples per task
- Manually verify correctness
- Use for calibration

### Option 3: Use Model-Generated Gold Standard
- Use Llama 3.3 70B as "ground truth" (highest accuracy model)
- Treat its outputs as reference for other models

---

## Files Created

1. **`src/analysis/semantic_verifier.py`**
   - Core verification engine
   - Task-specific logic for maths and code
   - Can be extended for other tasks

2. **`semantic_verification_results.json`**
   - Full results with per-sample verifications
   - Breakdown by task, model, verification type

3. **`component_learner.py`** (from previous)
   - Correlation analysis framework
   - Ready to correlate SDDF components with semantic failures

---

## Recommended Next Steps

### Priority 1: Extend Semantic Verification
- [ ] Add classification verification (need reference labels)
- [ ] Add retrieval QA verification (compare with reference answers)
- [ ] Add code testing with full test suites (not just examples)

### Priority 2: Component Learning with Real Signal
- [ ] Re-run component correlation using semantic failures (not syntactic)
- [ ] Analyze: which components predict semantic failure?
- [ ] Learn task-specific component weights

### Priority 3: Reference Data Integration (Option C)
- [ ] Search HuggingFace for original datasets used in benchmark
- [ ] Match samples to original data with reference annotations
- [ ] Enable verification for all 8 tasks

---

## Conclusion

✅ **We now have real semantic ground truth for 2 tasks (Maths, Code)**
- Option B implemented: Task-specific metrics work
- Clear semantic failure signal (20-53% failure rates)
- Ready for component learning

⏳ **Option C in progress**: HuggingFace dataset search
- To enable all 8 tasks
- Would provide complete coverage

---

**Status**: Framework ready for component learning with semantic correctness
