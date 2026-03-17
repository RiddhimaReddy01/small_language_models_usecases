from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
import shutil

from sddf.ingest import (
    infer_model_family,
    normalize_classification_results,
    normalize_code_generation_results,
    normalize_ie_predictions,
    normalize_instruction_following_results,
    normalize_maths_results,
    normalize_retrieval_grounded_predictions,
    normalize_summarization_results,
    normalize_text_generation_results,
)
from sddf.pipeline import run_sddf_postprocess


class SddfIngestPipelineTests(unittest.TestCase):
    def test_infer_model_family(self) -> None:
        self.assertEqual(infer_model_family("gemini-2.5-flash", provider="google"), "LLM")
        self.assertEqual(infer_model_family("phi3:mini", provider="ollama"), "SLM")

    def test_normalizers_and_archive(self) -> None:
        classification_rows = normalize_classification_results(
            [
                {
                    "dataset": "demo",
                    "text": "great movie",
                    "true_label": "positive",
                    "prediction": "positive",
                    "latency": 0.5,
                    "is_valid": True,
                    "status": "success",
                }
            ],
            model_name="phi3:mini",
            run_metadata={"model": "phi3:mini"},
        )
        self.assertEqual(classification_rows.iloc[0]["primary_metric"], 1.0)

        textgen_rows = normalize_text_generation_results(
            [
                {
                    "task_id": 1,
                    "run_id": 0,
                    "task_type": "samples",
                    "prompt": "Write 3 bullets about AI",
                    "response": "- fast\n- useful\n- local",
                    "reference": "three bullets",
                    "metrics": {
                        "operational": {"total_time": 0.8, "peak_ram_mb": 128},
                        "framework": {"instruction_following": {"constraint_satisfaction_rate": 1.0}},
                    },
                }
            ],
            metadata={"model_name": "gemini-2.5-flash", "model_type": "google", "task_type": "samples"},
        )
        self.assertEqual(textgen_rows.iloc[0]["model_family"], "LLM")

        config = SimpleNamespace(
            dataset=SimpleNamespace(name="cnn_dailymail", config_name="3.0.0"),
            model=SimpleNamespace(model_name="distilbart-cnn", provider="huggingface", word_limit=60),
        )
        summarization_rows = normalize_summarization_results(
            [
                {
                    "sample_id": "a1",
                    "generated_summary": "Short summary",
                    "reference_summary": "Reference summary",
                    "article": "Long article text here",
                    "latency_seconds": 1.2,
                    "memory_mb": 512,
                    "rouge_1_f1": 0.42,
                    "length_violation_flag": 0,
                    "reference_words": 12,
                    "summary_words": 9,
                    "output_tokens": 20,
                    "hallucination_flag": 0,
                    "information_loss_flag": 0,
                }
            ],
            config,
        )
        self.assertEqual(summarization_rows.iloc[0]["task"], "summarization")

        instruction_rows = normalize_instruction_following_results(
            [
                {
                    "model": "Qwen/Qwen2.5-Coder-0.5B",
                    "responses": [
                        {
                            "instruction": "Answer in 5 words",
                            "response": "AI can help people daily",
                            "constraints_satisfied": 1,
                            "total_constraints": 1,
                            "pass": True,
                            "latency_sec": 0.4,
                            "output_tokens": 5,
                        }
                    ],
                }
            ]
        )
        self.assertEqual(instruction_rows.iloc[0]["task"], "instruction_following")

        code_rows = normalize_code_generation_results(
            [
                {
                    "model_name": "mistral:7b",
                    "dataset": "HumanEval",
                    "task_id": "HumanEval/1",
                    "generated_code": "def foo():\n    return 1",
                    "passed": False,
                    "format_compliant": True,
                    "latency_seconds": 1.1,
                    "peak_ram_gb": 0.5,
                    "prompt": "Write a function",
                    "entry_point": "foo",
                }
            ]
        )
        self.assertEqual(code_rows.iloc[0]["task"], "code_generation")

        maths_rows = normalize_maths_results(
            {
                "experiments": [
                    {
                        "model": "gemma_2b",
                        "dataset": "gsm8k",
                        "records": [
                            {
                                "question": "What is 2+2?",
                                "difficulty": "easy",
                                "source": "gsm8k",
                                "base": {
                                    "request_id": "gsm8k:gemma:0:base",
                                    "status": "ok",
                                    "latency": 0.5,
                                    "prediction": "4",
                                    "gold": "4",
                                    "correct": True,
                                },
                            }
                        ],
                    }
                ]
            }
        )
        self.assertEqual(maths_rows.iloc[0]["task"], "maths")

        retrieval_rows = normalize_retrieval_grounded_predictions(
            {
                "qwen": [
                    {
                        "id": "1",
                        "prediction": "Denver Broncos",
                        "reference": "Denver Broncos",
                        "context": "Super Bowl context",
                        "latency_sec": 0.9,
                        "input_tokens": 20,
                        "output_tokens": 3,
                        "memory_mb": 0.0,
                    }
                ]
            }
        )
        self.assertEqual(retrieval_rows.iloc[0]["primary_metric"], 1.0)

        ie_rows = normalize_ie_predictions(
            [
                {
                    "model": "SmolLM2-1.7B-Instruct",
                    "doc_id": "doc1",
                    "split": "clean",
                    "text": "Invoice total 10.00",
                    "prediction": {"total": "10.00"},
                    "reference_fields": {"total": "10.00"},
                    "schema_valid": True,
                    "latency_seconds": 0.8,
                    "input_tokens": 30,
                    "output_tokens": 5,
                    "raw_output": "{\"total\":\"10.00\"}",
                    "backend_metadata": {},
                }
            ],
            ["total"],
        )
        self.assertEqual(ie_rows.iloc[0]["task"], "information_extraction")

        tmpdir = Path("tests/.tmp_sddf_ingest")
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            first = run_sddf_postprocess(classification_rows, task="classification", output_dir=tmpdir)
            second = run_sddf_postprocess(textgen_rows, task="text_generation", output_dir=tmpdir)
            self.assertTrue(Path(first["archive_path"]).exists())
            self.assertTrue(Path(second["archive_path"]).exists())
        finally:
            if tmpdir.exists():
                shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()
