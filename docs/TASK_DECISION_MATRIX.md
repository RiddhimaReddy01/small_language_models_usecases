# Task Decision Matrix

Primary routing matrix: sort candidates by model size, apply `tau_risk` first, then `tau_cap`.

| Task | Smallest candidate order | tau_risk | tau_cap | Binding gate | Routing policy |
|---|---|---:|---:|---|---|
| classification | hf_api:meta-llama/Llama-3.2-1B-Instruct -> gemini-3.1-flash-lite-preview | None | 4.404 | risk | Escalate to gemini-3.1-flash-lite-preview; hf_api:meta-llama/Llama-3.2-1B-Instruct fails the risk gate before size-based capability selection can begin. |
| maths | llama3_2_1b_hf -> gemini_flash | None | None | risk | Escalate to gemini_flash; llama3_2_1b_hf fails the risk gate before size-based capability selection can begin. |
| text_generation | hf_llama32_1b -> gemini-2.5-flash-fresh | None | 0.000 | risk | Escalate to gemini-2.5-flash-fresh; hf_llama32_1b fails the risk gate before size-based capability selection can begin. |
| summarization | meta-llama/Llama-3.2-1B-Instruct -> gemini-2.5-flash-lite | None | 375.000 | risk | Escalate to gemini-2.5-flash-lite; meta-llama/Llama-3.2-1B-Instruct fails the risk gate before size-based capability selection can begin. |
| information_extraction | Llama-3.2-1B-Instruct -> gemini-2.5-flash-lite | None | None | risk | Escalate to gemini-2.5-flash-lite; Llama-3.2-1B-Instruct fails the risk gate before size-based capability selection can begin. |
| retrieval_grounded | hf_api:meta-llama/Llama-3.2-1B-Instruct -> gemini/gemini-3.1-flash-lite-preview | None | None | risk | Escalate to gemini/gemini-3.1-flash-lite-preview; hf_api:meta-llama/Llama-3.2-1B-Instruct fails the risk gate before size-based capability selection can begin. |
| instruction_following | hf_api:meta-llama/Llama-3.2-1B-Instruct -> gemini-2.5-flash [BASELINE] | 0.000 | 0.000 | risk | Route to hf_api:meta-llama/Llama-3.2-1B-Instruct up to difficulty 0.000; escalate to gemini-2.5-flash [BASELINE] beyond that boundary. |
| code_generation | meta-llama/Llama-3.2-1B-Instruct -> gemini-2.5-flash | None | None | risk | Escalate to gemini-2.5-flash; meta-llama/Llama-3.2-1B-Instruct fails the risk gate before size-based capability selection can begin. |
