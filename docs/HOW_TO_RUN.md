# How to Run the Publication-Ready Benchmark Pipeline

## 5-Minute Setup

### Step 1: Verify Ollama is Running

```bash
# Terminal 1: Check Ollama is available
ollama --version
# Should output: ollama version 0.18.1 (or similar)

# If not running, start it:
ollama serve
# Keep this terminal open (Ollama will run in background)
```

Verify models are available:
```bash
ollama list
# Should show your models (qwen2.5:0.5b, phi3:mini, etc.)
```

### Step 2: Prepare Your Data (75 Examples)

You need CSV files with columns: `sample_id`, `bin`, `text`, `model_size`

Example: `text_generation/rebin_results.csv`
```csv
sample_id,bin,text,model_size,difficulty_score
sample_0,0,"Explain quantum computing",0.5B,2.3
sample_1,0,"What is AI?",0.5B,2.1
...
sample_74,4,"Complex reasoning about...",0.5B,8.9
```

**Quick prep script**:
```python
import pandas as pd

# Load your existing data
df = pd.read_csv("text_generation/rebin_results.csv")

# Sample 75 examples (15 per bin if it has 5 bins)
df_sampled = pd.concat([
    df[df['difficulty_bin'] == b].sample(min(15, len(df[df['difficulty_bin'] == b])))
    for b in range(5)
])

# Ensure required columns
df_sampled['sample_id'] = df_sampled.index.astype(str)
df_sampled['bin'] = df_sampled['difficulty_bin']
df_sampled['text'] = df_sampled['input_text']  # Rename if needed
df_sampled['model_size'] = '0.5B'  # Set appropriately

# Save
df_sampled[['sample_id', 'bin', 'text', 'model_size']].to_csv(
    "text_generation/benchmark_75.csv", index=False
)
print(f"Saved {len(df_sampled)} examples")
```

---

## Full Walkthrough (Step-by-Step)

### Phase 1: Prepare Configuration (10 minutes)

**File: `run_benchmark_inference_example.py`**

Create this file:

