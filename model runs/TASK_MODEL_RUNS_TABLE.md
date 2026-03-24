# Task Model Runs Table

This version includes numeric snapshots from the surviving artifacts, with canonical ladder slots normalized to:

- `SLM-0`: 0.5B tiny model
- `SLM-1`: Qwen 2B-class model
- `SLM-2`: Phi 3B-class model
- `BASELINE`: Groq-hosted LLM

Notes:
- Numbers are taken from the nearest surviving artifact for each task/slot.
- If an exact canonical slot is not preserved on disk, the table keeps the slot and shows the nearest archived evidence.
- `BASELINE` remains Groq in the canonical design; where the original Groq numeric artifact is no longer checked out, the table keeps the baseline slot and marks it as a removed baseline snapshot.

| Task | SLM-0 | SLM-1 | SLM-2 | BASELINE | Capability metrics | Operational metrics | Prompt / model / hardware settings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `classification` | canonical 0.5B slot; no clean numeric archive found | nearest evidence: `qwen2.5:1.5b` | nearest evidence: `phi3:mini` | canonical Groq baseline; no checked-out numeric snapshot | `phi3:mini`: SST-2 acc `1.000`, Emotion acc `0.667`, AG News acc `0.750`; macro-F1 `1.000/0.556/0.667` | `phi3:mini`: latency mean `5.520s / 1.330s / 2.495s`; throughput `0.181 / 0.751 / 0.401`; parse failure `0.0` | examples use `phi3:mini` and `qwen2.5:1.5b`; seed `42`; profile `fast15` |
| `maths` | canonical 0.5B slot; no surviving numeric snapshot | canonical Qwen 2B slot; no checked-out numeric snapshot | nearest evidence: `phi3_mini` | canonical Groq baseline; exact historical numeric artifact not checked out | `phi3_mini`: final answer acc `19.2%`, pass@3 `47.3%`, majority-vote acc `9.7%`; baseline snapshot: `38.3% / 76.5% / 32.8%` | `phi3_mini`: latency `28.41s`, throughput `2.11 qpm`; baseline snapshot latency `1.08s`, throughput `55.78 qpm` | metrics file preserves per-model capability/reliability/efficiency breakdown |
| `text_generation` | canonical 0.5B slot; no clean numeric archive found | nearest evidence: `qwen-2.5-3b` | nearest evidence: `phi-3.5-mini` | canonical Groq baseline; exact historical numeric artifact not checked out | no surviving aggregate score table in checked-out suite; numeric setup snapshot only: `15` examples per run | temperature `0.7`, workers `1`, context `4096`; Qwen file size `2,104,932,768` bytes; Phi file size `2,393,232,672` bytes | `llama_cpp`, seed `42`, GGUF paths recorded in suite manifest |
| `summarization` | canonical 0.5B slot | canonical Qwen 2B slot | nearest numeric SLM snapshot: `meta-llama/Llama-3.2-1B-Instruct` | canonical Groq baseline; exact historical numeric artifact not checked out | SLM snapshot: ROUGE-1 `0.281`, ROUGE-2 `0.106`, ROUGE-L `0.181`; baseline snapshot: `0.277 / 0.069 / 0.173` | SLM snapshot latency `0.763s`, tok/s `22.40`; baseline snapshot latency `0.583s`, tok/s `24.84`; hallucination `0.0` vs `0.2` | prompt: exactly one sentence, `12-20` words; max article tokens `400`; seed `42`; temp `0.0` |
| `information_extraction` | `Qwen2.5-0.5B-Instruct` | nearest archived Qwen mid-tier: `Qwen2.5-1.5B-Instruct` | canonical Phi 3B slot; no surviving IE phi snapshot | canonical Groq baseline; exact historical numeric artifact not checked out | SLM-0: macro-F1 `0.167`, micro-F1 `0.222`, exact match `0.000`; SLM-1: `0.025 / 0.042 / 0.000`; baseline snapshot: `0.188 / 0.300 / 0.000` | SLM-0 latency `14.59s`, throughput `4.11 docs/min`, invalid output `0.50`; SLM-1 latency `17.45s`, throughput `3.44`; baseline snapshot latency `0.857s`, throughput `70.04` | backend `ollama`, temperature `0.0`, output dir `outputs`, Qwen 0.5B model id preserved |
| `retrieval_grounded` | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | canonical Qwen 2B slot | canonical Phi 3B slot; no surviving checked-out phi snapshot | canonical Groq baseline; exact historical numeric artifact not checked out | SLM-0: exact match `66.67`, F1 `71.26`, context util `96.67`, answer-length acc `86.67`; baseline snapshot: `63.33 / 77.78 / 83.33 / 90.00` | SLM-0 latency `5534ms`, p95 `8079ms`, tok/s `4.23`, hallucination `3.33%`; baseline snapshot latency `829ms`, p95 `1056ms`, tok/s `6.40`, hallucination `16.67%` | config records model `Qwen/Qwen2.5-Coder-0.5B-Instruct`, temperature `0.0`, output dir `outputs_qwen05b_cpu` |
| `instruction_following` | `Qwen/Qwen2.5-Coder-0.5B` | canonical Qwen 2B slot; nearest checked-out mid-tier is DeepSeek 1.3B, not exact Qwen 2B | canonical Phi 3B slot | canonical Groq baseline; exact historical numeric artifact not checked out | SLM-0: pass rate `0.40`, constraint satisfaction `0.40`, format compliance `0.00`; baseline snapshot: pass rate `1.00` | SLM-0 avg latency `17.89s`, tok/s `4.79`; nearest mid-tier artifact `42.83s`; baseline snapshot latency `0.98s` | results preserve per-prompt traces for `20` prompts on SLMs and `13` prompts on baseline |
| `code_generation` | `Qwen2.5-Coder-0.5B-Instruct` | nearest archived Qwen mid-tier: `Qwen2.5-Coder-1.5B-Instruct` | nearest archived phi evidence: `phi3:mini` config; no checked-out phi numeric summary | canonical Groq baseline; exact historical numeric artifact not checked out | SLM-0: pass@1 `0.50`; SLM-1 nearest numeric: pass@1 `1.00`; baseline snapshot: pass@1 `0.15` | SLM-0 latency `7.40s`, tok/s `7.70`; SLM-1 latency `91.05s`, tok/s `0.60`; baseline snapshot latency `0.665s`, tok/s `110.14` | prompt variants `default` / `fast_cpu`; temperature `0.4` and `0.15`; configs preserve model names and runtimes |

## Calculation Basis

- Classification numbers come from `tasks/classification/results/metrics_summary_1773488616.json`.
- Maths numbers come from `tasks/maths/results/reports/benchmark_metrics.json`.
- Summarization numbers come from `tasks/Summarization/outputs/hf_llama1b_gemini_pair/summarization_summary.json`.
- Information extraction numbers come from the archived `summary.json` files under `tasks/Information Extraction/outputs/`.
- Retrieval-grounded numbers come from `tasks/Retrieval_grounded/outputs_qwen05b_arrow30/metrics/results.json` and `tasks/Retrieval_grounded/outputs_gemini_flash_arrow30/metrics/results.json`.
- Instruction-following numbers come from `tasks/instruction_following/results/results_detailed.json`.
- Code-generation numbers come from `tasks/code_generation/runs/run_20260314_031256/summary.json` and `tasks/code_generation/runs/run_20260314_043918/summary.json`.
