# Metrics Tables

## Capability Metrics

| Model | Avg Accuracy | Avg Macro F1 | Avg Weighted F1 | Avg Precision | Avg Recall | Avg Validity Rate |
|---|---:|---:|---:|---:|---:|---:|
| `gemma2:2b` | 0.8056 | 0.7302 | 0.7593 | 0.7083 | 0.7738 | 0.9444 |
| `phi3:mini` | 0.7500 | 0.6836 | 0.6836 | 0.6667 | 0.7500 | 1.0000 |
| `qwen2.5:1.5b` | 0.6389 | 0.5741 | 0.5741 | 0.5528 | 0.6389 | 1.0000 |
| `gemini-2.5-flash-lite` | 0.3889 | 0.3714 | 0.3873 | 0.3869 | 0.3730 | 0.5833 |

## Operational Metrics

| Model | Total Samples | Total Runtime (s) | Avg Throughput (samples/s) | Avg Mean Latency (s) | Avg P95 Latency (s) | Avg CPU Util (%) | Avg Mem Delta (MB) | Avg Parse Failure Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `gemini-2.5-flash-lite` | 16 | 4.16 | 4.8784 | 0.2449 | 0.3896 | 59.12 | 8.65 | 0.4167 |
| `qwen2.5:1.5b` | 16 | 12.63 | 1.2814 | 0.8258 | 1.0652 | 90.27 | 160.18 | 0.0000 |
| `gemma2:2b` | 16 | 23.44 | 0.7222 | 1.4722 | 2.6957 | 88.35 | -117.70 | 0.0556 |
| `phi3:mini` | 16 | 29.73 | 0.5547 | 1.9278 | 3.1425 | 40.92 | 469.37 | 0.0000 |
