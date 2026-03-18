# Multi-Model Benchmark Guide

## Overview

Run 3 different model sizes (0.5B, 1.5B, 3.8B) across 8 tasks using the **same 75 queries** and **same difficulty bins** for fair comparison.

**Key Features:**
- ✅ Same 75 queries (15 per bin) for all models
- ✅ Skips already-completed tasks
- ✅ Parallel execution (2 models at same time)
- ✅ Smart task allocation (0.5B always, 1.5B or 3.8B depending on task)
- ✅ Shows scaling: 0.5B → 1.5B → 3.8B

---

## Quick Start

### Option 1: Run Everything (Recommended)

```bash
python scripts/run_all_models.py --parallel
```

This will:
1. Run 0.5B (tinyllama) on all 8 tasks
2. Run 1.5B or 3.8B (depending on task) on all 8 tasks
3. Run 2 models in parallel per task
4. **Total time: ~1.6-2 hours**

### Option 2: Run Without Parallel (Slower)

```bash
python scripts/run_all_models.py
```

- Runs models sequentially (one at a time)
- **Total time: ~2.5-3 hours**

### Option 3: Verbose Output

```bash
python scripts/run_all_models.py --parallel --verbose
```

- Shows detailed progress for each task

---

## Single Task Execution

Run just one task with a specific model:

```bash
# Run text_generation with tinyllama
python scripts/run_benchmark_all_8_tasks.py tinyllama:1.1b --task text_generation

# Run classification with phi3:mini
python scripts/run_benchmark_all_8_tasks.py phi3:mini --task classification

# Run all 8 tasks with qwen2.5:1.5b (overrides defaults)
python scripts/run_benchmark_all_8_tasks.py qwen2.5:1.5b
```

---

## Model Allocation Plan

Each task tests specific models:

### Tasks using qwen2.5:1.5b (originally):
- text_generation
- code_generation
- maths
- summarization
- retrieval_grounded
- instruction_following

**New plan:** Skip 1.5B → Test 0.5B + 3.8B

### Tasks using phi3:mini (originally):
- classification
- information_extraction

**New plan:** Skip 3.8B → Test 0.5B + 1.5B

---

## Summary of All Runs

| Task | Current (Skip) | Add Model 1 | Add Model 2 |
|------|---|---|---|
| Text Generation | 1.5B | 0.5B | 3.8B |
| Code Generation | 1.5B | 0.5B | 3.8B |
| Classification | 3.8B | 0.5B | 1.5B |
| Maths | 1.5B | 0.5B | 3.8B |
| Summarization | 1.5B | 0.5B | 3.8B |
| Retrieval Grounded | 1.5B | 0.5B | 3.8B |
| Instruction Following | 1.5B | 0.5B | 3.8B |
| Information Extraction | 3.8B | 0.5B | 1.5B |

---

## What Gets Created

After running, you'll have:

```
benchmark_output/
├── text_generation/
│   ├── qwen2.5_1.5b/      ← Already exists (SKIP)
│   ├── tinyllama_0.5b/    ← NEW (75 samples)
│   └── phi3_mini/         ← NEW (75 samples)
│
├── code_generation/
│   ├── qwen2.5_1.5b/      ← Already exists (SKIP)
│   ├── tinyllama_0.5b/    ← NEW (75 samples)
│   └── phi3_mini/         ← NEW (75 samples)
│
... [6 more tasks]

TOTAL: 24 directories × 75 samples = 1,800 samples
```

---

## Important: Same Queries & Bins

**Critical guarantee:** Each model in a task uses:
- ✅ Same 75 sample queries
- ✅ Same 5 difficulty bins (0-4)
- ✅ Same 15 samples per bin

Only difference: **The model** that processes them

This enables fair comparison:
```
Query: "Write a poem about spring"

0.5B (tinyllama):
  Bin 0 (Easy):    [output] - pass/fail
  Bin 4 (Hardest): [output] - pass/fail

1.5B (qwen2.5):
  Bin 0 (Easy):    [output] - pass/fail
  Bin 4 (Hardest): [output] - pass/fail

3.8B (phi3):
  Bin 0 (Easy):    [output] - pass/fail
  Bin 4 (Hardest): [output] - pass/fail
```

