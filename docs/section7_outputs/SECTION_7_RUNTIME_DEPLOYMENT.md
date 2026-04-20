## 7. Runtime Deployment

This section operationalizes SDDF v3 at inference time for Smita's eight enterprise use cases (UC1 to UC8).  
At runtime, each incoming input is scored for difficulty \(d\), compared with the model-specific threshold \(\tau^*\), and routed to either local SLM inference or LLM escalation.

### 7.1 Runtime Theory and Decision Rule

Let \(x\) be an incoming input, \(m\) be the selected SLM, and \(d(x)\) be the SDDF difficulty score computed from `sddf/difficulty.py`.

\[
d(x) = f_{\text{SDDF}}(x)
\]

The threshold \(\tau^*_m\) is carried from validation:

\[
\tau^*_m = \max d \;\text{s.t.}\; C_m(d)\ge \tau_{cap},\; R_m(d)\le \tau_{risk}
\]

Runtime routing policy:

\[
\text{route}(x)=
\begin{cases}
\text{SLM}, & d(x)\le \tau^*_m \\
\text{LLM}, & d(x)>\tau^*_m
\end{cases}
\]

Runtime output contract:

\[
y(x)=\{\hat{y},\; \text{route}(x)\}
\]

where \(\hat{y}\) is the prediction and \(\text{route}(x)\in\{\text{SLM},\text{LLM}\}\) is the routing decision.

### 7.2 Runtime Configuration for Smita's Use Cases

Assumption used for deployment table: one runtime SLM per use case, selected as the best SLM from Section 6 test results.

| Use Case | Task Family | Runtime SLM | \(\tau^*_m\) | Routed to SLM | Routed to LLM | Routing Policy |
|---|---|---|---:|---:|---:|---|
| UC1 | Classification | Mistral-7B | 3.8522 | 15 | 3 | SLM if \(d\le 3.8522\), else LLM |
| UC2 | Information Extraction | Gemma3-4B | 0.0000 | 18 | 0 | SLM if \(d\le 0\), else LLM |
| UC3 | Classification | Gemma3-4B | 4.0588 | 15 | 3 | SLM if \(d\le 4.0588\), else LLM |
| UC4 | Classification | Gemma3-4B | 3.9698 | 15 | 3 | SLM if \(d\le 3.9698\), else LLM |
| UC5 | Code Generation | Llama-3.1-8B | 0.0000 | 18 | 0 | SLM if \(d\le 0\), else LLM |
| UC6 | Classification | Llama-3.1-8B | 5.6421 | 15 | 3 | SLM if \(d\le 5.6421\), else LLM |
| UC7 | Summarization | Qwen2.5-7B | 12.0000 | 3 | 15 | SLM if \(d\le 12.0\), else LLM |
| UC8 | Text Generation | Gemma3-4B | N/A | 18 | 0 | Generation runtime flow; no class-based \(\tau^*\) row |

### 7.3 Hybrid Runtime Plan (What I will do in Hybrid cases)

For use cases where both SLM and LLM routes are active in observed runtime routing (for example UC1, UC3, UC4, UC6, and UC7), the deployment plan is:

1. Compute \(d(x)\) from SDDF features.
2. Compare \(d(x)\) to \(\tau^*_m\) for the selected runtime SLM.
3. If \(d(x)\le \tau^*_m\), execute local SLM and return its prediction.
4. If \(d(x)>\tau^*_m\), escalate to LLM and return the LLM prediction.
5. Persist an audit record with `item_id`, `difficulty_score`, `tau_star`, `routing_decision`, `prediction`.
6. Track route mix over time (`n_routed_slm`, `n_routed_llm`) to detect drift and re-calibrate \(\tau^*\) when route proportions or error patterns shift.

### 7.4 Runtime Output Schema

| Field | Description | Source |
|---|---|---|
| `prediction` | Model output \(\hat{y}\) (label, extracted structure, or generated text) | Smita raw output schema by use case |
| `routing_decision` | `SLM` or `LLM` after threshold comparison | SDDF runtime rule above |

Minimal runtime record:

```json
{
  "item_id": "UCx_###",
  "difficulty_score": 3.41,
  "tau_star": 3.85,
  "routing_decision": "SLM",
  "prediction": "THREAT"
}
```

### 7.5 What I Understand and What I Do Not Fully Understand Yet

**What I understand**

- Difficulty scoring must be computed using SDDF feature logic from Riddhima's repo (`sddf/difficulty.py`).
- \(\tau^*\) must come from SDDF v3 validation logic (`sddf/validation_dynamic.py`) and then be frozen for runtime deployment.
- Runtime contract for each input is exactly two required outputs: prediction and routing decision.
- For UC1 to UC7, the raw files support direct label-level runtime prediction traces.

**What I do not fully understand yet**

- UC8 runtime labeling is not directly compatible with the same class-based \(\tau^*\) and prediction schema because the persisted raw file is generation-first and does not store a unified class correctness field in the same format as UC1 to UC7.
- The production selection rule for choosing a single SLM per use case is not yet explicitly locked (best test SLM vs lowest-latency compliant SLM vs cost-constrained SLM). I used best test SLM as the current assumption.
- A live stream specification for runtime input ingestion (batch window, online update cadence for \(d\), and audit logging frequency) is not yet explicitly documented in Smita's repo.
