# Benchmark 2024: Official Datasets for SDDF Training
**Complete reference for all 8 task families**

---

## Executive Summary

**benchmark_2024** consolidated official open-source datasets into a unified 75-query interface per task family, stratified by difficulty. This document maps each task to its original official dataset(s).

| Task | Official Dataset(s) | Size | HuggingFace | Download |
|---|---|---|---|---|
| **Maths** | GSM8K + MATH + SVAMP | 20.7K | ✅ | Below |
| **Classification** | Multiple sources* | ~75 | ✅ | Below |
| **Information Extraction** | SROIE | ~75 | ✅ | Below |
| **Retrieval Grounded** | SQuAD + NQ | ~30-138 MB | ✅ | Below |
| **Code Generation** | HumanEval + MBPP | ~164 | ✅ | Below |
| **Instruction Following** | Enterprise gold sets | ~75 | ❌ | Internal |
| **Summarization** | CNN/DailyMail or SamSum | ~30-90K | ✅ | Below |
| **Text Generation** | Enterprise gold sets | ~75 | ❌ | Internal |

---

## 1. MATHS

### Official Datasets

#### **GSM8K (Grade School Math 8K)**
- **Source**: OpenAI
- **HuggingFace**: `openai/gsm8k`
- **Size**: 7,473 training problems
- **Task**: Multi-step arithmetic word problems
- **Download**:
```bash
# Via HuggingFace datasets library
from datasets import load_dataset
gsm8k = load_dataset("openai/gsm8k", "main")  # 7,473 problems

# Via direct download
wget https://huggingface.co/datasets/openai/gsm8k/raw/main/data/train.jsonl
```
- **Format**: JSONL with `question` and `answer` fields
- **License**: MIT

#### **MATH (MATH competition problems)**
- **Source**: DeepMind/Meta
- **HuggingFace**: `heegyu/MATH_Subset`
- **Size**: 12,500 problems
- **Task**: High school and college math (AMC, AIME, etc.)
- **Download**:
```bash
from datasets import load_dataset
math_dataset = load_dataset("heegyu/MATH_Subset")
```
- **Format**: JSONL with problem, solution, difficulty
- **License**: CC-BY-4.0

#### **SVAMP (Simulated World Arithmetic Problems)**
- **Source**: Patel et al., 2021
- **HuggingFace**: `svamp`
- **Size**: 700 problems
- **Task**: Arithmetic word problems (paraphrases of existing datasets)
- **Download**:
```bash
from datasets import load_dataset
svamp = load_dataset("svamp")
```
- **Format**: JSONL
- **License**: CC-BY-4.0

### Benchmark 2024 Processing
- **Combined size**: 7,473 + 12,500 + 700 = **20,673 problems**
- **Sampling**: Stratified by difficulty (5 quantile bins)
- **Per-task per-model**: **75 queries** (15 per difficulty bin)
- **Total maths samples**: 75 × 4 models = 300 raw outputs

---

## 2. CLASSIFICATION

### Official Dataset Sources
Classification used curated public sentiment/categorization datasets:

#### **Possible Sources** (based on task requirements):
- **AG News** (topic classification, 4 classes)
  - HuggingFace: `ag_news`
  - Size: 120K articles
  - Download: `load_dataset("ag_news")`

- **DBpedia** (entity classification, 14 classes)
  - HuggingFace: `dbpedia_14`
  - Size: 630K texts
  - Download: `load_dataset("dbpedia_14")`

- **IMDB** (sentiment, 2 classes)
  - HuggingFace: `imdb`
  - Size: 100K reviews
  - Download: `load_dataset("imdb")`

- **Yahoo Answers** (topic classification, 10 classes)
  - HuggingFace: `yahoo_answers_qa`
  - Download: `load_dataset("yahoo_answers_qa")`

### Benchmark 2024 Processing
- **Combined**: Multiple classification datasets
- **Per-task per-model**: **75 queries**
- **Stratification**: 5 difficulty bins (15 per bin)
- **Schema**: `{text, label, difficulty}`

---

## 3. INFORMATION EXTRACTION

### Official Dataset