```python
#!/usr/bin/env python3
"""
Example: Run benchmark on 75 examples, 2 models
"""

from pathlib import Path
from benchmark_inference_pipeline import (
    BenchmarkInferenceEngine,
    DatasetManifest,
    PromptConfig,
    generate_sddf_ready_output,
)
import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_ROOT = Path("./benchmark_output")
BACKEND = "ollama"

# Task configuration: each task gets one model
TASKS_CONFIG = {
    "text_generation": {
        "model": "qwen2.5:0.5b",
        "examples_csv": Path("text_generation/benchmark_75.csv"),
        "prompt_template_v": "v1.0",
        "system_prompt": "You are a helpful assistant.",
        "instruction_wrapper": "Q: {input}\nA:",
    },
    "code_generation": {
        "model": "qwen2.5-coder:0.5b",
        "examples_csv": Path("code_generation/benchmark_75.csv"),
        "prompt_template_v": "v1.0",
        "system_prompt": "You are an expert programmer.",
        "instruction_wrapper": "Problem: {input}\nSolution:",
    },
    "classification": {
        "model": "phi3:mini",
        "examples_csv": Path("classification/benchmark_75.csv"),
        "prompt_template_v": "v1.0",
        "system_prompt": "Classify the following text.",
        "instruction_wrapper": "Text: {input}\nClass:",
    },
    "maths": {
        "model": "qwen2.5:0.5b",
        "examples_csv": Path("maths/benchmark_75.csv"),
        "prompt_template_v": "v1.0",
        "system_prompt": "Solve the following math problem.",
        "instruction_wrapper": "Problem: {input}\nAnswer:",
    },
    # Add more tasks as needed
}

# ============================================================================
# RUN EACH TASK
# ============================================================================

def run_task(task: str, config: dict) -> Path:
    """Run a single task with full publication infrastructure"""

    print(f"\n{'='*70}")
    print(f"Task: {task}")
    print(f"Model: {config['model']}")
    print(f"Examples: {config['examples_csv']}")
    print(f"{'='*70}\n")

    # Load examples
    examples_df = pd.read_csv(config["examples_csv"])
    print(f"Loaded {len(examples_df)} examples")
    print(f"Bins: {sorted(examples_df['bin'].unique())}")
    print(f"Distribution: {examples_df['bin'].value_counts().sort_index().to_dict()}")

    examples = examples_df.to_dict("records")

    # Create prompt config (task-specific)
    prompt_config = PromptConfig(
        task=task,
        template_version=config["prompt_template_v"],
        system_prompt=config["system_prompt"],
        instruction_wrapper=config["instruction_wrapper"],
        temperature=0.7,
        top_p=0.9,
        max_tokens=200,
        stop_tokens=["\n\n", "Human:", "Assistant:"],
        parsing_rules={},
        seed=42
    )

    # Create dataset manifest
    bins = sorted(examples_df['bin'].unique())
    target_per_bin = {int(b): len(examples_df[examples_df['bin'] == b]) for b in bins}
    samples_per_bin = {
        int(b): examples_df[examples_df['bin'] == b]['sample_id'].tolist()
        for b in bins
    }

    dataset_manifest = DatasetManifest(
        task=task,
        source_dataset="benchmark_2024",
        selection_method="stratified_by_difficulty",
        binning_rule="quantile(5)",
        seed=42,
        target_per_bin=target_per_bin,
        samples_included=samples_per_bin
    )

    # Create output directory
    task_output = OUTPUT_ROOT / task / config["model"].replace("/", "_").replace(":", "_")
    task_output.mkdir(parents=True, exist_ok=True)

    # Create engine
    engine = BenchmarkInferenceEngine(
        task=task,
        model_name=config["model"],
        dataset_manifest=dataset_manifest,
        prompt_config=prompt_config,
        output_dir=task_output,
        backend=BACKEND
    )

    print(f"Output: {task_output}\n")

    # Run inference (MAIN STEP)
    print("Starting inference batch...\n")
    results_df = engine.run_batch(examples)

    print(f"\nResults: {len(results_df)} examples processed")
    print(f"Success: {len(results_df[results_df['status'] == 'success'])}")
    print(f"Failed: {len(results_df[results_df['status'] == 'failed'])}")
    print(f"Invalid: {len(results_df[results_df['status'] == 'invalid'])}")

    # Finalize run
    print("\nFinalizing run...")
    engine.finalize_run(results_df)

    # Generate SDDF output
    print("Generating SDDF output...")
    sddf_path = generate_sddf_ready_output(task_output)
    print(f"SDDF ready: {sddf_path}\n")

    return task_output


def main():
    """Run all tasks"""
    print("\n" + "="*70)
    print("PUBLICATION-READY BENCHMARK PIPELINE")
    print("="*70)

    results = {}
    for task, config in TASKS_CONFIG.items():
        try:
            output_dir = run_task(task, config)
            results[task] = {"status": "success", "output_dir": str(output_dir)}
        except Exception as e:
            print(f"ERROR in {task}: {e}")
            results[task] = {"status": "failed", "error": str(e)}

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    success = sum(1 for r in results.values() if r["status"] == "success")
    failed = sum(1 for r in results.values() if r["status"] == "failed")

    print(f"\nCompleted: {success}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print(f"\nOutput root: {OUTPUT_ROOT}")

    for task, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        print(f"{status} {task}: {result.get('output_dir', result.get('error'))}")

    print("\nAll artifacts ready for publication!")


if __name__ == "__main__":
    main()
```

---

## Running It

### Option A: Run All Tasks (Recommended for First Time)

```bash
# Terminal 2 (keep Ollama running in Terminal 1)
cd "c:\Users\riddh\OneDrive\Desktop\SLM use cases"

python run_benchmark_inference_example.py
```

**Expected output**:
```
======================================================================
PUBLICATION-READY BENCHMARK PIPELINE
======================================================================

======================================================================
Task: text_generation
Model: qwen2.5:0.5b
Examples: text_generation/benchmark_75.csv
======================================================================

Loaded 75 examples
Bins: [0, 1, 2, 3, 4]
Distribution: {0: 15, 1: 15, 2: 15, 3: 15, 4: 15}
Output: ./benchmark_output/text_generation/qwen2_5_0_5b

Starting inference batch...

Processing sample_0 (bin 0, 1/75)
Processing sample_1 (bin 0, 2/75)
...
Processing sample_74 (bin 4, 75/75)

Results: 75 examples processed
Success: 74
Failed: 0
Invalid: 1

Finalizing run...
Generating SDDF output...
SDDF ready: ./benchmark_output/text_generation/qwen2_5_0_5b/sddf_ready.csv

[Repeats for code_generation, classification, maths, ...]

======================================================================
SUMMARY
======================================================================

Completed: 4/4
Failed: 0/4

Output root: ./benchmark_output
✅ text_generation: ./benchmark_output/text_generation/qwen2_5_0_5b
✅ code_generation: ./benchmark_output/code_generation/qwen2_5_coder_0_5b
✅ classification: ./benchmark_output/classification/phi3_mini
✅ maths: ./benchmark_output/maths/qwen2_5_0_5b

All artifacts ready for publication!
```

**Timing**:
- CPU: 2-3 hours (can run overnight)
- GPU (if available): 30-60 minutes

---

### Option B: Run Single Task (for Testing)

