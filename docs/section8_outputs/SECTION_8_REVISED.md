## 8. Evaluation Framework

Section 8 evaluates UC1 to UC8 at use-case level by aligning policy prediction (S3) with runtime deployment outcomes (Section 7), and by quantifying quality, routing behavior, risk, cost, and latency using SDDF test artifacts (Section 6).

### 8.1 Tier Correctness

$$\text{S3 Tier} \quad vs \quad \text{Runtime Tier}$$

Runtime tier is derived from strict aggregated `routing_decision` (`SLM` -> `Pure SLM`, `HYBRID` -> `Hybrid`, `LLM` -> `LLM Only`).

Observed agreement: 3/8 use cases (convergence rate = 0.375).

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

- Underestimation: S3 assigns a lower tier than runtime requires (dangerous).
- Overestimation: S3 assigns a higher tier than runtime requires (inefficient).

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

Primary method: Spearman rank correlation. Robustness check: Kendall tau-b.

$$\text{corr}(S3, C_m(d)), \quad \text{corr}(S3, R_m(d))$$

| Method | corr(S3, Cm(d)) | p-value | corr(S3, Rm(d)) | p-value |
|---|---:|---:|---:|---:|
| Spearman | -0.2664 | 0.5237 | 0.2664 | 0.5237 |
| Kendall tau-b | -0.1612 | 0.5952 | 0.1612 | 0.5952 |

The observed coefficients indicate limited monotonic alignment between S3 scores and empirical SDDF outcomes at UC level. With non-significant p-values in both tests, S3 should be interpreted as a coarse-grained policy prior rather than a continuous predictor of capability or risk.

### 8.4 System Performance (SDDF Test-Phase Evidence)

UC8 is excluded from label-based metrics (Accuracy/F1/Failure) because no compatible ground-truth label structure is persisted for direct UC8 classification-style scoring in the same format as UC1-UC7.

| Use Case | Runtime Accuracy* | Runtime F1* | Runtime Failure* | SLM Coverage Pr(d<=tau) | Runtime P95 (ms) |
|---|---:|---:|---:|---:|---:|
| UC1 | 0.8333 | 0.8286 | 0.1667 | 0.00 | 2426.3 |
| UC2 | 1.0000 | 1.0000 | 0.0000 | 1.00 | 3600.1 |
| UC3 | 0.8333 | 0.7000 | 0.1667 | 0.00 | 2426.9 |
| UC4 | 1.0000 | 1.0000 | 0.0000 | 0.00 | 363.1 |
| UC5 | 0.8333 | 0.7117 | 0.1667 | 0.27 | 2738.1 |
| UC6 | 0.5000 | 0.4333 | 0.5000 | 0.00 | 2593.9 |
| UC7 | 0.5000 | 0.4127 | 0.5000 | 0.00 | 2639.3 |
| UC8 | N/A | N/A | N/A | 1.00 | 10265.5 |

*Label-based metrics reported for UC1-UC7 only.

#### 8.4.1 Equal-Weight Macro Summary (UC1-UC7)

| System | Accuracy_macro | F1_macro | Failure_macro |
|---|---:|---:|---:|
| LLM-only baseline (observed LLM rows) | 0.7857 | 0.7202 | 0.2143 |
| SLM-only baseline (observed best-SLM rows) | 0.8095 | 0.7794 | 0.1905 |
| Runtime routing system | 0.7857 | 0.7266 | 0.2143 |

#### 8.4.2 Formal Cost Model

Cost is evaluated with Section 1 ranges using routing coverage:

$$\text{Cost}_{UC}=p_{SLM}\cdot C_{SLM}+(1-p_{SLM})\cdot C_{LLM}, \quad p_{SLM}=\Pr(d\le\tau)$$

with $C_{SLM}\in[127,500]$ USD/month and $C_{LLM}\in[50{,}000,100{,}000]$ USD/month.

| Strategy | Cost Range (USD/month) | Accuracy_macro* | F1_macro* | Failure_macro* | Mean P95 (ms) |
|---|---:|---:|---:|---:|---:|
| LLM-only | 50000-100000 | 0.7857 | 0.7202 | 0.2143 | 2111.2 |
| SLM-only | 127-500 | 0.8095 | 0.7794 | 0.1905 | 2799.6 |
| Runtime routing | 35849-71767 | 0.7857 | 0.7266 | 0.2143 | 3381.6 |

*Macro metrics exclude UC8 by design.

#### 8.4.3 Latency Interpretation

Runtime mean P95 latency exceeds LLM-only mean P95 in this dataset. This indicates that local SLM inference can become CPU-bound and less optimized than hosted LLM infrastructure for some workloads. This is an operational finding rather than a theoretical contradiction.

#### 8.4.4 Failure Mode Analysis (Best-SLM Test Outputs)

| Failure Type | Description | Frequency |
|---|---|---:|
| hard_failure | Invalid/error outputs requiring escalation | 108 |
| wrong_prediction | Valid output but incorrect label/content | 15 |
| none | Correct outputs (non-failure reference count) | 21 |

### 8.5 Convergence Formalization and Decision Quality

Convergence rate is defined as:

$$\text{Convergence Rate}=\frac{\#(\text{S3 Tier}=\text{Runtime Tier})}{\text{Total Use Cases}}$$

Observed convergence rate: 0.375 (3/8).

Decision quality metric is defined as decision accuracy under task-family threshold constraints:

$$\text{Decision Accuracy}=\frac{\#(\text{routing decisions satisfying cap/risk criteria})}{\text{Total decisions}}$$

Observed decision accuracy: 0.500.