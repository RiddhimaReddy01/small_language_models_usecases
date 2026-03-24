# SDDF Pipeline Overview

This document ties the theory in the requirements to the runnable code in `sddf/` and `src/routing/`. The goal is to show how the learned difficulty signals, capability/risk curves, and t thresholds flow into the primary routing matrix: model size vs risk first, then model size vs capability.

## 1. Difficulty vector (`sddf/difficulty.py`)
- Each query is represented by the six-dimensional signal
  \[
  d(x) = (n_{\text{in}}, H, \hat{R}, |\Gamma|, \tilde{a}, D),
  \]
  where token count, Shannon entropy, the reasoning proxy, constraint count, approximate parametric dependence, and dependency distance capture distinct failure modes.
- The [`DifficultyWeightLearner`](sddf/difficulty_weights.py) learns weights \(w_i\) for each feature via gradient descent on a capability-risk utility so that the weighted score best explains the downstream curves. The learner trains so that
  \[
  s_k(w) = \sum_i w_i \, d_i, \qquad U_k = \sigma(\alpha(s_k - \tau))\left[P_{\text{cap},k} - \lambda P_{\text{risk},k} - (U_{\text{LLM}} - \lambda R_{\text{LLM}})\right],
  \]
  maximizing the sum of \(U_k\) over bins.
- `annotate_dominant_dimension` computes these features, and `make_difficulty_bins` groups the scores (quantile or uniform) to define \(P(\text{bin}\mid \text{complexity})\). These bins get translated into soft probabilities \(P(\text{bin}_k \mid d)\) by `difficulty_to_bin_probabilities` in `src/routing/framework.py`, so new requests immediately inherit the bin-weighted curves.

## 2. Capability and risk curves (`src/routing/framework.py`)
- Capability per bin \(k\) is computed as \(P(\text{success}\mid \text{bin}_k)\) by aggregating per-model validation metrics stored under `tasks/<task>/results/metrics_summary_*.json` (QA accuracy, pass@k, constraint satisfaction, etc.).
- The expected capability for a difficulty vector \(d\) is
  \[
  E[\text{cap}\mid d] = \sum_k P(\text{bin}_k \mid d)\cdot P(\text{success}\mid \text{bin}_k).
  \]
- The risk sensitivity curve records semantic failures (using the failure taxonomy implemented in `sddf/failure_taxonomy.py` and its severity weights). Each bin contributes \(P(\text{failure}\mid \text{bin}_k)\).
- Expected risk becomes
  \[
  E[\text{risk}\mid d] = \sum_k P(\text{bin}_k \mid d)\cdot P(\text{failure}\mid \text{bin}_k).
  \]

## 3. Learned t thresholds and tipping points (`src/routing/production_router.py`)
- The production router performs gradient ascent on the capability-risk utility, seeking the tipping behavior (a spike + decline in capability and a mirrored risk uptick). It adjusts the coefficients and the thresholds \(\tau_\cap\) and \(\tau_\rho\) so the learned curve best matches the observed capability and risk per bin.
- `_detect_tau_cap` and `_detect_tau_risk` use Wilson score confidence intervals (`src/utils/stats.py::wilson_interval`) with min-sample gating to locate bins where the lower CI remains above the configured capability threshold or risk tolerance.
- The learned taus (stored in each `AnalysisResult`) define the two routing boundaries: the highest difficulty that remains risk-eligible (`tau_risk`) and the highest difficulty that remains capability-eligible (`tau_cap`).

## 4. Decision matrix (parameter count vs risk, then parameter count vs capability)
- Models in `AnalysisResult` are sorted by parameter count. The router applies the two-tier matrix per bin:
  1. **Risk tier**: select the smallest model satisfying \(E[\text{risk}] \le \tau_\rho\). If the risk tier fails, the router escalates to a larger SLM or falls back to the baseline LLM.
  2. **Capability tier**: from the risk-eligible set, pick the smallest model with \(E[\text{cap}] \ge \tau_\cap\). Even if risk is acceptable, failing the capability tier forces a fallback to the next model or the LLM.
- The gating in `sddf.gates` and `sddf.routing.learn_routing_thresholds` mirrors this logic: they count how often the SLM stays within difficulty/latency bounds, compute precision/recall, and steer routing accordingly.

## 5. Pareto frontier and operational metrics (`sddf/curves.py`)
- Each bin stores latency metadata (`latency_sec_slm`, `latency_sec_llm`) and derived ratios. `compute_ratio_curve` summarises the SLM/LLM capability ratio per difficulty while `smooth_ratio_curve` stabilises those ratios for tipping-point detection.
- The resulting curves feed into Pareto reasoning over:
  - **Task complexity** (difficulty bins learned in section 1)
  - **Accuracy / capability** (per-bin success metrics)
  - **Cost / latency** (per-bin latency rows, SLM vs LLM ratios)
- These Pareto summaries appear under `tasks/<task>/results/sddf/reports/` and guide the “complexity vs accuracy vs cost vs latency” discussion when choosing tiers. Updating a model run requires refreshing the artifacts in `data/02_sampling` and `data/03_complexity` so the Pareto summaries stay aligned with the learned curves.

## Tooling
- `tools/train_difficulty_weights.py` runs the gradient descent loop over bin features/curves so the weights keep improving as new data arrives.
- `src/routing/production_router.py` persists the learned taus and Pareto metadata in `AnalysisResult`, exports JSON policies, and powers the Phase 1 routing decisions described above.

Keep this document beside the code so the equations, learned weights, tau logic, and Pareto narrative stay synchronized with the implementation.