```bash
python -c "
from pathlib import Path
from run_benchmark_inference_example import run_task

config = {
    'model': 'qwen2.5:0.5b',
    'examples_csv': Path('text_generation/benchmark_75.csv'),
    'prompt_template_v': 'v1.0',
    'system_prompt': 'You are helpful.',
    'instruction_wrapper': 'Q: {input}\nA:',
}

run_task('text_generation', config)
"
```

---

## Monitor Progress

### Watch Logs in Real-Time

```bash
# Terminal 3: Watch logs
tail -f benchmark_output/text_generation/logs/*.log
```

### Check Current Status

```bash
# Check how many examples completed
wc -l benchmark_output/text_generation/qwen2_5_0_5b/outputs.jsonl

# Check coverage report
python -c "
import json
with open('benchmark_output/text_generation/qwen2_5_0_5b/run_manifest.json') as f:
    manifest = json.load(f)
    print(json.dumps(manifest['completion_by_bin'], indent=2))
"
```

---

## What Gets Produced

After running, you'll have:

```
benchmark_output/
├── all_runs.jsonl                    # Master log
└── text_generation/
    └── qwen2_5_0_5b/
        ├── run_manifest.json         # ✅ Audit trail
        ├── config_snapshot.json      # ✅ Full config
        ├── hardware.json             # ✅ CPU, RAM, OS, versions
        ├── prompt_config.json        # ✅ Template, decoding
        ├── dataset_manifest.json     # ✅ Sample selection
        ├── outputs.jsonl             # ✅ All 14-field records
        ├── summary.json              # ✅ Per-bin stats
        ├── sddf_ready.csv            # ✅ SDDF output
        └── logs/
            └── run_*.log             # ✅ Execution logs
```

---

## Inspect Results

### View Sample Record
```bash
python -c "
import json
with open('benchmark_output/text_generation/qwen2_5_0_5b/outputs.jsonl') as f:
    first = json.loads(f.readline())
    print(json.dumps(first, indent=2))
"
```

### Check SDDF Output
```bash
python -c "
import pandas as pd
df = pd.read_csv('benchmark_output/text_generation/qwen2_5_0_5b/sddf_ready.csv')
print(df)
"
```

### View Coverage
```bash
python -c "
import json
with open('benchmark_output/text_generation/qwen2_5_0_5b/run_manifest.json') as f:
    manifest = json.load(f)
    for bin_id, coverage in sorted(manifest['coverage_by_bin'].items()):
        print(f'Bin {bin_id}: {coverage[\"success\"]}/{coverage[\"target\"]} ({coverage[\"coverage_pct\"]:.0f}%)')
"
```

---

## If Interrupted

The pipeline is resumable. Just run again:

```bash
python run_benchmark_inference_example.py
```

It will:
1. Detect completed examples
2. Skip them
3. Continue from where it left off
4. No data loss, no re-runs

---

## Troubleshooting

### Ollama Not Found
```bash
# Solution: Start Ollama in another terminal
ollama serve
```

### Model Not Found
```bash
# Solution: Pull the model
ollama pull qwen2.5:0.5b
ollama pull phi3:mini
ollama list  # Verify
```

### Memory Issues
```bash
# Use smaller quantization
ollama pull qwen2.5:0.5b-q4_0  # 4-bit quantized (smaller)
```

### Inference Too Slow
```bash
# Check if GPU is available
python -c "import torch; print(torch.cuda.is_available())"

# If no GPU, consider using quantized models (faster)
# Or reduce max_tokens in prompt_config
```

### Connection Refused
```bash
# Ollama not running. In Terminal 1:
ollama serve
```

---

## Next: Generate Reports

Once all tasks complete, you have:
- ✅ All 10 publication requirements satisfied
- ✅ Hardware specs recorded
- ✅ Prompt versions saved
- ✅ Sample selection documented
- ✅ Per-bin metrics computed
- ✅ SDDF output ready

**Generate Part A/Part B reports** using the artifacts in `benchmark_output/`

---

## Quick Checklist

- [ ] Ollama running (`ollama serve`)
- [ ] Models downloaded (`ollama list`)
- [ ] Data prepared (75 examples × 8 tasks)
- [ ] `run_benchmark_inference_example.py` created
- [ ] Run: `python run_benchmark_inference_example.py`
- [ ] Monitor: `tail -f benchmark_output/*/logs/*.log`
- [ ] Check results in `benchmark_output/`
- [ ] Generate reports from artifacts

---

## That's It!

Run the script and it handles everything:
- ✅ Per-query metadata
- ✅ Hardware capture
- ✅ Prompt tracking
- ✅ Dataset manifest
- ✅ Failure taxonomy
- ✅ Validation
- ✅ Coverage tracking
- ✅ SDDF output
- ✅ Resume support

**Ready to publish. Just run it.**
