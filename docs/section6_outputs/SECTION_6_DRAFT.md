## 6. SDDF v3 (Empirical Validation Layer)

This section reports SDDF v3 empirical validation using Smita's benchmark artifacts and Riddhima's SDDF implementation as the computational ground truth. The implementation path was:

- Difficulty and feature extraction: `sddf/difficulty.py`
- Capability and risk estimation plus adaptive thresholding: `sddf/validation_dynamic.py`
- Source benchmark artifacts: `data/gold_sets/*.csv`, `data/raw_outputs/*.csv`

Because the benchmark raw files are test-heavy, SDDF phases were executed with a deterministic item-level split of 60/20/20 for train, validation, and test, respectively, with fixed random seed 42. This yielded 18 train items, 6 validation items, and 6 test items per use case before model-run expansion.

### 6.2 Train Phase

#### Difficulty feature extraction

For each sample, SDDF computes a difficulty representation

$$
\mathbf{x}_d = [n_{in}, H, \hat{R}, |\Gamma|, P, D, n_{in}H, \hat{R}|\Gamma|, P\hat{R}, \ldots]
$$

where $n_{in}$ is input length, $H$ is entropy, $\hat{R}$ is reasoning proxy, $|\Gamma|$ is constraint count, $P$ is parametric dependence, and $D$ is dependency distance, with task-family-specific augmentations.

#### Failure signal construction

Binary failure was constructed from the benchmark output fields:

$$
F_i = \mathbb{1}[\text{incorrect}_i \lor \text{invalid}_i \lor \text{error}_i]
$$

and per-sample capability was defined as

$$
C_i = 1 - F_i.
$$

The train-phase failure signal was therefore directly tied to observed benchmark correctness and validity fields without synthetic relabeling.

**Table 6.1. Train-phase outputs (best SLM per use case).**

| Use Case | Task Family | Best SLM | Train Failure Signal Rate |
|---|---|---|---:|
| UC1 | Classification | Mistral-7B | 0.0556 |
| UC2 | Information Extraction | Gemma3-4B | 0.5000 |
| UC3 | Classification | Gemma3-4B | 0.1111 |
| UC4 | Classification | Gemma3-4B | 0.0000 |
| UC5 | Code Generation | Llama-3.1-8B | 0.0556 |
| UC6 | Classification | Llama-3.1-8B | 0.2222 |
| UC7 | Summarization | Qwen2.5-7B | 0.1667 |
| UC8 | Text Generation | Gemma3-4B | 0.0000 |

**Figure 6.1 (to insert).** Train-phase feature distribution by task family: $n_{in}$, $H$, and $\hat{R}$.

### 6.3 Validation Phase

Validation estimates capability and risk as functions of difficulty:

$$
C_m(d) = \mathbb{E}[\mathbb{1}[\text{correct}] \mid d, m], \qquad
R_m(d) = \mathbb{E}[\text{risk} \mid d, m].
$$

Risk is task-family weighted in SDDF v3, with nonzero penalties only for failures.

Adaptive thresholds were computed on the validation split as percentile targets:

$$
\tau_{cap} = \mathrm{Percentile}_{50}(C_m), \qquad
\tau_{risk} = \mathrm{Percentile}_{75}(R_m).
$$

**Table 6.2. Validation thresholds and selected $\tau^*$ (best SLM per use case).**

| Use Case | Best SLM | $\tau_{cap}$ | $\tau_{risk}$ | $\tau^*$ | Selection Source |
|---|---|---:|---:|---:|---|
| UC1 | Mistral-7B | 1.0000 | 0.0467 | 3.8522 | strict_feasible_adaptive |
| UC2 | Gemma3-4B | 0.3333 | 0.4000 | 0.0000 | strict_feasible_adaptive |
| UC3 | Gemma3-4B | 0.8167 | 0.1330 | 4.0588 | strict_feasible_adaptive |
| UC4 | Gemma3-4B | 1.0000 | 0.0000 | 3.9698 | strict_feasible_adaptive |
| UC5 | Llama-3.1-8B | 0.5000 | 0.4513 | 0.0000 | strict_feasible_adaptive |
| UC6 | Llama-3.1-8B | 1.0000 | 0.0000 | 5.6421 | strict_feasible_adaptive |
| UC7 | Qwen2.5-7B | 0.7000 | 0.1526 | 12.0000 | strict_feasible_adaptive |

