# Quick Start: Batch Inference Pipeline

## 3-Step Setup (10 minutes)

### 1. Install Ollama
```bash
# Download: https://ollama.ai
# Then pull models:
ollama pull qwen2.5:0.5b
ollama pull qwen2.5-coder:0.5b
ollama pull llama2:7b
ollama pull phi:latest
```

### 2. Start Ollama (Keep Running)
```bash
ollama serve
# Keep this terminal open
```

### 3. Run Pipeline
```bash
# Terminal 2:
chmod +x run_batch_pipeline.sh
./run_batch_pipeline.sh

# That's it!
# - Runs all 8 tasks automatically
# - Saves checkpoints after every example
# - Auto-resumes if interrupted
# - No manual intervention needed
```

---

## Monitoring

```bash
# Terminal 3: Watch progress
tail -f inference_output/pipeline.log

# Or check status:
ls -lh inference_output/*/text_generation_*_results.csv
```

---

## If Interrupted

```bash
# Just run again, will auto-resume from checkpoint:
./run_batch_pipeline.sh

# Or explicitly resume:
./run_batch_pipeline.sh --resume
```

---

## Expected Output

```
inference_output/
├── pipeline.log
├── manifest.json           # No re-runs
├── .checkpoints/           # Resume from here
│   ├── text_generation_*.checkpoint.json
│   └── ...
└── {task}/
    └── {task}_*_results.csv
```

---

## Timing

| Hardware | Time |
|----------|------|
| CPU (Laptop) | 1-2 hours |
| GPU (T4) | 15-30 min |

---

## That's All!

No configuration needed. Just run and it handles everything:
- ✅ Auto-checkpoints every query
- ✅ Deduplication (no re-runs)
- ✅ Error retry logic
- ✅ Resumable on interrupt
- ✅ Detailed logging
- ✅ Completely offline

**Questions? See `BATCH_PIPELINE_SETUP.md` for detailed docs.**
