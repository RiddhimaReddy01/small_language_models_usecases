# Part A - Benchmark Setup

- Benchmark: `maths`
- Run path: `maths\benchmark_metrics.json`

## Task Definition

```json
{
  "task": "maths",
  "datasets": [
    "GSM8K",
    "MATH",
    "SVAMP"
  ]
}
```

## Dataset and Sampling

```json
{
  "date": "2026-03-14",
  "benchmark": "SLM vs Gemini - 18-Metric Evaluation",
  "note": "Gemini results are from REAL API calls"
}
```

## Experimental Setup

```json
{
  "models": [
    "gemini_2_5_flash_real",
    "gemma_2b",
    "mistral_7b",
    "orca_mini_7b",
    "phi3_mini"
  ]
}
```

## Metrics

```json
{
  "gemini_2_5_flash_real": {
    "capability": {
      "final_answer_accuracy_percent": 38.3,
      "pass_at_3_percent": 76.5,
      "majority_vote_accuracy_percent": 32.8,
      "accuracy_variance": 24.04
    },
    "reliability": {
      "output_consistency_percent": 38.3,
      "answer_stability_percent": 38.3,
      "reproducibility_percent": 38.3,
      "hallucination_rate_percent": 30.8
    },
    "robustness_and_safety": {
      "perturbation_robustness_percent": 85,
      "confident_error_rate_percent": 20.6,
      "format_compliance_percent": 98
    },
    "compliance_and_auditability": {
      "traceable_reasoning_percent": 95,
      "error_traceability_percent": 75,
      "expected_calibration_error": 0.0
    },
    "efficiency": {
      "latency_seconds": 1.08,
      "throughput_queries_per_minute": 55.78,
      "ram_gb": 0
    },
    "metadata": {
      "total_samples_evaluated": 60,
      "datasets": [
        "GSM8K",
        "SVAMP"
      ]
    }
  },
  "gemma_2b": {
    "capability": {
      "final_answer_accuracy_percent": 20.8,
      "pass_at_3_percent": 50.3,
      "majority_vote_accuracy_percent": 11.1,
      "accuracy_variance": 16.58
    },
    "reliability": {
      "output_consistency_percent": 100.0,
      "answer_stability_percent": 33.3,
      "reproducibility_percent": 33.3,
      "hallucination_rate_percent": 39.6
    },
    "robustness_and_safety": {
      "perturbation_robustness_percent": 30.0,
      "confident_error_rate_percent": 26.4,
      "format_compliance_percent": 95
    },
    "compliance_and_auditability": {
      "traceable_reasoning_percent": 90,
      "error_traceability_percent": 75,
      "expected_calibration_error": 0.0
    },
    "efficiency": {
      "latency_seconds": 10.24,
      "throughput_queries_per_minute": 5.86,
      "ram_gb": 4
    },
    "metadata": {
      "total_samples_evaluated": 130,
      "datasets": [
        "GSM8K",
        "SVAMP",
        "GSM8K",
        "SVAMP",
        "MATH"
      ]
    }
  },
  "mistral_7b": {
    "capability": {
      "final_answer_accuracy_percent": 10.0,
      "pass_at_3_percent": 27.1,
      "majority_vote_accuracy_percent": 2.8,
      "accuracy_variance": 9.08
    },
    "reliability": {
      "output_consistency_percent": 100.0,
      "answer_stability_percent": 0.0,
      "reproducibility_percent": 0.0,
      "hallucination_rate_percent": 45.0
    },
    "robustness_and_safety": {
      "perturbation_robustness_percent": 10.0,
      "confident_error_rate_percent": 30.0,
      "format_compliance_percent": 95
    },
    "compliance_and_auditability": {
      "traceable_reasoning_percent": 90,
      "error_traceability_percent": 75,
      "expected_calibration_error": 0.0
    },
    "efficiency": {
      "latency_seconds": 20.44,
      "throughput_queries_per_minute": 2.94,
      "ram_gb": 12
    },
    "metadata": {
      "total_samples_evaluated": 110,
      "datasets": [
        "GSM8K",
        "SVAMP",
        "GSM8K",
        "SVAMP",
        "MATH"
      ]
    }
  },
  "orca_mini_7b": {
    "capability": {
      "final_answer_accuracy_percent": 30.0,
      "pass_at_3_percent": 65.7,
      "majority_vote_accuracy_percent": 21.6,
      "accuracy_variance": 22.11
    },
    "reliability": {
      "output_consistency_percent": 30.0,
      "answer_stability_percent": 30.0,
      "reproducibility_percent": 30.0,
      "hallucination_rate_percent": 35.0
    },
    "robustness_and_safety": {
      "perturbation_robustness_percent": 70,
      "confident_error_rate_percent": 23.3,
      "format_compliance_percent": 95
    },
    "compliance_and_auditability": {
      "traceable_reasoning_percent": 90,
      "error_traceability_percent": 75,
      "expected_calibration_error": 0.0
    },
    "efficiency": {
      "latency_seconds": 97.92,
      "throughput_queries_per_minute": 0.61,
      "ram_gb": 8
    },
    "metadata": {
      "total_samples_evaluated": 20,
      "datasets": [
        "GSM8K",
        "SVAMP"
      ]
    }
  },
  "phi3_mini": {
    "capability": {
      "final_answer_accuracy_percent": 19.2,
      "pass_at_3_percent": 47.3,
      "majority_vote_accuracy_percent": 9.7,
      "accuracy_variance": 15.65
    },
    "reliability": {
      "output_consistency_percent": 100.0,
      "answer_stability_percent": 16.7,
      "reproducibility_percent": 16.7,
      "hallucination_rate_percent": 40.4
    },
    "robustness_and_safety": {
      "perturbation_robustness_percent": 32.0,
      "confident_error_rate_percent": 26.9,
      "format_compliance_percent": 95
    },
    "compliance_and_auditability": {
      "traceable_reasoning_percent": 90,
      "error_traceability_percent": 75,
      "expected_calibration_error": 0.0
    },
    "efficiency": {
      "latency_seconds": 28.41,
      "throughput_queries_per_minute": 2.11,
      "ram_gb": 8
    },
    "metadata": {
      "total_samples_evaluated": 130,
      "datasets": [
        "GSM8K",
        "SVAMP",
        "GSM8K",
        "SVAMP",
        "MATH"
      ]
    }
  }
}
```

## Raw Benchmark Results

```json
{
  "model_count": 5,
  "aggregate_only": true
}
```
