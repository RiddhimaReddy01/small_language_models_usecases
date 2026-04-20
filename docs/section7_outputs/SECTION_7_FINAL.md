## 7. Runtime Deployment

Runtime deployment is defined as a policy decision layer that maps each enterprise use case to a single `routing_decision` using SDDF task-family difficulty and frozen threshold policy.

### 7.1 Runtime Policy

For each use case \(u\), let \(f(u)\) denote its SDDF task family from Table 1 (computed by `s3_sddf_bridge.py`).  
Let \(d_u\) be the empirical difficulty distribution computed from Smita's use-case inputs using Riddhima's `sddf/difficulty.py`.  
Let \(\tau_{f(u)}^{\text{frozen}}\) be the **SLM-consensus frozen threshold** for task family \(f(u)\), computed as the mean \(\tau^*\) across SLMs from SDDF v3 offline test outputs in `continuous_validation_results.json`.

Decision rule:

\[
\text{routing\_decision}(u)=
\begin{cases}
\texttt{SLM}, & \Pr(d_u \le \tau_{f(u)}^{\text{frozen}})=1 \\
\texttt{LLM}, & \Pr(d_u \le \tau_{f(u)}^{\text{frozen}})=0 \\
\texttt{HYBRID}, & 0 < \Pr(d_u \le \tau_{f(u)}^{\text{frozen}}) < 1
\end{cases}
\]

This section intentionally emits only one runtime output field:

\[
\texttt{routing\_decision} \in \{\texttt{SLM},\texttt{HYBRID},\texttt{LLM}\}.
\]

### 7.2 Computation Inputs

- UC-to-task-family mapping: Smita-Riddhima bridge table (`s3_sddf_bridge.py`)
- Difficulty computation: `repos/small_language_models_usecases/sddf/difficulty.py`
- Frozen thresholds: SLM-consensus \(\tau^*\) from `repos/small_language_models_usecases/continuous_validation_results.json`
- Smita use-case inputs: `repos/SLM_Research_Project/data/gold_sets/*.csv`

### 7.3 Runtime Decisions for Smita's Use Cases

| Use Case | routing_decision |
|---|---|
| UC1 | LLM |
| UC2 | SLM |
| UC3 | LLM |
| UC4 | LLM |
| UC5 | HYBRID |
| UC6 | LLM |
| UC7 | LLM |
| UC8 | SLM |

### 7.4 Implementation Note

The exact generated artifact used for this section is:

- `docs/section7_outputs/routing_decision_only_strict.csv`
- `docs/section7_outputs/runtime_routing_consensus_frozen_tau.csv`
