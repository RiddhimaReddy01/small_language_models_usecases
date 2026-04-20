# Appendix E-F-I-J

## Appendix E. Formal Optimization Problem

### E.1 SDDF Validation Problem (continuous threshold form)

For task family \(f\), model \(m\), and difficulty threshold \(\tau\), the operational threshold selection implemented in `repos/small_language_models_usecases/sddf/validation_dynamic.py` can be written as:

$$
\max_{\tau \in \mathcal{T}}\; \tau
$$

subject to

$$
\hat C_{m,f}(\tau) \ge c^{\mathrm{dyn}}_{m,f}, \qquad \hat R_{m,f}(\tau) \le r^{\mathrm{dyn}}_{m,f}
$$

where \(\hat C_{m,f}(\tau)\) and \(\hat R_{m,f}(\tau)\) are empirical capability/risk over samples with difficulty score \(d \le \tau\), and dynamic targets are:

$$
c^{\mathrm{dyn}}_{m,f} = \mathrm{clip}(\min(c^{\mathrm{static}}, C^{\mathrm{base}}_{m,f}-\Delta_c), c_{\min}, c_{\max})
$$

$$
r^{\mathrm{dyn}}_{m,f} = \mathrm{clip}(\max(r^{\mathrm{static}}, R^{\mathrm{base}}_{m,f}+\Delta_r), r_{\min}, r_{\max})
$$

with defaults in code: \(\Delta_c=0.05\), \(\Delta_r=0.05\).

### E.2 Infeasible-case fallback (minimum violation)

If no \(\tau\) satisfies both constraints, SDDF uses a fallback optimizer:

$$
\tau^* = \arg\min_{\tau \in \mathcal{T}} V(\tau), \quad
V(\tau)=\max(0,c^{\mathrm{dyn}}_{m,f}-\hat C_{m,f}(\tau)) + \max(0,\hat R_{m,f}(\tau)-r^{\mathrm{dyn}}_{m,f})
$$

Tie-breakers in code are lexicographic: lower risk, higher capability, larger \(\tau\).

### E.3 Adaptive percentile variant

In adaptive mode (`find_operational_tau_adaptive`), targets are percentile-derived:

$$
c^{\mathrm{target}} = Q_p\left(\{\hat C_{m,f}(\tau):\tau\in\mathcal{T}\}\right),
\qquad
r^{\mathrm{target}} = Q_q\left(\{\hat R_{m,f}(\tau):\tau\in\mathcal{T}\}\right)
$$

then choose max feasible \(\tau\), else minimum-violation fallback.

### E.4 S3 policy optimization layer and bridge constraint

From `repos/small_language_models_usecases/sddf/s3_framework.py`:

1. Compute weighted score

$$
S3 = \left(\frac{\sum_i w_i d_i}{\sum_i 5w_i}\right)\cdot 5
$$

2. Apply hard/flag gate constraints before tier assignment.

3. Map to tier with boundaries \((\tau_1,\tau_2)=(3.2,4.0)\).

4. Bridge to runtime route limit

$$
\tau_{\mathrm{route}} = \min(\tau_{\mathrm{risk}},\tau_{\mathrm{cap}})
$$

### E.5 Concrete optimization/control parameters observed in artifacts

From `repos/small_language_models_usecases/model_runs/classification/sddf/routing_policy.json`:

| Parameter | Value |
|---|---:|
| Threshold method | `continuous_isotonic_knn_beta` |
| Policy capability threshold | 0.8 |
| Policy risk threshold | 0.2 |
| Wilson confidence level | 0.9 |
| Tau bootstrap draws | 200 |
| Conservative percentile | 10.0 |
| Utility coefficients \((\alpha,\beta,\gamma)\) | (1.0, 0.25, 1.0) |

## Appendix F. Theoretical Properties

### F.1 Monotonic curve regularization

`build_difficulty_curves` in `validation_dynamic.py` applies isotonic regression:

- capability curve forced monotone non-decreasing in difficulty-bin index,
- risk curve forced monotone non-increasing in difficulty-bin index.

This regularizes noisy empirical estimates before optimization.

### F.2 Feasibility guarantee

For every task-family/model pair, threshold selection returns a valid output because:

1. strict feasible set returns `strict_feasible_max`,
2. otherwise fallback returns `fallback_min_violation`.

Hence \(\tau^*\) exists even when constraints conflict.

### F.3 Bounded targets

Dynamic targets are clipped to compact intervals, guaranteeing bounded optimization domain and stable comparisons:

$$
c^{\mathrm{dyn}} \in [c_{\min}, c_{\max}], \qquad r^{\mathrm{dyn}} \in [r_{\min}, r_{\max}]
$$

### F.4 Non-compensatory safety in S3

`prescreen_gate` in `s3_framework.py` enforces non-compensatory constraints:

- Hard Rule 1: `SK=5` \(\Rightarrow\) disqualified,
- Hard Rule 2: `TC=5` and `SK\ge4` \(\Rightarrow\) disqualified,
- Flag Rule: `SK\ge4` \(\Rightarrow\) minimum tier `hybrid`.

Thus low values in other dimensions cannot compensate severe security/complexity flags.

### F.5 Empirical robustness signal from Smita repo

From `repos/SLM_Research_Project/evaluation/sensitivity_matrix_20260413_234329.csv`:

