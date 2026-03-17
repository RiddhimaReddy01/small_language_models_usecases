from __future__ import annotations

import unittest

import pandas as pd

from sddf.curves import compute_ratio_curve, smooth_ratio_curve
from sddf.difficulty import (
    annotate_dominant_dimension,
    compute_constraint_count,
    compute_entropy,
    compute_n_in,
    compute_reasoning_proxy,
    make_difficulty_bins,
)
from sddf.gates import apply_quality_gate, evaluate_quality_gate, label_slm_acceptability
from sddf.matching import match_model_outputs
from sddf.routing import learn_routing_thresholds, route_example, route_example_three_way
from sddf.tipping import estimate_tipping_point
from sddf.zones import assign_deployment_zone


class SddfCoreTests(unittest.TestCase):
    def test_difficulty_helpers(self) -> None:
        self.assertEqual(compute_n_in("a b c"), 3.0)
        self.assertAlmostEqual(compute_entropy("a a b"), 0.918295, places=5)
        self.assertEqual(
            compute_constraint_count(
                {
                    "required_fields": ["a", "b"],
                    "format_rules": ["json"],
                    "content_rules": ["no_pii"],
                    "length_rules": ["lt_50"],
                }
            ),
            5.0,
        )
        self.assertGreater(
            compute_reasoning_proxy({"question": "what is 2 plus 2", "num_steps": 2, "num_entities": 1}),
            0.0,
        )

    def test_annotate_and_bin_difficulty(self) -> None:
        df = pd.DataFrame(
            [
                {"example_id": "1", "input_text": "short text"},
                {"example_id": "2", "input_text": "a much longer piece of source text"},
                {"example_id": "3", "input_text": "medium source"},
            ]
        )
        annotated = annotate_dominant_dimension(df, task="summarization")
        self.assertTrue((annotated["difficulty_dim"] == "n_in").all())
        self.assertIn("difficulty_score", annotated.columns)

        binned = make_difficulty_bins(annotated, n_bins=2)
        self.assertIn("difficulty_bin", binned.columns)
        self.assertTrue(binned["difficulty_bin"].notna().all())

    def test_matching_curves_tipping_and_zones(self) -> None:
        results = pd.DataFrame(
            [
                {"example_id": "e1", "model_name": "slm", "difficulty_score": 1.0, "difficulty_bin": 0, "primary_metric": 0.98, "valid_output": 1, "latency_sec": 0.10},
                {"example_id": "e1", "model_name": "llm", "difficulty_score": 1.0, "difficulty_bin": 0, "primary_metric": 1.00, "valid_output": 1, "latency_sec": 0.30},
                {"example_id": "e2", "model_name": "slm", "difficulty_score": 2.0, "difficulty_bin": 1, "primary_metric": 0.90, "valid_output": 1, "latency_sec": 0.12},
                {"example_id": "e2", "model_name": "llm", "difficulty_score": 2.0, "difficulty_bin": 1, "primary_metric": 1.00, "valid_output": 1, "latency_sec": 0.31},
                {"example_id": "e3", "model_name": "slm", "difficulty_score": 3.0, "difficulty_bin": 2, "primary_metric": 0.70, "valid_output": 1, "latency_sec": 0.14},
                {"example_id": "e3", "model_name": "llm", "difficulty_score": 3.0, "difficulty_bin": 2, "primary_metric": 1.00, "valid_output": 1, "latency_sec": 0.32},
                {"example_id": "e4", "model_name": "slm", "difficulty_score": 4.0, "difficulty_bin": 3, "primary_metric": 0.60, "valid_output": 1, "latency_sec": 0.16},
                {"example_id": "e4", "model_name": "llm", "difficulty_score": 4.0, "difficulty_bin": 3, "primary_metric": 1.00, "valid_output": 1, "latency_sec": 0.33},
            ]
        )

        matched = match_model_outputs(results, "slm", "llm")
        curve = compute_ratio_curve(matched)
        smooth = smooth_ratio_curve(curve, method="rolling", frac=0.5)

        self.assertEqual(len(matched), 4)
        self.assertEqual(len(curve), 4)
        self.assertIn("ratio_smooth", smooth.columns)

        tip = estimate_tipping_point(smooth, threshold=0.95, require_consecutive=2)
        self.assertEqual(tip, 2.0)

        zone = assign_deployment_zone(smooth.iloc[-1], ratio_threshold_safe=0.95, ratio_threshold_hybrid=0.85)
        self.assertEqual(zone, "C")

    def test_quality_gate_and_routing(self) -> None:
        matched = pd.DataFrame(
            [
                {"difficulty_score": 1.0, "primary_metric_slm": 0.95, "valid_output_slm": 1, "latency_sec_slm": 0.10},
                {"difficulty_score": 2.0, "primary_metric_slm": 0.90, "valid_output_slm": 1, "latency_sec_slm": 0.12},
                {"difficulty_score": 3.0, "primary_metric_slm": 0.70, "valid_output_slm": 1, "latency_sec_slm": 0.14},
                {"difficulty_score": 4.0, "primary_metric_slm": 0.50, "valid_output_slm": 0, "latency_sec_slm": 0.16},
            ]
        )
        labeled = label_slm_acceptability(matched, quality_threshold=0.85)
        gated = apply_quality_gate(labeled, {"max_difficulty": 2.5, "max_latency_sec": 0.2})
        metrics = evaluate_quality_gate(gated)

        self.assertGreaterEqual(metrics["precision"], 0.5)
        self.assertGreaterEqual(metrics["recall"], 0.5)

        thresholds = learn_routing_thresholds(matched, target_precision=0.9)
        self.assertIsNotNone(thresholds)
        self.assertGreaterEqual(thresholds["max_difficulty"], 1.0)
        self.assertEqual(route_example({"difficulty_score": 1.0}, thresholds), "SLM")
        self.assertEqual(
            route_example_three_way({"difficulty_score": 2.0}, {"safe_max": 1.5, "hybrid_max": 2.5}),
            "SLM_WITH_GATE",
        )


if __name__ == "__main__":
    unittest.main()
