# Retrieval-Grounded QA Benchmark

Evaluates small language models (SLMs) on answering questions using supplied context passages. Tests whether models can produce answers grounded strictly in the provided context—critical for RAG (Retrieval-Augmented Generation) systems.

## Pipeline Overview

```
Data Ingestion → Model Load → Inference → Metrics → Results
     (dataset)      (HF/API)   (generate)  (EM,F1)   (JSON)
```

1. **Data ingestion**: Loads SQuAD or Natural Questions, samples N questions, truncates context.
2. **Model load**: Downloads from Hugging Face (SLMs) or uses API (Gemini).
3. **Inference**: Runs deterministic generation (temp=0) per question.
4. **Metrics**: Computes EM, F1, context utilization, hallucination rate.
5. **Results**: Writes `results/results.json` and per-model predictions.

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd Retrieval_grounded
pip install -r requirements.txt

# 2. Run benchmark (SLMs only, ~25–45 min on CPU)
python run.py

# 3. With Gemini baseline (optional)
cp .env.example .env   # Edit .env, add GEMINI_API_KEY
python run.py --baseline-gemini
```

## Hardware Requirements

| Spec | Minimum | Recommended (faster) |
|------|---------|----------------------|
| RAM | 8 GB | 16 GB+ |
| CPU | Any | Multi-core |
| GPU | Not required | CUDA-capable (auto-detected) |
| Disk | ~2 GB (models) | ~5 GB |

- **CPU**: All three SLMs run in ~25–45 min sequentially. Use `--device cuda` if you have a GPU.
- **GPU**: Much faster. Use `--workers 2` or `3` if you have enough VRAM (e.g. 8 GB+ per model).
- **Gemini**: API-only; no local compute. Requires `GEMINI_API_KEY`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | For `--baseline-gemini` | Get at [Google AI Studio](https://aistudio.google.com/apikey) |
| `HF_TOKEN` | Optional | Speeds up Hugging Face downloads |

Copy `.env.example` to `.env` and fill in values.

## Task Definition

- **Input**: Retrieved context passage + question  
- **Output**: Answer derived strictly from the context  
- **Focus**: Context comprehension and grounded answering (no reliance on internal knowledge)

## Datasets

| Dataset | Source | Size |
|---------|--------|------|
| **SQuAD** (default) | `rajpurkar/squad` | ~30 MB |
| **Natural Questions** | `LLukas22/nq-simplified` | ~138 MB |

Data is downloaded on first run via Hugging Face `datasets`.

## Models

| Model | Size | Backend |
|-------|------|---------|
| Qwen2.5-Coder 0.5B | 0.5B | Hugging Face |
| DeepSeek-Coder 1.3B | 1.3B | Hugging Face |
| Qwen2.5-Coder 1.5B | 1.5B | Hugging Face |
| Gemini 3.1 Flash Lite | API | Google AI |

## Usage

```bash
# Default: 30 questions, SQuAD, all three SLMs
python run.py

# GPU + parallel workers
python run.py --device cuda --workers 2

# Gemini only (fast, no model download)
python run.py --gemini-only

# Full run: SLMs + Gemini baseline
python run.py --baseline-gemini

# Custom dataset / questions
python run.py --dataset natural_questions --num_questions 50
python run.py --models Qwen/Qwen2.5-Coder-0.5B-Instruct  # Single model
```

### Run Scripts

```bash
# Unix / macOS
./run.sh              # SLMs + Gemini (if GEMINI_API_KEY set)
./run.sh quick        # Single model + Gemini

# Windows
run.bat               # SLMs only
run.bat gemini        # Gemini only
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--dataset` | squad | `squad`, `natural_questions`, or `nq` |
| `--num_questions` | 30 | Number of QA pairs |
| `--max_context_tokens` | 300 | Max context length |
| `--max_answer_tokens` | 10 | Max reference answer length |
| `--models` | (config) | Model IDs to evaluate |
| `--output_dir` | ./results | Output directory |
| `--device` | auto | `cpu`, `cuda`, or `auto` |
| `--workers` | 1 | Parallel workers (SLMs) |
| `--baseline-gemini` | off | Add Gemini API baseline |
| `--gemini-only` | off | Run only Gemini (skip SLMs) |
| `--gemini-concurrency` | 10 | Parallel Gemini API calls |

## Sampling Strategy (CPU-Friendly)

| Parameter | Value |
|-----------|-------|
| Questions | 30 |
| Context passages | 1 per question |
| Context length | ≤300 tokens |
| Answer length | ≤10 tokens |

Target runtime: ~25–45 min on CPU for all three models; ~3–5 min for Gemini only.

## Inference Settings

- **temperature**: 0.0
- **top_p**: 1.0
- **max_new_tokens**: 30
- **sampling**: disabled (greedy/deterministic)

## Metrics

### Capability Metrics

| Metric | Formula |
|--------|---------|
| **Exact Match (EM)** | Correct answers / Total questions |
| **F1 Score** | Token overlap between prediction and reference |
| **Context Utilization Rate (CUR)** | Answers grounded in context / Total answers |
| **Answer Length Accuracy** | Answers within ≤10 tokens / Total answers |

### Reliability Metrics

| Metric | Meaning |
|--------|---------|
| `hallucination_rate` | Answer not present in context |
| `unsupported_answer_rate` | Claim unsupported by context |
| `partial_answer_rate` | Incomplete answer (overlap but not exact) |

### Operational Metrics

| Metric | Description |
|--------|-------------|
| `latency_ms` | Time per inference |
| `tokens_per_sec` | Generation throughput |
| `memory_mb` | RAM usage |
| `input_tokens_avg` | Average context size |

## Output

- `results/results.json` — Aggregate metrics per model  
- `results/predictions_<model>.json` — Per-example predictions for analysis

## Prompt Template

```
Answer the question using only the information in the context.

Context:
{context}

Question:
{question}

Answer:
```