#### **SROIE (Scanned Receipts OCR Information Extraction)**
- **Source**: ICDAR 2019 Robust Reading Challenge
- **Task**: Extract fields from receipt images (vendor, date, total, items)
- **Size**: ~1,000 training documents
- **Download**: 
```bash
# Via HuggingFace
from datasets import load_dataset
sroie = load_dataset("huggingface/sroie")

# Or direct from ICDAR
# https://rrc.cvc.uab.es/?ch=13
```
- **Format**: OCR text + JSON labels (vendor_name, invoice_date, total_amount, tax_amount, line_items)
- **License**: CC-BY-4.0 (for HF version)
- **Fields Extracted**:
  - `vendor_name`
  - `invoice_date`
  - `invoice_number`
  - `total_amount`
  - `tax_amount`
  - `line_item_count`

### Benchmark 2024 Processing
- **Sample size**: ~75 documents per model
- **Stratification**: 5 difficulty bins (15 per bin)
- **Difficulty markers**: 
  - Easy: clear labels, standard format
  - Medium: ambiguous fields, non-standard dates
  - Hard: abbreviations, footer references, multi-page

---

## 4. RETRIEVAL GROUNDED

### Official Datasets

#### **SQuAD (Stanford Question Answering Dataset)**
- **Source**: Stanford University
- **HuggingFace**: `rajpurkar/squad`
- **Size**: ~100K questions on Wikipedia passages
- **Download**:
```bash
from datasets import load_dataset
squad = load_dataset("rajpurkar/squad")  # v1.1

# Version 2.0 with unanswerable questions
squad_v2 = load_dataset("rajpurkar/squad", "squad_v2")
```
- **Format**: 
  ```json
  {
    "context": "Wikipedia passage text...",
    "question": "Who was...?",
    "answers": {"text": ["answer"], "answer_start": [123]}
  }
  ```
- **Metrics**: Exact Match (EM), F1 Score
- **License**: CC-BY-SA-4.0

#### **Natural Questions (NQ)**
- **Source**: Google AI
- **HuggingFace**: `LLukas22/nq-simplified`
- **Size**: ~307K questions on Wikipedia passages
- **Download**:
```bash
from datasets import load_dataset
nq = load_dataset("LLukas22/nq-simplified")  # Simplified version
```
- **Format**: Similar to SQuAD
- **Difficulty**: More natural questions (from real search logs)
- **License**: CC-BY-SA-3.0

### Benchmark 2024 Processing
- **Combined**: SQuAD + Natural Questions
- **Per-task per-model**: **75 queries**
- **Context truncation**: Limited to test model grounding ability
- **Metrics**: EM, F1, hallucination rate
- **Stratification**: 5 difficulty bins

---

## 5. CODE GENERATION

### Official Datasets

#### **HumanEval (OpenAI)**
- **Source**: OpenAI
- **Size**: 164 problems
- **Task**: Generate Python functions from docstrings
- **Download**:
```bash
# Via HuggingFace
from datasets import load_dataset
humaneval = load_dataset("openai_humaneval")

# Or direct from GitHub
# https://github.com/openai/human-eval
```
- **Format**: Python function signatures + docstrings + test cases
- **Evaluation**: `pass@1`, `pass@10` (code execution)
- **License**: MIT

#### **MBPP (Mostly Basic Programming Problems)**
- **Source**: Google
- **Size**: 1,000 problems
- **Task**: Generate Python functions from natural language descriptions
- **Download**:
```bash
from datasets import load_dataset
mbpp = load_dataset("google/mbpp")  # Full version

# Or sanitized version
mbpp_sanitized = load_dataset("mbpp")
```
- **Format**: Problem description → Python code
- **Evaluation**: Test case execution
- **License**: CC-BY-4.0

### Benchmark 2024 Processing
- **Combined**: HumanEval + MBPP
- **Per-task per-model**: **75 problems**
- **Stratification**: 5 difficulty bins
  - Easy: Simple functions (string/list ops)
  - Medium: Multi-step logic
  - Hard: Algorithmic reasoning
- **Metrics**: Pass@1, correctness, time-to-completion

---

## 6. SUMMARIZATION

