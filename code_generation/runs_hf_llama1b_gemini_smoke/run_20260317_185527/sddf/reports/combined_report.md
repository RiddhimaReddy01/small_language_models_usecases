# Part A - Benchmark Setup

- Benchmark: `code_generation`
- Run path: `code_generation\runs_hf_llama1b_gemini_smoke\run_20260317_185527`

## Task Definition

```json
{
  "task": "code_generation",
  "datasets": [
    "HumanEval",
    "MBPP"
  ]
}
```

## Dataset and Sampling

```json
{
  "human_eval_sample": 1,
  "mbpp_sample": 1,
  "time_budget_minutes": 2,
  "execution_timeout_seconds": 10,
  "seed": 42,
  "prompt_variant": "default",
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
      "label": "Llama 3.2 1B (HF API)",
      "kind": "hf_api",
      "model_name": "meta-llama/Llama-3.2-1B-Instruct",
      "load_in_4bit": false,
      "use_chat_template": false,
      "api_key_env": "HF_TOKEN",
      "max_input_tokens": null,
      "input_cost_per_1k_tokens": 0.0,
      "output_cost_per_1k_tokens": 0.0,
      "extra": {}
    },
    {
      "label": "Gemini Flash",
      "kind": "gemini",
      "model_name": "gemini-2.5-flash",
      "load_in_4bit": false,
      "use_chat_template": false,
      "api_key_env": "GEMINI_API_KEY",
      "max_input_tokens": null,
      "input_cost_per_1k_tokens": 0.0,
      "output_cost_per_1k_tokens": 0.0,
      "extra": {}
    }
  ],
  "generation": {
    "temperature": 0.2,
    "max_new_tokens": 128,
    "min_new_tokens": 48,
    "top_p": 1.0,
    "seed": 42,
    "profile": "default",
    "adaptive_max_new_tokens": false
  }
}
```

## Metrics

```json
[
  {
    "model": "Llama 3.2 1B (HF API)",
    "model_name": "meta-llama/Llama-3.2-1B-Instruct",
    "time_budget_minutes": 2,
    "human_eval_attempted": 1,
    "mbpp_attempted": 1,
    "total_attempted": 2,
    "tasks_completed_in_budget": 2,
    "pass@1": 0.0,
    "syntax_error_rate": 0.0,
    "runtime_failure_rate": 0.5,
    "logical_failure_rate": 0.5,
    "reliability_score": 0.0,
    "self_consistency_score": null,
    "format_compliance": 1.0,
    "signature_compliance": 1.0,
    "instruction_adherence": 1.0,
    "deterministic_reproducibility": null,
    "unsafe_code_rate": 0.0,
    "avg_latency_seconds": 1.1961471999820787,
    "p95_latency_seconds": 1.3868362999637611,
    "tokens_per_second": 24.919317204387553,
    "peak_ram_gb": 0.0108795166015625,
    "avg_output_tokens": 26.5,
    "cost_per_request": 0.0
  },
  {
    "model": "Gemini Flash",
    "model_name": "gemini-2.5-flash",
    "time_budget_minutes": 2,
    "human_eval_attempted": 1,
    "mbpp_attempted": 1,
    "total_attempted": 2,
    "tasks_completed_in_budget": 2,
    "pass@1": 0.0,
    "syntax_error_rate": 1.0,
    "runtime_failure_rate": 0.0,
    "logical_failure_rate": 0.0,
    "reliability_score": 0.0,
    "self_consistency_score": null,
    "format_compliance": 0.0,
    "signature_compliance": 0.0,
    "instruction_adherence": 0.0,
    "deterministic_reproducibility": null,
    "unsafe_code_rate": 0.0,
    "avg_latency_seconds": 1.142901500017615,
    "p95_latency_seconds": 1.1583095000241883,
    "tokens_per_second": 5.250750567249648,
    "peak_ram_gb": 0.0,
    "avg_output_tokens": 6,
    "cost_per_request": 0.0
  }
]
```

## Raw Benchmark Results

```json
{
  "task_result_count": 4
}
```

# Part B - SDDF Analysis

- Benchmark: `code_generation`
- Run path: `code_generation\runs_hf_llama1b_gemini_smoke\run_20260317_185527`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `R_hat`: 4 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 2 rows
- Bin `nan` / `SLM`: 2 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Historical comparison

- Historical code-generation results suggest API baselines retain an advantage on non-trivial algorithmic tasks, while local SLMs only pass trivial tasks reliably.
- Because the saved artifacts are aggregate, this remains a directional comparison rather than a paired one.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred transition point

- Historical tipping signal: historical evidence suggests a sharp break once tasks move beyond trivial single-loop logic into algorithmic reasoning.
- Operational reading: local SLMs can sometimes handle trivial tasks, but non-trivial algorithms are still a strong escalation signal.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Historical uncertainty

- Historical sample size signal: `4` task results were saved.
- Uncertainty source: completed-task counts are unstable and some local runs were incomplete, so exact thresholds should be treated cautiously.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 4
- Invalid outputs: 2
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested gate

- accept SLM outputs only on trivial, low-reasoning tasks with passing tests
- escalate recursive, multi-structure, or benchmark-hard tasks by default
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred deployment stance

- Likely SDDF stance: LLM-preferred except for trivial code generation slices.
- Why: historical pass rates show the primary bottleneck is reasoning depth, not formatting.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested routing policy

- reserve SLMs for simple transformation or boilerplate tasks
- route algorithmic or benchmark-hard tasks directly to stronger models
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

