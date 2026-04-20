## 6. SDDF v3 (Empirical Validation Layer)

Section 6 is the offline calibration stage and is performed at the SDDF task-family level using Riddhima's repository artifacts.

### 6.1 Offline Objective

For each task family \(t\), SDDF v3 estimates model capability and risk across difficulty and selects an operational threshold:

\[
C_m(d)=\mathbb{E}[\mathbf{1}(\text{correct})\mid d,m], \qquad
R_m(d)=\mathbb{E}[\text{risk}\mid d,m]
\]

\[
\tau_m^*(t)=\max d\;\text{s.t.}\;C_m(d)\ge \tau_{cap},\;R_m(d)\le \tau_{risk}
\]

When strict feasibility is absent, SDDF applies fallback minimum-violation selection.

### 6.2 Train Phase: Difficulty Features by Task Family

Difficulty is computed with `sddf/difficulty.py` using a shared feature backbone and task-specific decomposition.

Shared backbone features:

\[
\mathbf{x}_{base}=[n_{in},H,\hat{R},|\Gamma|,P,D,\hat{R}|\Gamma|,n_{in}H,P\hat{R}]
\]

Task-specific SDDF features:

| Task family | Additional feature block from `difficulty.py` |
|---|---|
| `classification` | `classification_ambiguity`, `classification_negation_density`, `classification_domain_shift` |
| `maths` | `math_numeric_density`, `math_symbol_density`, `math_precision_cues` |
| `instruction_following` | `instruction_format_strictness`, `instruction_prohibition_count`, `instruction_step_count`, `instruction_conflict_cues` |
| `summarization`, `retrieval_grounded`, `information_extraction`, `text_generation`, `code_generation` | Primarily backbone features plus task-dimension mapping in `TASK_DIMENSION_MAP` |

Failure signal is constructed from observed outcomes:

\[
F_i=\mathbf{1}[\text{incorrect}_i \lor \text{invalid}_i \lor \text{error}_i],\quad C_i=1-F_i
\]

### 6.3 Validation Phase: Capability-Risk Curves and \(\tau^*\)

Offline validation artifacts are taken from:

- `repos/small_language_models_usecases/continuous_validation_results.json`

Models used in SDDF v3 offline calibration: `qwen2.5_0.5b`, `qwen2.5_3b`, `qwen2.5_7b`.

Consensus frozen task-family threshold is defined as mean \(\tau^*\) across SLMs:

\[
\tau_t^{\text{consensus}}=\frac{1}{|M_{SLM}|}\sum_{m\in M_{SLM}}\tau_m^*(t)
\]

### 6.4 Test Verification of Operational \(\tau^*\)

The SDDF v3 test outputs verify whether selected thresholds produce usable coverage/capability/risk operating points.

| Task family | SLM runs | \(\tau^{\text{consensus}}\) | Mean coverage | Mean \(C(\tau^*)\) | Mean \(R(\tau^*)\) | Dominant \(\tau\)-source |
|---|---:|---:|---:|---:|---:|---|
| classification | 3 | 0.6667 | 0.8805 | 0.3145 | 0.3428 | fallback_min_violation_robust |
| code_generation | 3 | 0.6667 | 0.8776 | 0.3044 | 0.3478 | mixed (strict + fallback) |
| information_extraction | 3 | 1.0000 | 1.0000 | 0.7037 | 0.1481 | fallback_min_violation_robust |
| instruction_following | 3 | 1.0000 | 1.0000 | 0.7133 | 0.1433 | fallback_min_violation_robust |
| maths | 3 | 0.3333 | 0.7803 | 0.1439 | 0.4280 | fallback_min_violation_robust |
| retrieval_grounded | 3 | 1.0000 | 1.0000 | 0.5159 | 0.2421 | fallback_min_violation_robust |
| summarization | 3 | 0.2972 | 0.6212 | 0.8350 | 0.0825 | mixed (strict + fallback) |
| text_generation | 3 | 0.9333 | 0.8803 | 0.8479 | 0.0761 | mixed (strict + fallback) |

These \(\tau_t^{\text{consensus}}\) values are frozen for online routing in Section 7.

---

## 7. Runtime Deployment

Section 7 is the online execution stage for Smita's use cases. It consumes Section 6 frozen task-family thresholds and outputs only one field: `routing_decision`.

### 7.1 Online Rule

Given use case \(u\), mapped task family \(t=f(u)\), and empirical use-case difficulty distribution \(d_u\):

\[
\text{routing\_decision}(u)=
\begin{cases}
\texttt{SLM}, & \Pr(d_u \le \tau_t^{\text{consensus}})=1 \\
\texttt{LLM}, & \Pr(d_u \le \tau_t^{\text{consensus}})=0 \\
\texttt{HYBRID}, & 0<\Pr(d_u \le \tau_t^{\text{consensus}})<1
\end{cases}
\]

Where:

- \(d_u\) is computed from Smita inputs via `sddf/difficulty.py` using mapped task-family features.
- \(\tau_t^{\text{consensus}}\) is the frozen SLM-consensus threshold from Section 6.

### 7.2 Online Decisions for Smita Use Cases

| Use case | Task family | Frozen \(\tau_t^{\text{consensus}}\) | \(\Pr(d_u\le\tau)\) | routing_decision |
|---|---|---:|---:|---|
| UC1 | classification | 0.6667 | 0.00 | LLM |
| UC2 | information_extraction | 1.0000 | 1.00 | SLM |
| UC3 | classification | 0.6667 | 0.00 | LLM |
| UC4 | classification | 0.6667 | 0.00 | LLM |
| UC5 | code_generation | 0.6667 | 0.27 | HYBRID |
| UC6 | classification | 0.6667 | 0.00 | LLM |
| UC7 | summarization | 0.2972 | 0.00 | LLM |
| UC8 | text_generation | 0.9333 | 1.00 | SLM |

### 7.3 Runtime Output Contract

Output field (only):

\[
\texttt{routing\_decision}\in\{\texttt{SLM},\texttt{HYBRID},\texttt{LLM}\}
\]

Strict generated artifact:

- `docs/section7_outputs/routing_decision_only_strict.csv`

### 7.4 Reproducibility Pointers

- Offline threshold source: `repos/small_language_models_usecases/continuous_validation_results.json`
- Online decision computation artifact: `docs/section7_outputs/runtime_routing_consensus_frozen_tau.csv`
- Section 7 strict output: `docs/section7_outputs/routing_decision_only_strict.csv`

