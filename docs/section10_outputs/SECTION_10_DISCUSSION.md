## 10. Discussion

This section interprets the cross-layer evidence from Section 9 by examining when policy-layer S3 aligns with SDDF runtime behavior, where it diverges, and what this implies for enterprise deployment governance.

### 10.1 When S3 Works

S3 aligns with empirical SDDF boundaries in three use cases: UC2, UC5, and UC6.

| Use case | S3 tier | Runtime tier | Interpretation |
|---|---|---|---|
| UC2 | Pure SLM | Pure SLM | Correct low-risk and high-feasibility assignment for information extraction. |
| UC5 | Hybrid | Hybrid | Correct boundary placement for partial feasibility and selective escalation. |
| UC6 | LLM Only | LLM Only | Correct high-risk assignment under safety-critical clinical conditions. |

The agreement rate is:

\[
\text{Agreement Rate}=\frac{3}{8}=0.375
\]

Although the aggregate agreement is moderate, these aligned cases span all three tiers (Pure SLM, Hybrid, LLM Only), indicating that S3 can correctly identify low-risk, intermediate, and high-risk operating regions when task structure and risk profile are well represented by the six-dimension rubric.

### 10.2 When S3 Fails

S3 diverges from runtime evidence in five use cases.

| Failure type | Use cases | Pattern |
|---|---|---|
| Underestimation (dangerous) | UC1, UC3, UC4, UC7 | S3 predicts a lower tier than runtime requires. |
| Overestimation (inefficient) | UC8 | S3 predicts LLM Only while runtime remains within Pure SLM region. |

The disagreement rate is:

\[
\text{Disagreement Rate}=\frac{5}{8}=0.625
\]

Boundary sensitivity is most visible at UC7. UC7 sits at the policy threshold boundary (S3 = 3.20), yet runtime behavior is fully escalated because observed instance difficulty lies above the frozen summarization threshold. This shows that small changes near policy cutoffs can produce large changes in operational routing.

UC8 exhibits the opposite boundary effect: policy-level conservatism yields LLM Only assignment, while empirical runtime evidence supports Pure SLM behavior. This demonstrates that boundary errors can occur in both directions, with different managerial consequences.

### 10.3 Role of Gate Rules

Gate rules are safety load-bearing components of S3 rather than optional heuristics.

| Gate rule | Intended function | Observed implication in this study |
|---|---|---|
| Hard Rule 1: \(SK=5\Rightarrow\) LLM Only | Prevent irreversible harm in highest-stakes tasks | UC6 remains escalated, consistent with safety-first governance. |
| Hard Rule 2: \(TC=5\ \land\ SK\ge 4\Rightarrow\) LLM Only | Block complex high-stakes autonomous deployment | UC8 is conservatively blocked at policy layer, despite runtime SLM feasibility. |
| Flag Rule: \(SK\ge 4\Rightarrow\) minimum Hybrid | Prevent unsafe downgrades from weighted averaging | Protects against compensatory scoring in elevated-stakes conditions. |

The central trade-off is explicit: gate rules reduce downside safety risk but can increase false conservatism in selected cases. In managerial terms, this is a deliberate asymmetry in favor of harm prevention.

### 10.4 Task-Family Mapping Limitations

The enterprise-task to task-family bridge is operationally useful but structurally lossy. A one-task to one-family mapping can mask mixed computational requirements within a single enterprise workflow.

Representative ambiguity patterns include:

| Use case | Primary family used | Latent secondary demands | Limitation introduced |
|---|---|---|---|
| UC7 (legal contract risk) | summarization | retrieval-grounded reasoning, clause-level extraction | Single-family mapping may underrepresent high-difficulty subcomponents. |
| UC8 (financial report drafting) | text_generation | instruction-following and numerical consistency checks | Policy score may overweight risk while runtime evidence reflects narrower generated scope. |
| UC2 (invoice extraction) | information_extraction | occasional classification-like validation logic | Usually stable, but pipeline-level heterogeneity remains possible. |

A practical implication is that mapping quality directly affects cross-framework agreement. When mapping granularity is too coarse, disagreements may reflect abstraction mismatch rather than policy failure alone.

### 10.5 Managerial Implications

The results support a two-stage deployment protocol.

1. Stage 1 (Policy screen): apply S3 with gate rules to establish an initial governance envelope.
2. Stage 2 (Empirical calibration): validate tier feasibility using SDDF \((C_m(d),R_m(d),\tau^*)\) and frozen runtime thresholds.
3. Stage 3 (Operational routing): enforce per-instance runtime escalation based on observed difficulty relative to \(\tau^*\).

This protocol creates complementary controls:

| Objective | S3 contribution | SDDF contribution |
|---|---|---|
| Risk control | Pre-deployment safeguards, non-compensatory gate logic | Post-calibration empirical boundary verification |
| Cost efficiency | Early identification of potentially localizable use cases | Quantified SLM coverage \(p_u=\Pr(d\le\tau^*)\) for runtime cost modeling |
| Governance traceability | Transparent rubric and explicit tier rationale | Auditable capability-risk metrics and threshold artifacts |

From the observed aggregate trade-off, runtime routing reduces average monthly cost relative to LLM-only operation (approximately 35,849 to 71,767 USD/month versus 50,000 to 100,000 USD/month), while preserving similar macro-level label performance in this dataset. The managerial conclusion is not that S3 should replace SDDF, but that S3 should be treated as a governance prior and SDDF as the operational truth layer before production commitments are finalized.

### 10.6 Figure 10.1 (Conceptual)

\[
\text{S3 Policy Prior} \rightarrow \text{Gate-Constrained Tier} \rightarrow \text{SDDF Calibration} \rightarrow \text{Runtime Routing} \rightarrow \text{Managerial Decision Audit}
\]

Grounded artifacts used for this discussion:

- `docs/section9_outputs/SECTION_9_RESULTS.md`
- `docs/section8_outputs/section8_uc_evaluation_table_enhanced.csv`
- `docs/section8_outputs/section8_summary_enhanced.json`
- `docs/section7_outputs/runtime_routing_consensus_frozen_tau.csv`
- `docs/source_extracts/S3_SDDF_Section4.txt`
