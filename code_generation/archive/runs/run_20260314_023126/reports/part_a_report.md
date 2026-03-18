# Part A - Benchmark Setup

- Benchmark: `code_generation`
- Run path: `c:\Users\riddh\OneDrive\Desktop\SLM use cases\code_generation\archive\runs\run_20260314_023126`

## Task Definition

```json
{
  "task": "code_generation",
  "datasets": [
    "MBPP"
  ]
}
```

## Dataset and Sampling

```json
{
  "human_eval_sample": 0,
  "mbpp_sample": 2,
  "time_budget_minutes": 3,
  "execution_timeout_seconds": 3,
  "seed": 456,
  "prompt_variant": "fast_cpu",
  "generations_per_task": 1,
  "reproducibility_retries": 0,
  "blocked_imports": [
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "ftplib",
    "telnetlib",
    "shutil"
  ],
  "blocked_calls": [
    "os.system",
    "os.remove",
    "os.rmdir",
    "os.unlink",
    "os.removedirs",
    "shutil.rmtree",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "socket.socket",
    "requests.get",
    "requests.post",
    "urllib.request.urlopen"
  ]
}
```

## Experimental Setup

```json
{
  "models": [
    {
      "label": "SmolLM2 360M (Transformers Tiny)",
      "kind": "hf_local",
      "model_name": "HuggingFaceTB/SmolLM2-360M-Instruct",
      "load_in_4bit": false,
      "use_chat_template": true,
      "api_key_env": "GEMINI_API_KEY",
      "max_input_tokens": null,
      "input_cost_per_1k_tokens": 0.0,
      "output_cost_per_1k_tokens": 0.0,
      "extra": {}
    }
  ],
  "generation": {
    "temperature": 0.15,
    "max_new_tokens": 96,
    "min_new_tokens": 48,
    "top_p": 0.9,
    "seed": 456,
    "profile": "fast_cpu",
    "adaptive_max_new_tokens": true
  }
}
```

## Metrics

```json
[
  {
    "model": "SmolLM2 360M (Transformers Tiny)",
    "model_name": "HuggingFaceTB/SmolLM2-360M-Instruct",
    "time_budget_minutes": 3,
    "human_eval_attempted": 0,
    "mbpp_attempted": 2,
    "total_attempted": 2,
    "tasks_completed_in_budget": 2,
    "pass@1": 1.0,
    "syntax_error_rate": 0.0,
    "runtime_failure_rate": 0.0,
    "logical_failure_rate": 0.0,
    "reliability_score": 1.0,
    "self_consistency_score": null,
    "format_compliance": 1.0,
    "signature_compliance": 1.0,
    "instruction_adherence": 1.0,
    "deterministic_reproducibility": null,
    "unsafe_code_rate": 0.0,
    "avg_latency_seconds": 5.698205250000228,
    "p95_latency_seconds": 5.929776900000434,
    "tokens_per_second": 8.104664843459929,
    "peak_ram_gb": 0.012638092041015625,
    "avg_output_tokens": 45,
    "cost_per_request": 0.0
  }
]
```

## Raw Benchmark Results

```json
{
  "task_result_count": 2
}
```
