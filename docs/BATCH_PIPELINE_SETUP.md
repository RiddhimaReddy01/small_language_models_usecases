# Batch Inference Pipeline Setup

## Overview
Production-grade batch inference pipeline with:
- ✅ CPU + Quantized models only
- ✅ Fixed model per job
- ✅ Parallelism = f(model size)
- ✅ Load model once per batch
- ✅ Auto-retry + error logging
- ✅ Autosave every query
- ✅ Resume if interrupted
- ✅ No manual intervention
- ✅ Offline (Ollama)
- ✅ No re-running completed queries

---

## Prerequisites

### 1. Install Ollama (Offline Inference)
```bash
# Download from https://ollama.ai
# Or install via package manager:

# macOS
brew install ollama

# Linux (Ubuntu/Debian)
curl https://ollama.ai/install.sh | sh

# Windows
# Download installer from https://ollama.ai
```

Verify:
```bash
ollama --version
ollama serve  # Start in background (keep running)
```

### 2. Python Dependencies
```bash
pip install pandas numpy ollama
# or for transformers backend:
pip install transformers torch
```

### 3. Download Models to Ollama
```bash
# Pull quantized models (first-time only, ~5GB total)
ollama pull qwen2.5:0.5b      # ~356MB
ollama pull qwen2.5:1.5b      # ~1GB
ollama pull qwen2.5-coder:0.5b # ~356MB
ollama pull llama2:7b          # ~4GB
ollama pull phi:latest         # ~1.6GB

# Verify
ollama list
```

---

## Architecture

```
run_batch_pipeline.sh (Orchestrator)
    |
    +-- batch_inference_pipeline.py (Core Engine)
         |
         +-- QueryManifest (Deduplication)
         |    |
         |    +-- manifest.json (completed queries)
         |
         +-- InferenceCheckpoint (Resumability)
         |    |
         |    +-- task_model.checkpoint.json
         |
         +-- BatchInferenceEngine
              |
              +-- Ollama Client OR Transformers Pipeline
                   |
                   +-- Auto-retry (max 3 attempts)
                   +-- Error logging
                   +-- Checkpoint every N examples
```

---

## Files

| File | Purpose |
|------|---------|
| `batch_inference_pipeline.py` | Core inference engine |
| `run_batch_pipeline.sh` | Orchestration script |
| `BATCH_PIPELINE_SETUP.md` | This file |

---

## Usage

### Start Ollama (Keep Running)
```bash
ollama serve
# Keep this terminal open, runs on http://localhost:11434
```

### Run Full Pipeline
```bash
# Make script executable
chmod +x run_batch_pipeline.sh

# Start pipeline (runs all 8 tasks)
./run_batch_pipeline.sh

# Output:
# inference_output/
# ├── pipeline.log
# ├── manifest.json
# ├── .checkpoints/
# │   ├── text_generation_qwen2.5:0.5b.checkpoint.json
# │   ├── code_generation_qwen2.5-coder:0.5b.checkpoint.json
# │   └── ...
# ├── text_generation/
# │   ├── text_generation_qwen2_5_0_5b_instruct_results.csv
# │   └── logs/
# ├── code_generation/
# └── ...
```

### Resume Interrupted Pipeline
```bash
# If interrupted, resumption is automatic on next run
# (Will skip already-completed queries)

./run_batch_pipeline.sh --resume

# Or just re-run normally:
./run_batch_pipeline.sh
# Will detect existing checkpoints and skip completed examples
```

### Run Single Task
```bash
python3 batch_inference_pipeline.py \
    text_generation \
    "Qwen/Qwen2.5-0.5B-Instruct" \
    text_generation/rebin_results.csv \
    ./inference_output/text_generation \
    ollama
```

---

## Configuration

### Edit Task-Model Mapping
In `run_batch_pipeline.sh`, modify:

```bash
declare -A TASK_MODELS=(
    ["text_generation"]="Qwen/Qwen2.5-0.5B-Instruct"
    ["code_generation"]="Qwen/Qwen2.5-Coder-0.5B-Instruct"
    # ... customize here
)
```

