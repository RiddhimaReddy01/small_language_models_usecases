# Summarization Results Tables

## Capability Metrics Results

| Run | Model | Articles | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Semantic Similarity | Compression Ratio | Hallucination Rate | Length Violation Rate | Information Loss Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Default | `sshleifer/distilbart-cnn-12-6` | 30 | 0.4343 | 0.2037 | 0.3127 | 0.7651 | 0.1977 | 0.3000 | 1.0000 | 0.8333 |
| Fast CPU | `t5-small` | 30 | 0.1173 | 0.0592 | 0.0814 | 0.2682 | 0.0510 | 0.7000 | 0.3000 | 0.9333 |
| Gemini 3 Flash Fast | `gemini-3-flash-preview` | 5 | 0.0083 | 0.0000 | 0.0083 | 0.0816 | 0.0030 | 0.8000 | 0.0000 | 1.0000 |
| Gemini Flash Partial | `gemini-2.5-flash` | 11 partial | 0.1227 | 0.0181 | 0.0884 | 0.3760 | 0.0277 | 0.4545 | 0.2727 | 1.0000 |

## Operational Metrics Results

| Run | Model | Articles | Avg Latency / Article | Throughput | Avg Memory Usage | Avg Input Tokens | End-to-End Wall Time |
|---|---|---:|---:|---:|---:|---:|---:|
| Default | `sshleifer/distilbart-cnn-12-6` | 30 | 13.1839 s | 5.0467 tokens/s | 1171.08 MB | 313.80 | ~395.5 s |
| Fast CPU | `t5-small` | 30 | 0.7085 s | 15.3606 tokens/s | 681.99 MB | 318.03 | ~21.3 s |
| Gemini 3 Flash Fast | `gemini-3-flash-preview` | 5 | 1.0551 s | 0.9642 tokens/s | API-managed | 334.20 | ~5.3 s |
| Gemini Flash Partial | `gemini-2.5-flash` | 11 partial | 0.8994 s | 9.4939 tokens/s | API-managed | 329.45 | Partial run |

## Notes

- Capability metrics capture quality and reliability behavior.
- Operational metrics capture runtime, throughput, memory, and input size.
- `Gemini Flash Partial` is based on a partial run with 11 completed articles.
- API-backed runs use `API-managed` memory because local process memory is not comparable to local Hugging Face model memory.