---

## Timing Breakdown

### Sequential Execution (--no-parallel)
```
Per task: 0.5B (5 min) + 1.5B/3.8B (12 min) = 17 min
8 tasks × 17 min = 136 min = 2.3 hours
```

### Parallel Execution (--parallel) - RECOMMENDED
```
Per task: 0.5B + (1.5B or 3.8B) run together = 12 min
8 tasks × 12 min = 96 min = 1.6 hours

SAVES: 0.7 hours!
```

---

## Smart Skipping

The system is intelligent about what's already done:

**Scenario: First run crashes on task 5**

Run again:
```bash
python scripts/run_all_models.py --parallel
```

What happens:
- ✅ Tasks 1-4: All models done → SKIP completely
- ✅ Task 5: 0.5B done → RUN 1.5B/3.8B only
- ✅ Tasks 6-8: Continue normally
- ✅ **NO WASTED TIME** - only runs what's needed

---

## Checkpoint Support

All files are checkpointed automatically:

```
benchmark_output/text_generation/tinyllama_0.5b/
├── outputs.jsonl         ← Append-only (can resume)
├── run_manifest.json     ← Audit trail
├── dataset_manifest.json ← Sample tracking
└── sddf_ready.csv        ← Metrics
```

If interrupted:
- Just re-run the command
- System detects completed tasks
- Resumes from checkpoint

---

## Output Files (Per Model+Task)

Each combination generates:

```
outputs.jsonl
  • 75 inference records
  • 14 fields per record
  • Immutable audit trail

sddf_ready.csv
  • Performance by difficulty bin
  • Success rate per bin
  • Latency metrics

part_a_report.md
  • Methodology documentation

part_b_report.md
  • Results and analysis
  • Pass rates by bin
  • Latency breakdown
```

---

## Examples

### Run all models with parallel execution
```bash
python scripts/run_all_models.py --parallel
```

### Run single task to test
```bash
python scripts/run_benchmark_all_8_tasks.py tinyllama:1.1b --task text_generation
```

### Run all 8 tasks with one model
```bash
python scripts/run_benchmark_all_8_tasks.py phi3:mini
```

### Monitor progress
```bash
python scripts/run_all_models.py --parallel --verbose
```

---

## Publication Results

After completion, you'll have:

**1,800 total samples** across:
- 8 tasks
- 3 models (0.5B, 1.5B, 3.8B)
- 75 queries each
- 5 difficulty bins each

**Showing:**
- ✅ Scaling behavior (how does performance increase with model size?)
- ✅ Tipping points (at what difficulty does small model fail?)
- ✅ Cost-benefit tradeoffs (is 3.8B worth 6x slower than 0.5B?)
- ✅ Routing policy (when to use 0.5B vs 1.5B vs 3.8B?)

---

## Troubleshooting

### Model not found
```
[ERROR] Model 'mistral:7b' not found
```

Solution: Pull the model first
```bash
ollama pull tinyllama:1.1b
ollama pull qwen2.5:1.5b
ollama pull phi3:mini
```

### Task fails mid-run

Just re-run:
```bash
python scripts/run_all_models.py --parallel
```

The system will:
- Skip completed parts
- Resume from checkpoint
- Complete missing parts

### Slow inference

Reduce parallel workers (edit run_all_models.py):
```python
with ThreadPoolExecutor(max_workers=1) as executor:  # was 2
```

---

## Questions?

Check the configuration in `scripts/run_all_models.py`:

```python
TASK_MODELS = {
    "text_generation": {
        "current": "qwen2.5:1.5b",
        "models_to_run": ["tinyllama:1.1b", "phi3:mini"]
    },
    ...
}
```

---

## Ready?

```bash
python scripts/run_all_models.py --parallel
```

Estimated time: **1.6-2 hours**

Let it run - you'll have complete multi-model benchmark when done!
