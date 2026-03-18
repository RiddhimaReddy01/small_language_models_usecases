# Part A - Benchmark Setup

- Benchmark: `text_generation`
- Run path: `C:\Users\riddh\OneDrive\Desktop\SLM use cases\text_generation\results\runs\suite_20260315_000947`

## Task Definition

```json
{
  "task": "text_generation",
  "task_type": "samples"
}
```

## Dataset and Sampling

```json
{
  "task_type": "samples",
  "seed": 42,
  "repeats": 1
}
```

## Experimental Setup

```json
{
  "resolved_models": [
    {
      "model_name": "qwen-2.5-3b",
      "config": {
        "model_path": "models/qwen2.5-3b-instruct-q4_k_m.gguf",
        "description": "Alibaba Qwen 2.5 3B Instruct",
        "n_ctx": 4096,
        "n_threads": 4,
        "model_name": "qwen-2.5-3b"
      },
      "resolved_model_path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\models\\qwen2.5-3b-instruct-q4_k_m.gguf",
      "model_file": {
        "path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\models\\qwen2.5-3b-instruct-q4_k_m.gguf",
        "exists": true,
        "size_bytes": 2104932768,
        "sha256_prefix": "00a761a854977223da3a93cae937e32ab38dc0e997318f8ef270d2856f237310",
        "sha256_prefix_bytes": 1048576
      }
    },
    {
      "model_name": "phi-3.5-mini",
      "config": {
        "model_path": "models/Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "description": "Microsoft Phi-3.5 Mini Instruct",
        "n_ctx": 4096,
        "n_threads": 4,
        "model_name": "phi-3.5-mini"
      },
      "resolved_model_path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\models\\Phi-3.5-mini-instruct-Q4_K_M.gguf",
      "model_file": {
        "path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\models\\Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "exists": true,
        "size_bytes": 2393232672,
        "sha256_prefix": "12de553f7876ed5dd28cfa46edc9ca9dc4ea81b598d6e098cb4961a4168686f8",
        "sha256_prefix_bytes": 1048576
      }
    }
  ],
  "temperature": 0.7,
  "workers": 1,
  "gguf_engine": "llama_cpp"
}
```

## Metrics

```json
{
  "benchmark_summary_path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\suite_20260315_000947\\benchmark_summary.json",
  "metrics_tables_path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\suite_20260315_000947\\metrics_tables.md"
}
```

## Raw Benchmark Results

```json
{
  "raw_files": [
    "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\suite_20260315_000947\\qwen-2.5-3b.json",
    "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\suite_20260315_000947\\phi-3.5-mini.json"
  ],
  "example_count_per_run": 15
}
```

# Part B - SDDF Analysis

- Benchmark: `text_generation`
- Run path: `C:\Users\riddh\OneDrive\Desktop\SLM use cases\text_generation\results\runs\suite_20260315_000947`

## SDDF: Dominant Difficulty Dimension

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Difficulty Annotation + Binning

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Matched SLM vs LLM Analysis

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Capability Curve + Tipping Point

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Uncertainty Analysis

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Failure Taxonomy

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Quality Gate

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Deployment Zones

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

## Routing Policy

- Status: `unsupported`
- Reason: No SDDF archive found for this run.

Not enough evidence to render this section.