### Model Size → Parallelism Map
In `batch_inference_pipeline.py`, the parallelism is auto-determined:

```python
parallelism_map: dict[str, int] = {
    "Qwen/Qwen2.5-0.5B-Instruct": 4,        # Small: 4 parallel
    "meta-llama/Llama-3.2-1B-Instruct": 2,  # Medium: 2 parallel
    "microsoft/Phi-3-mini-4k": 2,           # Medium: 2 parallel
    "Qwen/Qwen2.5-1.5B": 1,                 # Large: 1 parallel (CPU)
    "Qwen/Qwen2.5-3B": 1,                   # Large: 1 parallel
    "mistralai/Mistral-7B": 1,              # Very large: 1 parallel
}
```

Add new models as needed.

### Checkpoint Interval
In `batch_inference_pipeline.py`:

```python
checkpoint_interval: int = 1  # Save after every N examples
# Change to 5 or 10 for faster runs if disk I/O is bottleneck
```

### Retry Settings
```python
max_retries: int = 3            # Attempts before failure
retry_delay: float = 5.0        # Seconds between retries
timeout_per_example: float = 60.0  # Seconds per inference
```

---

## Output Structure

```
inference_output/
├── pipeline.log                          # Main log
├── manifest.json                         # Query deduplication
├── .checkpoints/
│   ├── text_generation_qwen....checkpoint.json
│   ├── code_generation_qwen....checkpoint.json
│   └── ... (one per task-model pair)
│
├── text_generation/
│   ├── text_generation_qwen_5_0_5b_instruct_results.csv
│   ├── manifest.json                    # Task-specific
│   └── logs/
│       └── text_generation_qwen....log
│
├── code_generation/
│   ├── code_generation_qwen....results.csv
│   ├── manifest.json
│   └── logs/
│
└── ... (one dir per task)
```

### Results CSV Format
```csv
example_id,output,model,timestamp,backend,success
example_0,"The AI system learns patterns...",Qwen/Qwen2.5-0.5B-Instruct,2024-03-18T10:30:45,ollama,True
example_1,"Error: timeout",Qwen/Qwen2.5-0.5B-Instruct,2024-03-18T10:30:50,ollama,False
```

### Checkpoint Format
```json
{
  "task": "text_generation",
  "model": "Qwen/Qwen2.5-0.5B-Instruct",
  "timestamp": "2024-03-18T10:45:30",
  "total_processed": 47,
  "total_errors": 2,
  "completed_example_ids": [
    "example_0",
    "example_1",
    "example_2",
    ...
  ],
  "last_error": "Timeout on example_23"
}
```

---

## Resumability Logic

### How Resume Works

1. **First Run**:
   - Creates checkpoint: `task_model.checkpoint.json`
   - Creates manifest: `manifest.json`
   - Processes all examples

2. **Interrupted** (e.g., power loss, manual stop):
   - Checkpoint saved with last completed example_id
   - Manifest has all completed queries

3. **Resume Run**:
   - Loads checkpoint
   - Loads manifest
   - Skips all examples in `completed_example_ids`
   - Continues from where it left off

4. **Query Deduplication**:
   - Hash of `task:model:example_id:text` stored in manifest
   - If same query run again (different task?), skips it
   - Prevents accidental re-running

---

## Monitoring

### Watch Logs in Real-Time
```bash
tail -f inference_output/pipeline.log

# Or per-task:
tail -f inference_output/text_generation/logs/text_generation_qwen....log
```

### Check Progress
```bash
# Total processed so far
wc -l inference_output/text_generation/text_generation_qwen_results.csv

# Last checkpoint status
cat inference_output/.checkpoints/text_generation_qwen.checkpoint.json | jq .
```

### Verify No Re-runs
```bash
# Check manifest - should match completed IDs
cat inference_output/manifest.json | jq 'keys | length'

# Should equal total examples processed
```

---

