from __future__ import annotations

import unittest

from codegen_eval.metrics import summarize_results
from codegen_eval.types import TaskRunResult


def _result(
    *,
    model_label: str,
    status: str,
    passed: bool,
    dataset: str = "MBPP",
    latency_seconds: float = 1.0,
    tokens_per_second: float = 2.0,
    output_tokens: int = 32,
    peak_ram_gb: float = 0.25,
    format_compliant: bool = True,
    signature_compliant: bool = True,
    instruction_adherent: bool = True,
) -> TaskRunResult:
    return TaskRunResult(
        model_label=model_label,
        model_name="example/model",
        dataset=dataset,
        task_id=f"{model_label}-{status}",
        attempted=True,
        completed=True,
        passed=passed,
        status=status,
        prompt="prompt",
        prompt_variant="default",
        entry_point="solve",
        raw_output="def solve(x):\n    return x",
        generated_code="def solve(x):\n    return x",
        latency_seconds=latency_seconds,
        tokens_per_second=tokens_per_second,
        output_tokens=output_tokens,
        input_tokens=16,
        estimated_cost=0.0,
        peak_ram_gb=peak_ram_gb,
        format_compliant=format_compliant,
        signature_compliant=signature_compliant,
        instruction_adherent=instruction_adherent,
        deterministic_reproducible=None,
        self_consistency_score=None,
        unsafe=False,
        error_message=None,
    )


class MetricsSummaryTests(unittest.TestCase):
    def test_summarize_results_aggregates_capability_and_operational_metrics(self) -> None:
        results = [
            _result(model_label="Model A", status="passed", passed=True, latency_seconds=2.0),
            _result(
                model_label="Model A",
                status="syntax_error",
                passed=False,
                latency_seconds=1.0,
                tokens_per_second=0.0,
                output_tokens=0,
                peak_ram_gb=0.0,
                format_compliant=False,
                signature_compliant=False,
                instruction_adherent=False,
            ),
        ]

        summary = summarize_results(results, time_budget_minutes=4)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["model"], "Model A")
        self.assertEqual(summary[0]["tasks_completed_in_budget"], 2)
        self.assertEqual(summary[0]["pass@1"], 0.5)
        self.assertEqual(summary[0]["syntax_error_rate"], 0.5)
        self.assertEqual(summary[0]["format_compliance"], 0.5)
        self.assertEqual(summary[0]["tokens_per_second"], 2.0)
        self.assertEqual(summary[0]["peak_ram_gb"], 0.25)


if __name__ == "__main__":
    unittest.main()
