# Summarization Results Tables

## Capability Metrics

| Model | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Semantic Similarity | Compression Ratio | Hallucination Rate | Length Violation Rate | Information Loss Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `t5-small` | 0.1173 | 0.0592 | 0.0814 | 0.2682 | 0.0510 | 0.7000 | 0.3000 | 0.9333 |
| `sshleifer/distilbart-cnn-12-6` | 0.4343 | 0.2037 | 0.3127 | 0.7651 | 0.1977 | 0.3000 | 1.0000 | 0.8333 |
| `gemini-2.5-flash` `valid n=3 / 11 partial` | 0.3228 | 0.0523 | 0.2134 | 0.6699 | 0.0876 | 0.6667 | 1.0000 | 1.0000 |
| `gemini-3-flash-preview` `valid n=0 / 5` | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Operational Metrics

| Model | Avg Latency / Article | Throughput | Avg Memory Usage | Avg Input Tokens | Articles Evaluated | End-to-End Wall Time |
|---|---:|---:|---:|---:|---:|---:|
| `t5-small` | 0.7085 s | 15.3606 tokens/s | 681.99 MB | 318.03 | 30 | ~161.4 s |
| `sshleifer/distilbart-cnn-12-6` | 13.1839 s | 5.0467 tokens/s | 1171.08 MB | 313.80 | 30 | ~521.1 s |
| `gemini-2.5-flash` `valid n=3 / 11 partial` | 1.2036 s | 28.8190 tokens/s | API-managed | 340.33 | 3 valid of 11 partial | Partial run |
| `gemini-3-flash-preview` `valid n=0 / 5` | N/A | N/A | API-managed | N/A | 0 valid of 5 | Completed, but all outputs invalid |

## Notes

`gemini-2.5-flash` and `gemini-3-flash-preview` were filtered with stricter validation rules after the runs completed. A valid summary must contain at least 5 words and end with sentence punctuation.

Under that rule:

- `gemini-2.5-flash` retained 3 valid summaries out of 11 completed partial outputs.
- `gemini-3-flash-preview` retained 0 valid summaries out of 5 outputs because each output was a fragment rather than a complete sentence.
