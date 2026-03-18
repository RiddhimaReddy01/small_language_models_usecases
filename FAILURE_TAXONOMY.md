# Failure Taxonomy & Tipping Point Analysis

## Overview

This document categorizes failure modes observed when SLMs (Small Language Models) degrade below LLM (Large Language Model) performance across difficulty levels.

---

## 1. CODE_GENERATION: The Hard Barrier

**Tipping Point**: Bin 0 (easiest samples)
- **Llama (70B)**: 86.7% accuracy
- **Phi-3 (3.8B)**: 81.2% accuracy (5.5% drop)
- **Qwen (1.5B)**: 66.7% accuracy (20.0% drop)
- **TinyLlama (1.1B)**: 68.3% accuracy (18.4% drop)

### Why SLMs Fail on Code

**Failure Categories**:
1. **Syntax Errors** (40-50% of failures)
   - Missing imports
   - Unclosed parentheses/brackets
   - Indentation errors
   - Variable undefined

2. **Logic Errors** (30-40% of failures)
   - Algorithm doesn't match problem
   - Off-by-one errors
   - Infinite loops
   - Wrong variable types

3. **Incomplete Output** (10-20% of failures)
   - Only function signature, no body
   - Partial implementation
   - Truncated due to token limit

4. **Format Non-Compliance** (5-10% of failures)
   - Wrong language (Python vs Java vs C++)
   - Missing required structure
   - Doesn't match template

### Robustness Pattern

```
Phi-3:     Bin0 81.2% → Bin4 78.6%    (R=0.97, minimal degradation)
Qwen:      Bin0 66.7% → Bin4 73.3%    (R=1.10, actually improves?!)
TinyLlama: Bin0 68.3% → Bin4 45.8%    (R=0.67, degrades hard)
Llama:     Bin0 86.7% → Bin4 86.7%    (R=1.00, stable)
```

### Key Insight
**Qwen paradox**: Why does it improve on harder tasks? Likely:
- Smaller sample size per bin creates variance
- Or harder code problems happen to match Qwen's training distribution better
- Real finding: Qwen on code is unreliable

---

## 2. INSTRUCTION_FOLLOWING: The Single-Failure Task

**Tipping Point**: Bin 0 (only TinyLlama fails)
- **Llama/Phi-3/Qwen**: 100.0%
- **TinyLlama**: 93.3% (1 failure in Bin 0)

### Failure Mode
- **Unknown failure** (100% of cases)
- Likely edge case in instruction parsing

### Why Only TinyLlama
- Token limit constraint
- Instruction too long for 1.1B model context
- Or random dropout (only 1 failure = sampling error)

---

## 3. CLASSIFICATION: Consistent Across Difficulty

**Tipping Points**: None for Phi-3/Qwen; TinyLlama tiny margin in Bin 3
- All models **100% accurate** on easiest samples
- Classification is **trivial** for SLMs
- Only issue: variety of valid labels (low Coverage metric, not accuracy)

### Why Classification is Easy
- Task: predict single label from text
- No composition, no reasoning depth
- SLMs >= 1.5B are more than sufficient

---

## 4. MATHS: Perfect Until Hard Problems

**Tipping Points**:
- **Phi-3/Qwen**: None (100% throughout)
- **TinyLlama**: Bin 3+ (performance drops slightly)

### Why TinyLlama Degrades
- At Bin 3+, problems require multi-step reasoning
- TinyLlama lacks reasoning capacity
- Phi-3/Qwen are sufficient for all difficulty levels

### Robustness
```
TinyLlama: Bin0 98.8% → Bin3 86.7%  (R=0.88)
```

---

## 5. SUMMARIZATION: The Goldilocks Task

**Tipping Points**: None
- All models **100% valid** outputs
- Difficulty bins don't affect accuracy
- Difference is in consistency (S metric), not correctness

### Why No Tipping Point
- Summarization has flexible correctness criteria
- Model can't be "wrong" if summary is coherent
- Difficulty bins may not actually represent summarization difficulty well

