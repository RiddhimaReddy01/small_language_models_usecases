# Benchmark 75-Query Dataset

Complete benchmark results comparing 3 SLMs against the working Groq Llama baseline.

## Structure

```
benchmark_75/
├── classification/
│   ├── llama_llama-3.3-70b-versatile/
│   ├── phi3_mini/
│   ├── qwen2.5_1.5b/
│   └── tinyllama_1.1b/
├── code_generation/
├── information_extraction/
├── instruction_following/
├── maths/
├── retrieval_grounded/
├── summarization/
└── text_generation/
```

## Models

| Model | Type | Status |
|-------|------|--------|
| `llama_llama-3.3-70b-versatile` | Baseline (Groq API) | Complete |
| `phi3_mini` | SLM (Ollama) | 75 queries each task |
| `qwen2.5_1.5b` | SLM (Ollama) | 75 queries each task |
| `tinyllama_1.1b` | SLM (Ollama) | 75+ queries each task |

## Query Counts

| Task | Groq Llama | phi3:mini | qwen2.5:1.5b | tinyllama |
|------|------|-----------|--------------|-----------|
| classification | 75 | 75 | 75 | 171 |
| code_generation | 75 | 75 | 75 | 191 |
| information_extraction | 75 | 75 | 75 | 75 |
| instruction_following | 75 | 75 | 75 | 75 |
| maths | 75 | 75 | 75 | 168 |
| retrieval_grounded | 75 | 75 | 75 | 176 |
| summarization | 75 | 75 | 75 | 177 |
| text_generation | 75 | 75 | 75 | 188 |

## File Format

Each model directory contains:
- `outputs.jsonl` - Query results (one JSON object per line)
- `run_manifest.json` - Run metadata and configuration
- `logs/` - Execution logs
- `metadata/` - Dataset and hardware information
- `sddf_ready.csv` - SDDF analysis ready flag

## Load Data in Code

```python
from load_benchmark_data import load_benchmark_outputs

# Load classification results for phi3:mini
outputs = load_benchmark_outputs('classification', 'phi3_mini')
print(len(outputs))  # 75

# Access individual result
result = outputs[0]
print(result.keys())  # Task ID, model, response, metrics, etc.
```

## Setup Ollama Models

```bash
bash pull_ollama_models.sh
```

Or manually:
```bash
ollama pull phi3:mini
ollama pull qwen2.5:1.5b
ollama pull tinyllama:1.1b
```

## Running Inference

Use the benchmark data to evaluate new models against the baseline:

```python
from load_benchmark_data import load_benchmark_outputs, get_available_tasks

for task in get_available_tasks():
    baseline = load_benchmark_outputs(task, 'llama_llama-3.3-70b-versatile')
    # Compare against your model's results
```