### Official Datasets

#### **CNN/DailyMail**
- **Source**: DeepMind
- **HuggingFace**: `cnn_dailymail`
- **Size**: ~300K news articles
- **Task**: Generate abstractive summaries of news articles
- **Download**:
```bash
from datasets import load_dataset
cnn_dm = load_dataset("cnn_dailymail", "3.0.0")
```
- **Format**: 
  ```json
  {
    "article": "Full article text...",
    "highlights": "Summary bullet points\n...",
    "id": "article_id"
  }
  ```
- **Metrics**: ROUGE (ROUGE-1, ROUGE-2, ROUGE-L)
- **License**: Custom (DeepMind)

#### **SamSum (Alternative)**
- **Source**: Samsung Electronics / KLUE
- **HuggingFace**: `samsum`
- **Size**: ~16K dialogue summaries
- **Task**: Summarize conversations
- **Download**:
```bash
from datasets import load_dataset
samsum = load_dataset("samsum")
```
- **Format**: Dialogue → abstractive summary
- **Metrics**: ROUGE, BLEU
- **License**: CC-BY-4.0

### Benchmark 2024 Processing
- **Selected**: CNN/DailyMail or SamSum
- **Per-task per-model**: **75 documents**
- **Stratification**: 5 difficulty bins
  - Easy: Simple articles, clear main points
  - Medium: Multi-topic, implicit connections
  - Hard: Technical articles, nuanced summaries
- **Metrics**: ROUGE-like match, factuality

---

## 7. INSTRUCTION FOLLOWING

### Official Dataset Source
**Enterprise Gold Sets** (synthetically created, not from public benchmarks)

Instruction following used **internally created test cases** designed to test:
- Strict format compliance
- Constraint satisfaction
- Policy adherence
- Multi-step instructions

### Sample Structure
```json
{
  "id": "IF_001",
  "task": "instruction_following",
  "prompt": "Follow these steps exactly: 1) ... 2) ... 3) ...",
  "expected_format": "yaml|json|plain_text",
  "constraints": ["no_profanity", "max_length_500", "cite_sources"],
  "correct_output": "...",
  "difficulty": "easy|medium|hard"
}
```

### Benchmark 2024 Processing
- **Source**: Internal construction
- **Per-task per-model**: **75 instructions**
- **No official public dataset reference**
- **Stratification**: 5 difficulty bins

---

## 8. TEXT GENERATION

### Official Dataset Source
**Enterprise Gold Sets** (synthetically created)

Text generation used **internally created prompts** designed to test:
- Policy-compliant response generation
- Tone and clarity
- Customer-facing communication
- Action item clarity

### Sample Structure
```json
{
  "id": "TG_001",
  "task": "text_generation",
  "prompt": "Generate a customer service response to: [complaint]",
  "constraints": ["professional_tone", "acknowledge_concern", "provide_action"],
  "expected_outcome": "Polite, actionable response",
  "difficulty": "easy|medium|hard"
}
```

### Benchmark 2024 Processing
- **Source**: Internal construction
- **Per-task per-model**: **75 prompts**
- **No official public dataset reference**
- **Stratification**: 5 difficulty bins

---

## Pipeline: Official Datasets → SDDF Training

```
Official Datasets (March 2024)
├─ Maths: GSM8K (7,473) + MATH (12,500) + SVAMP (700)
├─ Classification: AG News, DBpedia, IMDB, Yahoo Answers
├─ Information Extraction: SROIE (1,000)
├─ Retrieval Grounded: SQuAD (100K) + NQ (307K)
├─ Code Generation: HumanEval (164) + MBPP (1,000)
├─ Instruction Following: Internal gold sets
├─ Summarization: CNN/DailyMail (300K)
└─ Text Generation: Internal gold sets
    ↓
    Feature Extraction: 19 difficulty features per sample
    ↓
    Stratified Sampling: seed=42, quantile(5 difficulty bins)
    ↓
    Per-Bin Stratification: 15 samples × 5 bins = 75 per task per model
    ↓
    dataset_manifest.json: Records source, seed, binning rule
    ↓
    model_runs/benchmark_75/
    (75 queries × 4 models × 8 tasks = 2,400 raw outputs)
    ↓
    SDDF Training Processing:
    ├─ Deduplicate common samples across 3 SLM models
    ├─ 60:20:20 train/val/test split (seed=42)
    └─ Result: ~250 common samples per task
        → model_runs/sddf_training_splits/
```