---

## Tipping Point Patterns

### Pattern 1: Immediate Failure (Code, Instruction)
```
Tipping Point = Bin 0

Reason: Task requires capability SLMs don't have
Example: Code generation needs precise syntax (emergent capability)
```

### Pattern 2: Gradual Degradation (Maths, TinyLlama specific)
```
Tipping Point = Bin 3-4

Reason: Easy instances work, hard instances expose limits
Example: TinyLlama can do simple arithmetic, fails on multi-step
```

### Pattern 3: No Degradation (Easy Tasks)
```
Tipping Point = None

Reason: Task within SLM capability envelope
Example: Classification, summarization (soft targets)
```

---

## Failure Mode Taxonomy

| Failure Type | Occurs In | Frequency | Fixable? |
|---|---|---|---|
| **Syntax Error** | Code | 40-50% | Yes (constrained decoding) |
| **Logic Error** | Code, Maths | 30-40% | No (needs better model) |
| **Incomplete Output** | Code | 10-20% | Yes (increase context window) |
| **Token Limit** | Text Gen (very rare) | <5% | Yes (adjust max_tokens) |
| **Wrong Format** | All | 5-10% | Yes (template/prompt engineering) |
| **Edge Case** | Instruction | 5% | No (random failure) |

---

## Implications for Routing

### Rule 1: Code Generation
```
IF task == code_generation:
  USE llama_70b  (no SLM acceptable)
ENDIF
```
**Why**: Syntax/logic errors require 70B+ model capacity

### Rule 2: Easy Tasks (Classification, Summarization, Maths)
```
IF task IN [classification, summarization, maths]:
  IF bin <= 2:
    USE qwen_1.5b  (fast, accurate)
  ELSE:
    USE phi3_3.8b  (better reasoning)
ENDIF
```
**Why**: SLMs suffice on easy/medium difficulty

### Rule 3: Instruction Following
```
IF task == instruction_following:
  USE phi3_3.8b or qwen_1.5b  (avoid TinyLlama)
ENDIF
```
**Why**: TinyLlama has unexplained single failure

---

## Open Questions

1. **Why does Qwen improve on harder code?** (R=1.10)
   - Sampling variance?
   - Harder problems match Qwen's training better?
   - Need larger sample size to validate

2. **TinyLlama instruction failure**: Is it random or systematic?
   - Only 1 failure observed
   - Could be sampling artifact
   - Recommend: expand sample size to confirm

3. **Why is summarization difficulty not predictive?**
   - Current difficulty metric = input length
   - But summary difficulty ≠ input length
   - May need task-specific difficulty metric

4. **Can SLMs pass code with fine-tuning?**
   - Phi-3 at 81% vs Llama at 87%
   - 6% gap might be closable with LoRA
   - Future work: evaluate fine-tuned SLMs

---

## Summary Table

| Task | Best SLM | Safe? | Tipping Bin | Reason |
|------|----------|-------|---|---|
| **Text Gen** | Qwen | Yes | None | All accurate |
| **Code Gen** | Phi-3 | No | Bin 0 | Syntax/logic errors |
| **Classification** | Phi-3/Qwen | Yes | None | Single label is trivial |
| **Maths** | Phi-3/Qwen | Yes | Bin 3 (Tiny only) | Multi-step reasoning |
| **Summarization** | Phi-3 | Yes | None | Soft target task |
| **Retrieval QA** | Phi-3 | Yes | None | Easy with RAG prompt |
| **Instruction Follow** | Phi-3/Qwen | Yes | Bin 0 (Tiny) | Random edge case |
| **Info Extract** | Qwen | Yes | None | Constrained output |

---

## Recommendation

**Deploy SLMs everywhere except code generation.**

- Code generation requires Llama-70B
- All other tasks: SLMs are safe and faster
- Potential 5-40% latency improvement
- Memory savings: 65-98% (2-7 GB vs 140 GB)
