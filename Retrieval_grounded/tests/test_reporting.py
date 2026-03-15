import shutil
from pathlib import Path

from src.reporting import generate_markdown_summary, save_metric_tables


def _sample_results() -> dict:
    return {
        "model-a": {
            "capability": {
                "exact_match": 66.6666,
                "f1_score": 71.25,
                "context_utilization_rate": 96.66,
                "answer_length_accuracy": 86.66,
            },
            "operational": {
                "latency_ms": 1000.0,
                "latency_p50_ms": 900.0,
                "latency_p95_ms": 1400.0,
                "tokens_per_sec": 5.5,
                "output_tokens_total": 42,
                "input_tokens_avg": 100.0,
                "memory_mb": 256.0,
                "wall_time_sec": 12.0,
                "questions": 2,
            },
        }
    }


def test_generate_markdown_summary_contains_metric_sections():
    report = generate_markdown_summary(_sample_results())
    assert "## Capability Metrics" in report
    assert "## Operational Metrics" in report
    assert "model-a" in report


def test_save_metric_tables_writes_expected_files():
    tmp_path = Path("tests/.tmp_reporting")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)

    save_metric_tables(
        tmp_path,
        _sample_results(),
        {"dataset_name": "squad", "num_questions": 2, "device": "cpu", "temperature": 0.0, "do_sample": False},
        {"platform": "test-platform", "python_version": "3.11", "torch_version": "2.x", "transformers_version": "4.x"},
    )

    expected_files = {
        "capability_metrics.md",
        "operational_metrics.md",
        "capability_metrics.csv",
        "operational_metrics.csv",
        "report.md",
        "reproducibility.md",
    }
    assert expected_files.issubset({path.name for path in tmp_path.iterdir()})
    assert "Exact Match (%)" in (tmp_path / "capability_metrics.md").read_text(encoding="utf-8")
    assert "Platform: test-platform" in (tmp_path / "reproducibility.md").read_text(encoding="utf-8")
    shutil.rmtree(tmp_path)