---

## Download All Official Datasets

### Quick Reference (HuggingFace Datasets)

```python
from datasets import load_dataset

# Maths
gsm8k = load_dataset("openai/gsm8k", "main")
math = load_dataset("heegyu/MATH_Subset")
svamp = load_dataset("svamp")

# Classification
ag_news = load_dataset("ag_news")
dbpedia = load_dataset("dbpedia_14")
imdb = load_dataset("imdb")

# Information Extraction
sroie = load_dataset("huggingface/sroie")

# Retrieval Grounded
squad = load_dataset("rajpurkar/squad")
nq = load_dataset("LLukas22/nq-simplified")

# Code Generation
humaneval = load_dataset("openai_humaneval")
mbpp = load_dataset("google/mbpp")

# Summarization
cnn_dm = load_dataset("cnn_dailymail", "3.0.0")
# OR
samsum = load_dataset("samsum")

# Instruction Following & Text Generation
# No public datasets — use internal gold sets
```

---

## Metadata: dataset_manifest.json

Each task run recorded:

```json
{
  "task": "classification",
  "source_dataset": "benchmark_2024",
  "selection_method": "stratified_by_difficulty",
  "binning_rule": "quantile(5)",
  "seed": 42,
  "target_per_bin": {
    "0": 15,
    "1": 15,
    "2": 15,
    "3": 15,
    "4": 15
  },
  "samples_included": {
    "0": ["0", "1", "2", ..., "14"],
    "1": ["15", "16", ..., "29"],
    ...
  },
  "timestamp_created": "2026-03-18T11:48:55.845927"
}
```

Location: `model_runs/benchmark_75/{task}/{model}/metadata/dataset_manifest.json`

---

## Summary Table

| Task | Dataset | Size | Official Benchmark | Split |
|---|---|---|---|---|
| **Maths** | GSM8K + MATH + SVAMP | 20.7K | ✅ OpenAI/DeepMind | 75 per model |
| **Classification** | Multiple (AG News, DBpedia, etc.) | ~50-120K | ✅ HuggingFace | 75 per model |
| **Information Extraction** | SROIE | ~1K | ✅ ICDAR 2019 | 75 per model |
| **Retrieval Grounded** | SQuAD + NQ | ~400K | ✅ Stanford/Google | 75 per model |
| **Code Generation** | HumanEval + MBPP | 1.2K | ✅ OpenAI/Google | 75 per model |
| **Instruction Following** | Internal gold sets | ~75 | ❌ Internal | 75 per model |
| **Summarization** | CNN/DailyMail | ~300K | ✅ DeepMind | 75 per model |
| **Text Generation** | Internal gold sets | ~75 | ❌ Internal | 75 per model |

---

## Key Dates

- **March 14, 2026**: Individual task benchmarks created (8 separate implementations)
- **March 18, 2026**: benchmark_2024 unified all tasks (consolidated pipeline)
- **March 24, 2026**: Benchmark 75 completed (75 queries per task per model)
- **April 9-18, 2026**: SDDF processing (deduplicate + split)
- **Current**: SDDF training dataset in `model_runs/sddf_training_splits/`

---

## References

- **OpenAI GSM8K**: https://github.com/openai/gsm8k
- **MATH Dataset**: https://github.com/hendrycks/math
- **SROIE**: https://rrc.cvc.uab.es/?ch=13
- **SQuAD**: https://rajpurkar.github.io/SQuAD-explorer/
- **Natural Questions**: https://ai.google.com/research/natural-questions
- **HumanEval**: https://github.com/openai/human-eval
- **MBPP**: https://huggingface.co/datasets/google/mbpp
- **CNN/DailyMail**: https://github.com/abisee/cnn-dailymail
- **HuggingFace Datasets**: https://huggingface.co/datasets
