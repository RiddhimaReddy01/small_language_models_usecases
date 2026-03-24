# SDDF Pipeline Overview

This document captures the learned flow described in the framework and the formulas used to power capability, risk, tipping points, and Pareto analysis.

## 1. Difficulty vector (framework/sddf/difficulty.py)
- Each query is represented by the six-dimensional signal
  \[
d(x) = (n_{\text{in}}, H, \hat{R}, |\Gamma|, \tilde{a}, D),
\]
  where tokens, entropy, reasoning proxy, constraint count, parametric dependence, and dependency distance each capture a different failure mode.
- Those features are combined via learned weights that are trained end-to-end: the gradient-ascent utility in `src/routing/production_router.py::_auto_thresholds_from_curves` adjusts each coefficient so the aggregated difficulty score best explains the subsequent capability/risk curves.
- `make_difficulty_bins()` quantiles/uniformly bins the score to define \(P(\text{bin}\mid\text{complexity})\); `difficulty_to_bin_probabilities()` then returns soft assignments \(P(\text{bin}\mid d)\) that translate new inputs into the bin-weighted curves.

## 2. Capability and risk curves (src/routing/framework.py)
- Capability per bin \(k\): \(P(\text{success}\mid\text{bin}_k)\), derived from task-specific metrics held in `tasks/<task>/results/metrics_summary_*.json`.
- Expected capability \(E[\text{cap}\mid d]=\sum_k P(\text{bin}_k\mid d)\cdot P(\text{success}\mid \text{bin}_k)\).
- Risk per bin \(k\): semantic failure rate \(P(\text{failure}\mid \text{bin}_k)\) using the failure taxonomy in `framework/sddf/reporting.py`.
- Expected risk \(E[\text{risk}\mid d]=\sum_k P(\text{bin}_k\mid d)\cdot P(\text{failure}\mid \text{bin}_k)\).

## 3. Learned τ thresholds and tipping points
- `src/routing/production_router.py` performs gradient ascent on the utility:
  \[
U(\tau_c,\tau_r) = \sum_k w_k \left[\text{accept}_{k} (P_{\text{cap},k}-\lambda P_{\text{risk},k}) + (1-\text{accept}_k)(\text{LLM}_{\text{cap}}-\lambda\text{LLM}_{\text{risk}})\right]
\]
  where \(\text{accept}_k = \sigma(\alpha(P_{\text{cap},k}-\tau_c))\sigma(\alpha(\tau_r-P_{\text{risk},k}))\), \(\alpha\) is steepness, \(\lambda\) trades off risk, and \(w_k\) are bin counts.
- `_detect_tau_cap` and `_detect_tau_risk` monitor capability and risk CIs to detect sudden drops/spikes (tipping behavior).

## 4. Decision matrix
- Models are ordered by size/parameter count in `AnalysisResult`.
- Per bin, the router picks the smallest model that satisfies:
  \[
E[\text{risk}] \le \tau_{\rho},\quad E[\text{cap}] \ge \tau_{\cap}.
\]
- If the risk condition fails, escalation moves to a larger SLM or the baseline LLM; if capability fails, fallback occurs even with acceptable risk, producing the two-tier matrix (size vs risk, then size vs capability).

## 5. Pareto frontier
- `framework/sddf/curves.py` stores latency/cost metadata (`latency_sec_*`) for each bin, enabling Pareto charts that span difficulty (complexity) vs accuracy vs cost/latency (previously summarized under `outputs/analysis/PARETO_FRONTIER_SUMMARY.md` and each task's SDDF reports).

This guide should be kept alongside the code so the equations and learned logic stay in sync with the implementation.