| Use case | Unique tier count across 5 weight profiles | Notes |
|---|---:|---|
| UC1 | 1 | Stable (`Hybrid`) |
| UC2 | 1 | Stable (`Pure SLM`) |
| UC3 | 1 | Stable (`Pure SLM`) |
| UC4 | 1 | Stable (`Pure SLM`) |
| UC5 | 2 | Boundary-sensitive (`Hybrid`/`Pure SLM`) |
| UC6 | 1 | Stable (`LLM Only`, gate-locked) |
| UC7 | 1 | Stable (`Hybrid`, flag-locked) |
| UC8 | 1 | Stable (`LLM Only`, gate-locked) |

## Appendix I. Generalization

### I.1 Implemented protocol (code-level)

`repos/small_language_models_usecases/framework/benchmarking/sddf_generalization_eval.py` defines cross-model generalization as:

1. load trained SDDF artifacts \((\text{weights},\text{scaler},\tau)\) per source model and seed,
2. apply them to target-model test splits in the same task family,
3. report transfer metrics in `generalization_report.json`.

### I.2 Available Artifacts and Output Status

| Artifact | Status | Evidence |
|---|---|---|
| `.../sddf_generalization_eval.py` | Present | Script exists |
| `.../generalization_report.json` | Not present | No file found in repo tree |
| Required target test JSONL under `sddf_training_splits_slm_only/<task>/<model>/test.jsonl` | Not present | task folders only contain `split_query_ids.json` |

Because the required test-split payloads are missing, direct cross-model transfer metrics are not currently reproducible from the checked-in artifacts alone.

### I.3 Available indirect generalization evidence across repos

1. Smita bridge report (`repos/SLM_Research_Project/evaluation/s3_sddf_bridge_report_20260413_234328.txt`) shows capability correlation \(\rho=-0.7262\) between S3 score and SDDF capability over 8 families.
2. Smita sensitivity matrix shows tier stability for 7/8 use cases under 5 weighting profiles; only UC5 is boundary-sensitive.

These support policy-level robustness but do not replace missing cross-model transfer metrics from `generalization_report.json`.

## Appendix J. Business / Economic Model

### J.1 Economic objective and assumptions (from code)

`repos/small_language_models_usecases/tools/generate_business_dashboard.py` defines:

$$
\mathrm{EV} = v_{\mathrm{success}}\cdot C - \ell_{\mathrm{fail}}\cdot R - c_{\mathrm{lat}}\cdot t - c_{\mathrm{direct}}
$$

with explicit proxy assumptions stored in `repos/small_language_models_usecases/model_runs/business_analytics/dashboard.json`:

| Assumption | Value |
|---|---:|
| Success value per correct query | 0.0500 USD |
| Failure loss per failure event | 0.2000 USD |
| Latency cost per second | 0.0001 USD |
| Local inference cost per second | 0.0002 USD |
| Baseline API cost per query | 0.0035 USD |

### J.2 Highest expected-value model by task family

(From `dashboard.json`, maximizing per-task `expected_value_usd`)

| Task family | Best model | Expected value (USD/query) | Direct cost (USD/query) | Capability | Risk |
|---|---|---:|---:|---:|---:|
| classification | `groq:llama-3.3-70b-versatile` | 0.00595 | 0.00350 | 0.5951 | 0.1012 |
| code_generation | `groq:llama-3.3-70b-versatile` | -0.02780 | 0.00350 | 0.4983 | 0.2458 |
| information_extraction | `groq:llama-3.3-70b-versatile` | 0.02484 | 0.00350 | 0.8043 | 0.0592 |
| instruction_following | `groq:llama-3.3-70b-versatile` | 0.02984 | 0.00350 | 0.8426 | 0.0433 |
| maths | `groq:llama-3.3-70b-versatile` | 0.01850 | 0.00350 | 0.7712 | 0.0824 |
| retrieval_grounded | `groq:llama-3.3-70b-versatile` | 0.01145 | 0.00350 | 0.6839 | 0.0956 |
| summarization | `qwen2.5:0.5b` | 0.02563 | 0.00059 | 0.7270 | 0.0491 |
| text_generation | `groq:llama-3.3-70b-versatile` | 0.04643 | 0.00350 | 1.0000 | 0.0000 |

### J.3 Pareto status patterns

From `dashboard.json`:

- Baseline LLM is frontier in all task families.
- SLM frontier inclusion is task-dependent:
  - strong in summarization (`qwen2.5:0.5b` dominates larger SLMs on EV),
  - mixed in retrieval-grounded and instruction-following,
  - weak in code-generation under current loss assumptions.

### J.4 Important interpretation constraint

The same business dashboard records `route_share_to_slm = 0.0` in the confidence-certified strategy block for listed models in this artifact snapshot. Therefore, economic tables above are best interpreted as model-wise static economics under recorded assumptions, not realized online blended-routing savings for this run snapshot.

## Source File Map (E/F/I/J)

| Appendix | Ground-truth files used |
|---|---|
| E | `repos/small_language_models_usecases/sddf/validation_dynamic.py`; `repos/small_language_models_usecases/sddf/s3_framework.py`; `repos/small_language_models_usecases/model_runs/classification/sddf/routing_policy.json` |
| F | `repos/small_language_models_usecases/sddf/validation_dynamic.py`; `repos/small_language_models_usecases/sddf/s3_framework.py`; `repos/SLM_Research_Project/evaluation/sensitivity_matrix_20260413_234329.csv` |
| I | `repos/small_language_models_usecases/framework/benchmarking/sddf_generalization_eval.py`; `repos/SLM_Research_Project/evaluation/s3_sddf_bridge_report_20260413_234328.txt`; `repos/SLM_Research_Project/evaluation/sensitivity_matrix_20260413_234329.csv` |
| J | `repos/small_language_models_usecases/tools/generate_business_dashboard.py`; `repos/small_language_models_usecases/model_runs/business_analytics/dashboard.json` |
