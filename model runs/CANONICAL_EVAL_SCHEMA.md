# Canonical Evaluation Schema

Each task evaluation should emit one run record per model tier in the canonical ladder.

## 1. Task Identity

- `task_name`
- `task_family`
- `dataset_name`
- `dataset_version`
- `sample_count`
- `run_id`
- `run_timestamp`

## 2. Model Identity

- `model_tier`
  - `SLM-0`
  - `SLM-1`
  - `SLM-2`
  - `BASELINE`
- `provider`
- `model_name`
- `parameter_class`
- `backend`
- `quantization`

## 3. Capability Metrics

Task-specific metrics should be recorded with names and values.

Examples:
- classification: `accuracy`, `macro_f1`, `weighted_f1`
- information extraction: `exact_match`, `micro_f1`, `macro_f1`
- summarization: `rouge1`, `rouge2`, `rougeL`
- text generation: task rubric / judge scores / constraint scores
- retrieval-grounded: `exact_match`, `token_f1`, `context_utilization`
- instruction following: `pass_rate`, `constraint_satisfaction`
- maths: `final_answer_accuracy`, `pass_at_k`, `majority_vote_accuracy`
- code generation: `pass_at_1`, `compile_rate`, `test_pass_rate`

Minimum required fields:
- `primary_metric_name`
- `primary_metric_value`
- `secondary_metrics`

## 4. Operational Metrics

- `avg_latency_sec`
- `p50_latency_sec`
- `p95_latency_sec`
- `throughput_qpm`
- `estimated_cost_per_query_usd`
- `estimated_total_cost_usd`
- `ram_gb`
- `vram_gb`
- `valid_output_rate`

## 5. Semantic Risk Metrics

- `semantic_weighted_risk`
- `quality_failure_rate`
- `failure_type_distribution`
- `critical_failure_rate`
- `abstain_rate`

Risk should prefer semantic failure labels when available, then quality shortfall, then invalid output fallback.

## 6. Model Settings

- `temperature`
- `top_p`
- `top_k`
- `max_output_tokens`
- `context_window`
- `seed`
- `stop_sequences`

## 7. Prompt Settings

- `system_prompt`
- `prompt_template`
- `few_shot_count`
- `few_shot_examples`
- `output_format_constraints`

## 8. Hardware / Runtime Settings

- `host_type`
- `cpu_name`
- `cpu_threads`
- `gpu_name`
- `gpu_count`
- `backend_runtime`
- `api_provider`
- `region`

## 9. SDDF Outputs

- `canonical_rows_path`
- `curve_plot_path`
- `part_a_report_path`
- `part_b_report_path`
- `combined_report_path`
- `tau_risk`
- `tau_cap`

## 10. Routing Outputs

- `risk_gate_pass`
- `capability_gate_pass`
- `selected_route`
- `recommended_operating_region`
- `fallback_model`

## 11. Audit / Reproducibility

- `prompt_config_path`
- `dataset_manifest_path`
- `hardware_manifest_path`
- `run_manifest_path`
- `notes`

## Deliverables

Every task should produce:
- one machine-readable run record per ladder model
- one aggregate comparison table across all ladder models
- SDDF artifacts for matched SLM vs baseline analysis
- routing decision outputs using `tau_risk` then `tau_cap`
