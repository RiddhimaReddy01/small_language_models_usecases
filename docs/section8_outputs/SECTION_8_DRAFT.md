## 8. Evaluation Framework

Section 8 evaluates UC1 to UC8 at use-case level by comparing S3 policy tiers with runtime deployment tiers produced by Section 7 routing decisions.

### 8.1 Tier Correctness

Comparison target:

$$\text{S3 Tier} \quad vs \quad \text{Runtime Tier}$$

Tier agreement is observed in 3/8 use cases.

| Use Case | S3 Tier | Runtime Tier | routing_decision |
|---|---|---|---|
| UC1 | Hybrid | LLM Only | LLM |
| UC2 | Pure SLM | Pure SLM | SLM |
| UC3 | Pure SLM | LLM Only | LLM |
| UC4 | Pure SLM | LLM Only | LLM |
| UC5 | Hybrid | Hybrid | HYBRID |
| UC6 | LLM Only | LLM Only | LLM |
| UC7 | Hybrid | LLM Only | LLM |
| UC8 | LLM Only | Pure SLM | SLM |

### 8.2 Gap Analysis

- Underestimation: S3 predicts lower tier than runtime requirement (dangerous).
- Overestimation: S3 predicts higher tier than runtime requirement (inefficient).

Counts: underestimation=4, overestimation=1, match=3.

| Use Case | Gap Type |
|---|---|
| UC1 | Underestimation (dangerous) |
| UC2 | Match |
| UC3 | Underestimation (dangerous) |
| UC4 | Underestimation (dangerous) |
| UC5 | Match |
| UC6 | Match |
| UC7 | Underestimation (dangerous) |
| UC8 | Overestimation (inefficient) |

### 8.3 Cross-Framework Convergence

Primary method: Spearman rank correlation (recommended for n=8 and non-linear/ordinal behavior).
Robustness check: Kendall tau-b.

$$\text{corr}(S3, C_m(d)), \quad \text{corr}(S3, R_m(d))$$

| Correlation | corr(S3, Cm(d)) | corr(S3, Rm(d)) |
|---|---:|---:|
| Spearman | -0.2664 | 0.2664 |
| Kendall tau-b | -0.1612 | 0.1612 |

Interpretation: convergence is weak in this UC-level online alignment, with modest inverse association between S3 score and capability and modest positive association between S3 score and risk.

### 8.4 System Performance (from SDDF Test Phase)

- Task-level metrics: accuracy, F1, failure rate, latency (best-SLM row from Section 6 artifacts).
- Routing effectiveness: runtime SLM coverage $\Pr(d \le \tau)$ from Section 7.
- Failure rate: $1-\text{accuracy}$.
- Cost/latency: cost proxy anchored to Section 1 ranges (SLM: $127-$500/month, LLM: $50k-$100k/month) blended by SLM routing coverage.

| Use Case | Accuracy | F1 | Failure Rate | SLM Coverage | P95 Latency (ms) | Cost Proxy Low ($/mo) | Cost Proxy High ($/mo) |
|---|---:|---:|---:|---:|---:|---:|---:|
| UC1 | 0.8333 | 0.7778 | 0.1667 | 0.00 | 322.8 | 50000 | 100000 |
| UC2 | 1.0000 | 1.0000 | 0.0000 | 1.00 | 3600.1 | 127 | 500 |
| UC3 | 0.8333 | 0.8333 | 0.1667 | 0.00 | 513.3 | 50000 | 100000 |
| UC4 | 1.0000 | 1.0000 | 0.0000 | 0.00 | 504.1 | 50000 | 100000 |
| UC5 | 0.8333 | 0.8333 | 0.1667 | 0.27 | 3535.8 | 36534 | 73135 |
| UC6 | 0.6667 | 0.4889 | 0.3333 | 0.00 | 2881.3 | 50000 | 100000 |
| UC7 | 0.5000 | 0.5222 | 0.5000 | 0.00 | 774.1 | 50000 | 100000 |
| UC8 |  |  |  | 1.00 | 10265.5 | 127 | 500 |