All reported best-model runs selected $\tau^*$ from the strict feasible set. No minimum-violation fallback was required for these best-model rows.

**Figure 6.2 (to insert).** Validation curves per use case: $C_m(d)$ and $R_m(d)$ with $(\tau_{cap}, \tau_{risk})$ and selected $\tau^*$.

### 6.4 Threshold Selection

Operational routing threshold follows:

$$
\tau^* = \max d\;\text{s.t.}\; C_m(d) \ge \tau_{cap},\; R_m(d) \le \tau_{risk}.
$$

If no feasible region exists, SDDF v3 applies minimum-violation fallback:

$$
\tau^* = \arg\min_d \left[\max(0,\tau_{cap}-C_m(d)) + \max(0,R_m(d)-\tau_{risk})\right].
$$

In runtime evaluation, routing is

$$
\text{route}(x)=
\begin{cases}
\text{SLM}, & d(x) \le \tau^* \\
\text{LLM}, & d(x) > \tau^*
\end{cases}
$$

which generated per-sample routing decisions stored in the Section 6 result JSON.

### 6.5 Test Phase

Test-phase outputs were computed at dataset level for each model and use case:

- Predictions
- Routing decisions
- Correctness counts
- Failure category counts

For label-bearing tasks (UC1-UC7), the following were computed:

- Accuracy
- Precision, Recall, F1 (macro)
- ROC-AUC and PR-AUC (hard-label proxy due to missing saved logits)
- Calibration metrics (Brier, ECE; hard-label proxy)

For UC8 (generation), raw outputs do not contain class labels or persisted human-judge scores in the same file. Therefore, generation criteria coverage and output validity were used as conservative proxies.

**Table 6.3. Test-phase performance (best SLM vs LLM).**

| Use Case | Best SLM | SLM Accuracy | LLM Accuracy | SLM F1 | SLM ROC-AUC | SLM PR-AUC | SLM Brier | SLM ECE | SLM P95 Latency (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| UC1 | Mistral-7B | 0.8333 | 0.8333 | 0.7778 | 0.7500 | 0.7333 | 0.3333 | 0.1667 | 322.8 |
| UC2 | Gemma3-4B | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 3600.0 |
| UC3 | Gemma3-4B | 0.8333 | 0.8333 | 0.8333 | 0.9125 | 0.7917 | 0.3333 | 0.1667 | 513.3 |
| UC4 | Gemma3-4B | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 504.2 |
| UC5 | Llama-3.1-8B | 0.8333 | 0.8333 | 0.8333 | 0.9125 | 0.7917 | 0.3333 | 0.1667 | 3535.8 |
| UC6 | Llama-3.1-8B | 0.6667 | 0.5000 | 0.4889 | 0.6806 | 0.4815 | 0.6667 | 0.3333 | 2881.4 |
| UC7 | Qwen2.5-7B | 0.5000 | 0.5000 | 0.5222 | 0.6250 | 0.4722 | 1.0000 | 0.5000 | 774.1 |

**UC8 generation proxy results (best SLM vs LLM).**

| Use Case | Best SLM | Criteria Hit Rate | Valid Output Rate | P95 Latency (ms) | LLM Criteria Hit Rate | LLM Valid Output Rate |
|---|---|---:|---:|---:|---:|---:|
| UC8 | Gemma3-4B | 0.0000 | 1.0000 | 10265.5 | 0.0043 | 0.4074 |

These UC8 proxy values should be interpreted cautiously because strict literal criterion matching underestimates semantic coverage and because test sample counts differ by model in the persisted raw artifact.

**Figure 6.3 (to insert).** Test-phase model comparison across UC1-UC7: Accuracy, F1, and calibration (ECE).

**Figure 6.4 (to insert).** Runtime routing histogram by use case with threshold line at $\tau^*$.

### Reproducibility Note for Section 6

All Section 6 results are reproducible from:

- `tools/compute_sddf_v3_section6_metrics.py`
- `docs/section6_outputs/sddf_v3_section6_results.json`
- `docs/section6_outputs/sddf_v3_section6_model_metrics.csv`

The computation preserves repository-grounded logic and does not introduce external heuristics beyond the documented deterministic split fallback required by raw artifact composition.
