# Section 6 SDDF v3 Computation Results

## Core Equations

- Capability curve: $C_m(d)$
- Risk surface: $R_m(d)$
- Threshold rule: $\tau^* = \max d\;\text{s.t.}\;C_m(d)\ge \tau_{cap},\;R_m(d)\le \tau_{risk}$
- Fallback: minimum violation when no strict feasible $\tau$ exists.

## Split Strategy

Smita raw outputs are test-heavy, so a deterministic item-level 60/20/20 split was used to execute SDDF train/validation/test end-to-end from available artifacts.

## Per-Use-Case Best SLM vs LLM

| Use Case | Best SLM | Best SLM Accuracy | LLM Accuracy | Best SLM $\tau^*$ | Metric Mode |
|---|---|---:|---:|---:|---|
| UC1 | Mistral-7B | 0.8333333333333334 | 0.8333333333333334 | 3.85216872360328 | hard_label_proxy |
| UC2 | Gemma3-4B | 1.0 | 1.0 | 0.0 | hard_label_proxy |
| UC3 | Gemma3-4B | 0.8333333333333334 | 0.8333333333333334 | 4.058813890331201 | hard_label_proxy |
| UC4 | Gemma3-4B | 1.0 | 1.0 | 3.9698157824268097 | hard_label_proxy |
| UC5 | Llama-3.1-8B | 0.8333333333333334 | 0.8333333333333334 | 0.0 | hard_label_proxy |
| UC6 | Llama-3.1-8B | 0.6666666666666666 | 0.5 | 5.642054706834413 | hard_label_proxy |
| UC7 | Qwen2.5-7B | 0.5 | 0.5 | 12.0 | hard_label_proxy |
| UC8 | Gemma3-4B |  |  |  | generation_criteria_proxy |

## Notes

- Difficulty features were computed with `sddf/difficulty.py` from Riddhima's repo.
- Validation thresholds were computed with adaptive SDDF v3 logic in `sddf/validation_dynamic.py`.
- ROC-AUC, PR-AUC, Brier, and ECE are hard-label proxies because probability logits are not persisted in Smita raw outputs.
- UC8 is generation-focused; class-label metrics are not available in raw outputs, so generation criteria coverage proxy is used.