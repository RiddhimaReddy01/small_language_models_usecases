## 9. Results

Section 9 reports UC1 to UC8 outcomes by aligning policy-layer S3 predictions with SDDF empirical evidence and runtime routing outputs.

### 9.1 Result Definitions

For each use case \(u\):

\[
\Delta_{tier}(u)=\text{TierIndex}(\text{Runtime}_u)-\text{TierIndex}(\text{S3}_u),
\quad \text{TierIndex}(\text{Pure SLM},\text{Hybrid},\text{LLM Only})=(1,2,3)
\]

\[
\text{Agreement}(u)=\mathbb{1}[\Delta_{tier}(u)=0]
\]

\[
p_u=\Pr(d_u\le\tau_t^*),\quad
\text{RuntimeBehavior}(u)=
\begin{cases}
\text{SLM}, & p_u=1\\
\text{LLM}, & p_u=0\\
\text{HYBRID}, & 0<p_u<1
\end{cases}
\]

### 9.2 UC1 to UC8 Outcome Table

| Use case | S3 score | Predicted tier | Mapped task family | SDDF capability \(C_m(d)\) | SDDF risk \(R_m(d)\) | Threshold \(\tau^*\) | Runtime behavior | Agreement / disagreement | Explanation |
|---|---:|---|---|---:|---:|---:|---|---|---|
| UC1 | 3.40 | Hybrid | classification | 0.3145 | 0.3428 | 0.6667 | LLM (\(p_u=0.00\)) | Disagreement | At the frozen threshold, no UC1 instances satisfy \(d\le\tau^*\), so runtime escalates to LLM-only behavior while S3 predicted Hybrid. |
| UC2 | 2.60 | Pure SLM | information_extraction | 0.7037 | 0.1481 | 1.0000 | SLM (\(p_u=1.00\)) | Agreement | All UC2 instances are within threshold, and empirical capability-risk values are consistent with pure local execution. |
| UC3 | 2.67 | Pure SLM | classification | 0.3145 | 0.3428 | 0.6667 | LLM (\(p_u=0.00\)) | Disagreement | The classification threshold is not met for UC3 runtime difficulty, producing full escalation to LLM despite a Pure SLM policy prediction. |
| UC4 | 2.07 | Pure SLM | classification | 0.3145 | 0.3428 | 0.6667 | LLM (\(p_u=0.00\)) | Disagreement | UC4 runtime difficulty mass lies above \(\tau^*\), so empirical routing requires LLM-only behavior. |
| UC5 | 3.27 | Hybrid | code_generation | 0.3044 | 0.3478 | 0.6667 | HYBRID (\(p_u=0.27\)) | Agreement | Partial coverage under threshold yields mixed routing, which matches the Hybrid policy prediction. |
| UC6 | 4.27 | LLM Only | classification | 0.3145 | 0.3428 | 0.6667 | LLM (\(p_u=0.00\)) | Agreement | With zero threshold coverage at runtime, UC6 remains fully escalated, consistent with the LLM-only policy assignment. |
| UC7 | 3.20 | Hybrid | summarization | 0.8350 | 0.0825 | 0.2972 | LLM (\(p_u=0.00\)) | Disagreement | Although family-level capability is high, the frozen threshold is low relative to UC7 observed difficulty, driving full escalation at runtime. |
| UC8 | 3.07 | LLM Only | text_generation | 0.8479 | 0.0761 | 0.9333 | SLM (\(p_u=1.00\)) | Disagreement | UC8 is fully within the empirical threshold region at runtime, so SDDF behavior is Pure SLM while S3 remains conservative. |

### 9.3 Figure 9.1 (Conceptual)

Figure 9.1: Cross-layer result path for each use case.

\[
\text{S3 Score} \rightarrow \text{Predicted Tier} \rightarrow (C_m(d),R_m(d),\tau^*) \rightarrow \text{Runtime Behavior} \rightarrow \text{Agreement Status}
\]

### 9.4 Ground-Truth Sources Used

- `docs/section8_outputs/section8_uc_evaluation_table_enhanced.csv`
- `docs/section7_outputs/runtime_routing_consensus_frozen_tau.csv`
- `docs/section8_outputs/section8_summary_enhanced.json`
- `docs/source_extracts/S3_SDDF_Section4.txt` (gate-rule interpretation context)