## Performance Tuning

### CPU Inference Speed
```bash
# Check current speed
tail -f inference_output/pipeline.log | grep "Processing"

# Typical speeds:
# - Qwen 0.5B:    2-3 sec/example
# - Llama 1B:     3-4 sec/example
# - Phi 3.5:      2-3 sec/example
# - Mistral 7B:   8-10 sec/example (CPU only)
```

### Optimize Model Quantization
For faster inference, use smaller quantization:

```bash
# Download 4-bit quantized (smaller, faster)
ollama pull qwen2.5:0.5b-q4_0

# Download 8-bit (slower, more accurate)
ollama pull qwen2.5:0.5b-q8_0
```

### Memory Usage
Ollama manages memory automatically:
```bash
# Monitor while running
watch -n 1 'ps aux | grep ollama | grep -v grep'

# Typical RAM per model:
# - 0.5B model:  ~1GB
# - 1B model:    ~2GB
# - 3B model:    ~4GB
# - 7B model:    ~8GB
```

---

## Troubleshooting

### "Ollama is not running"
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run pipeline
./run_batch_pipeline.sh
```

### "Model not found"
```bash
# Pull the model first
ollama pull qwen2.5:0.5b

# Verify available
ollama list
```

### "Connection refused"
```bash
# Ollama server not running or not on port 11434
netstat -an | grep 11434

# Restart:
killall ollama
ollama serve
```

### Out of Memory
```bash
# Use smaller quantization
ollama pull model:0.5b-q4_0

# Or reduce parallelism in script
parallelism_map["your_model"] = 1
```

### Stuck or Slow
```bash
# Check logs for errors
tail -100 inference_output/pipeline.log

# Check if Ollama is responsive
curl http://localhost:11434/api/tags

# Restart pipeline (will resume from checkpoint)
^C  # Stop current run
./run_batch_pipeline.sh --resume
```

---

## Example: Full Workflow

### Step 1: Prepare (Phase 1)
```bash
# Aggregate existing results
python3 << 'EOF'
import pandas as pd
from pathlib import Path

for task in ['text_generation', 'code_generation', 'maths']:
    df = pd.read_csv(f"{task}/rebin_results.csv")
    df = df.sample(min(75, len(df)))  # Sample 75 per task
    df.to_csv(f"{task}/sampled_75.csv", index=False)
    print(f"{task}: {len(df)} examples")
EOF
```

### Step 2: Start Ollama
```bash
ollama serve
# Keep terminal open
```

### Step 3: Run Pipeline (Phase 2)
```bash
# Terminal 2
chmod +x run_batch_pipeline.sh
./run_batch_pipeline.sh

# Runs all 8 tasks sequentially
# ~2-3 hours on CPU, auto-checkpoints every example
```

### Step 4: Monitor
```bash
# Terminal 3
tail -f inference_output/pipeline.log

# Or check individual tasks:
ls -lh inference_output/*/text_generation_*_results.csv
```

### Step 5: Resume (if interrupted)
```bash
# Just re-run, will auto-resume
./run_batch_pipeline.sh

# Or explicitly:
./run_batch_pipeline.sh --resume
```

### Step 6: Validation
```bash
# Check all tasks completed
ls inference_output/*/text_generation_*_results.csv

# Verify no re-runs happened
python3 << 'EOF'
import json
with open("inference_output/manifest.json") as f:
    manifest = json.load(f)
print(f"Total unique queries: {len(manifest)}")
EOF
```

---

## Summary

| Feature | Implemented |
|---------|-------------|
| CPU + Quantized | ✅ |
| Fixed model per job | ✅ |
| Parallelism by model size | ✅ |
| Load model once | ✅ |
| Auto-retry + logging | ✅ |
| Autosave every query | ✅ |
| Resume if interrupted | ✅ |
| No manual intervention | ✅ |
| Offline (Ollama) | ✅ |
| No re-running | ✅ |

**Ready to run. Just execute `./run_batch_pipeline.sh` and let it complete.**
