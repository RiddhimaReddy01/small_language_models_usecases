# Metrics Tables

## Capability Metrics

| Model | Total Tasks | Success Rate | Constraint Satisfaction | Format Compliance | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | Refusal Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-baseline | 15 | 1.0000 | 0.1667 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |
| phi-3.5-mini | 15 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |
| qwen-2.5-3b | 15 | 1.0000 | 0.1333 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |

## Operational Metrics

| Model | Successful Tasks | Failed Tasks | Avg TTFT (s) | Avg Total Time (s) | Avg Tokens | Avg TPS | Avg Peak RAM MB | Avg Load Time (s) | Total Cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-baseline | 15 | 0 | 1.1757 | 5.8787 | 155.4800 | 39.0056 | 0.0000 | 0.0010 | 0.0002 |
| phi-3.5-mini | 15 | 0 | 0.8435 | 45.6180 | 402.8667 | 9.1310 | 3035.5568 | 3.2469 | 0.0000 |
| qwen-2.5-3b | 15 | 0 | 0.5061 | 22.1081 | 241.8667 | 10.8736 | 2486.0938 | 6.1511 | 0.0000 |
