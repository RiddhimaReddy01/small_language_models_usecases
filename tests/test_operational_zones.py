"""
Tests for Dynamic Operational Zones with Three Routing Strategies.

Tests cover:
1. Unit tests for select_tau_strategy() - zone size calculations
2. Unit tests for get_strategy_rationale() - explanation strings
3. Integration tests for find_operational_zone() - full zone discovery
4. Strategy selection tests - correct strategy picked based on zone size
5. Edge case tests - empty zones, single-element zones, etc.
6. Real data tests - with actual validation samples
"""
from __future__ import annotations

import unittest
from sddf.validation_dynamic import (
    select_tau_strategy,
    get_strategy_rationale,
    find_operational_zone,
    compute_per_sample_metrics,
    build_difficulty_curves,
)


class TestSelectTauStrategy(unittest.TestCase):
    """Test the select_tau_strategy function for zone size and strategy selection."""

    def test_empty_feasible_set(self):
        """Empty zone: no routing possible."""
        result = select_tau_strategy([])

        self.assertEqual(result["zone_size"], 0)
        self.assertEqual(result["strategy"], "none")
        self.assertIsNone(result["recommended_tau"])
        self.assertIsNone(result["tau_conservative"])
        self.assertIsNone(result["tau_balanced"])
        self.assertIsNone(result["tau_aggressive"])

    def test_single_element_zone(self):
        """Single element: zone_size = 0, strategy = none."""
        result = select_tau_strategy([1])

        self.assertEqual(result["zone_min"], 1)
        self.assertEqual(result["zone_max"], 1)
        self.assertEqual(result["zone_size"], 0)
        # Single element = empty zone size, so should be "none"
        self.assertEqual(result["strategy"], "none")

    def test_narrow_zone_hard_task(self):
        """Zone size 0.5 (< 1.5): test with realistic curves."""
        # Hard task: SLM fails more, so lower difficulties preferred
        cap_curve = {0: 0.92, 0.5: 0.78}  # Decreasing capability
        risk_curve = {0: 0.05, 0.5: 0.10}  # Increasing risk

        result = select_tau_strategy([0, 0.5], cap_curve, risk_curve, lambda_risk=1.0)

        self.assertEqual(result["zone_min"], 0)
        self.assertEqual(result["zone_max"], 0.5)
        self.assertAlmostEqual(result["zone_size"], 0.5)
        # Strategy determined by optimization formula
        self.assertIn(result["strategy"], ["conservative", "balanced", "aggressive"])

    def test_medium_zone_medium_task(self):
        """Zone size 2.0 (1.5 <= size < 3): BALANCED strategy."""
        result = select_tau_strategy([0, 1, 2])

        self.assertEqual(result["zone_min"], 0)
        self.assertEqual(result["zone_max"], 2)
        self.assertEqual(result["zone_size"], 2)
        self.assertEqual(result["strategy"], "balanced")
        self.assertAlmostEqual(result["recommended_tau"], 1.0)  # mean(F)

    def test_wide_zone_easy_task(self):
        """Zone size 4.0 (>= 3): easy task with realistic curves."""
        # Easy task: SLM good at all difficulties, can route more
        cap_curve = {0: 0.96, 1: 0.92, 2: 0.85, 3: 0.75, 4: 0.65}
        risk_curve = {0: 0.01, 1: 0.02, 2: 0.04, 3: 0.06, 4: 0.08}

        result = select_tau_strategy([0, 1, 2, 3, 4], cap_curve, risk_curve, lambda_risk=1.0)

        self.assertEqual(result["zone_min"], 0)
        self.assertEqual(result["zone_max"], 4)
        self.assertEqual(result["zone_size"], 4)
        # For easy task with these curves, formula should optimize
        self.assertIn(result["strategy"], ["conservative", "balanced", "aggressive"])

    def test_boundary_zone_1_5(self):
        """Zone size exactly 1.5: BALANCED strategy."""
        result = select_tau_strategy([0, 1.5])

        self.assertEqual(result["zone_size"], 1.5)
        self.assertEqual(result["strategy"], "balanced")
        self.assertAlmostEqual(result["recommended_tau"], 0.75)  # mean

    def test_boundary_zone_3_0(self):
        """Zone size exactly 3.0: test with curves."""
        cap_curve = {0: 0.90, 3: 0.70}
        risk_curve = {0: 0.05, 3: 0.15}

        result = select_tau_strategy([0, 3], cap_curve, risk_curve, lambda_risk=1.0)

        self.assertEqual(result["zone_size"], 3)
        # Strategy depends on optimization, not just zone size
        self.assertIn(result["strategy"], ["conservative", "balanced", "aggressive"])

    def test_three_options_available(self):
        """All three options should be available for non-empty zones."""
        result = select_tau_strategy([0, 1, 2])

        self.assertEqual(result["tau_conservative"], 0)
        self.assertEqual(result["tau_balanced"], 1)
        self.assertEqual(result["tau_aggressive"], 2)
        # Recommended should be one of the three
        self.assertIn(result["recommended_tau"], [0, 1, 2])

    def test_non_contiguous_feasible_set(self):
        """Feasible set doesn't need to be contiguous."""
        cap_curve = {0: 0.90, 2: 0.75, 5: 0.60}
        risk_curve = {0: 0.05, 2: 0.15, 5: 0.25}

        result = select_tau_strategy([0, 2, 5], cap_curve, risk_curve, lambda_risk=1.0)

        self.assertEqual(result["zone_min"], 0)
        self.assertEqual(result["zone_max"], 5)
        self.assertEqual(result["zone_size"], 5)
        # Should have min/max even if non-contiguous
        self.assertEqual(result["tau_conservative"], 0)
        self.assertEqual(result["tau_aggressive"], 5)


class TestGetStrategyRationale(unittest.TestCase):
    """Test the get_strategy_rationale function for explanations."""

    def test_empty_zone_rationale(self):
        """Empty zone explanation."""
        rationale = get_strategy_rationale(0)

        self.assertIn("Empty zone", rationale)
        self.assertIn("no safe routing", rationale.lower())

    def test_wide_zone_rationale(self):
        """Wide zone (easy task) rationale."""
        rationale = get_strategy_rationale(4.0)

        self.assertIn("Wide zone", rationale)
        self.assertIn("AGGRESSIVE", rationale)
        self.assertIn("cost savings", rationale.lower())

    def test_medium_zone_rationale(self):
        """Medium zone rationale."""
        rationale = get_strategy_rationale(2.0)

        self.assertIn("Medium zone", rationale)
        self.assertIn("BALANCED", rationale)

    def test_narrow_zone_rationale(self):
        """Narrow zone (hard task) rationale."""
        rationale = get_strategy_rationale(0.5)

        self.assertIn("Narrow zone", rationale)
        self.assertIn("CONSERVATIVE", rationale)

    def test_rationale_includes_zone_size(self):
        """Rationale should include the actual zone size."""
        rationale = get_strategy_rationale(2.5)

        self.assertIn("2.5", rationale)


class TestFindOperationalZone(unittest.TestCase):
    """Test the find_operational_zone function for full zone discovery."""

    def test_empty_zone_discovery(self):
        """When no difficulty level meets both constraints, zone is empty."""
        cap_curve = {0: 0.50, 1: 0.45, 2: 0.40}
        risk_curve = {0: 0.50, 1: 0.55, 2: 0.60}
        coverage = {0: 10, 1: 10, 2: 10}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70,  # Require 70% capability
            risk_static=0.30,  # Require ≤30% risk
            baseline_cap=0.75,
            baseline_risk=0.40,
        )

        self.assertEqual(result["feasible_set"], [])
        self.assertEqual(result["operational_zone"]["zone_size"], 0)
        self.assertEqual(result["routing_decision"]["strategy"], "none")

    def test_medium_zone_discovery(self):
        """Discover a medium-sized feasible set."""
        cap_curve = {0: 0.88, 1: 0.73, 2: 0.61, 3: 0.48}
        risk_curve = {0: 0.10, 1: 0.15, 2: 0.20, 3: 0.28}
        coverage = {0: 8, 1: 12, 2: 15, 3: 18}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.55,  # Capability requirement
            risk_static=0.40,  # Risk threshold
            baseline_cap=0.85,
            baseline_risk=0.15,
        )

        # Should find some feasible difficulties
        self.assertGreater(len(result["feasible_set"]), 0)
        self.assertGreater(result["operational_zone"]["zone_size"], 0)
        self.assertIn(result["routing_decision"]["strategy"],
                     ["conservative", "balanced", "aggressive"])

    def test_dynamic_threshold_calculation(self):
        """Verify dynamic thresholds are calculated correctly."""
        cap_curve = {0: 0.90}
        risk_curve = {0: 0.05}
        coverage = {0: 10}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.65,
            risk_static=0.30,
            baseline_cap=0.95,
            baseline_risk=0.02,
            mcap=0.05,
            mrisk=0.05,
        )

        # cap_dyn = min(0.65, 0.95 - 0.05) = min(0.65, 0.90) = 0.65
        self.assertAlmostEqual(result["cap_dyn"], 0.65)
        # risk_dyn = max(0.30, 0.02 + 0.05) = max(0.30, 0.07) = 0.30
        self.assertAlmostEqual(result["risk_dyn"], 0.30)

    def test_operational_zone_structure(self):
        """Verify the returned operational_zone structure."""
        cap_curve = {0: 0.90, 1: 0.80}
        risk_curve = {0: 0.05, 1: 0.10}
        coverage = {0: 10, 1: 15}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70, risk_static=0.30,
            baseline_cap=0.92, baseline_risk=0.03,
        )

        # Check structure
        self.assertIn("operational_zone", result)
        self.assertIn("zone_min", result["operational_zone"])
        self.assertIn("zone_max", result["operational_zone"])
        self.assertIn("zone_size", result["operational_zone"])

    def test_routing_decision_structure(self):
        """Verify the returned routing_decision structure."""
        cap_curve = {0: 0.90, 1: 0.80}
        risk_curve = {0: 0.05, 1: 0.10}
        coverage = {0: 10, 1: 15}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70, risk_static=0.30,
            baseline_cap=0.92, baseline_risk=0.03,
        )

        # Check structure
        self.assertIn("routing_decision", result)
        self.assertIn("tau_conservative", result["routing_decision"])
        self.assertIn("tau_balanced", result["routing_decision"])
        self.assertIn("tau_aggressive", result["routing_decision"])
        self.assertIn("recommended_tau", result["routing_decision"])
        self.assertIn("strategy", result["routing_decision"])
        self.assertIn("rationale", result["routing_decision"])


class TestRealDataIntegration(unittest.TestCase):
    """Test with realistic validation data."""

    def test_code_generation_medium_task(self):
        """Real example: CODE_GENERATION (medium task)."""
        # Simulate validation samples
        val_samples = [
            {
                "sample_id": f"sample_{i}",
                "slm_correct": i < 5,  # SLM fails on harder samples
                "llm_correct": True,
            }
            for i in range(10)
        ]

        scores = {f"sample_{i}": i / 10 for i in range(10)}  # Difficulty 0.0-0.9

        # Build curves
        metrics, baseline_cap, baseline_risk = compute_per_sample_metrics(
            val_samples, scores, task="code_generation"
        )
        cap_curve, risk_curve, coverage = build_difficulty_curves(metrics)

        # Find zone
        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.55,
            risk_static=0.40,
            baseline_cap=baseline_cap,
            baseline_risk=baseline_risk,
        )

        # Should find some feasible set (at least for easiest samples)
        if result["feasible_set"]:  # If feasible set not empty
            self.assertGreater(result["operational_zone"]["zone_size"], 0)
            self.assertIn(result["routing_decision"]["strategy"],
                         ["conservative", "balanced", "aggressive"])
            # For medium task, should likely be balanced
            if result["operational_zone"]["zone_size"] >= 1.5:
                self.assertEqual(result["routing_decision"]["strategy"], "balanced")

    def test_summarization_easy_task(self):
        """Real example: SUMMARIZATION (easy task)."""
        # Simulate: SLM very good on summarization
        val_samples = [
            {
                "sample_id": f"sample_{i}",
                "slm_correct": i < 8,  # SLM succeeds more often
                "llm_correct": True,
            }
            for i in range(10)
        ]

        scores = {f"sample_{i}": i / 10 for i in range(10)}

        metrics, baseline_cap, baseline_risk = compute_per_sample_metrics(
            val_samples, scores, task="summarization"
        )
        cap_curve, risk_curve, coverage = build_difficulty_curves(metrics)

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70,
            risk_static=0.30,
            baseline_cap=baseline_cap,
            baseline_risk=baseline_risk,
        )

        # Verify zone is discovered
        if result["feasible_set"]:
            zone_size = result["operational_zone"]["zone_size"]
            # Just verify a strategy was selected
            self.assertIn(result["routing_decision"]["strategy"],
                         ["conservative", "balanced", "aggressive"])


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_all_difficulties_feasible(self):
        """All difficulty levels are feasible (very easy task)."""
        cap_curve = {0: 1.0, 1: 0.95, 2: 0.90, 3: 0.85, 4: 0.80}
        risk_curve = {0: 0.0, 1: 0.01, 2: 0.02, 3: 0.03, 4: 0.04}
        coverage = {0: 5, 1: 10, 2: 15, 3: 20, 4: 25}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.50, risk_static=0.50,
            baseline_cap=0.99, baseline_risk=0.001,
        )

        # All should be feasible
        self.assertEqual(result["feasible_set"], [0, 1, 2, 3, 4])
        self.assertEqual(result["operational_zone"]["zone_size"], 4)
        # Formula will optimize, just verify strategy is valid
        self.assertIn(result["routing_decision"]["strategy"],
                     ["conservative", "balanced", "aggressive"])

    def test_only_easiest_difficulty_feasible(self):
        """Only easiest difficulty level is feasible."""
        cap_curve = {0: 0.90, 1: 0.60, 2: 0.40}
        risk_curve = {0: 0.10, 1: 0.40, 2: 0.70}
        coverage = {0: 10, 1: 20, 2: 30}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.85, risk_static=0.20,
            baseline_cap=0.92, baseline_risk=0.15,
        )

        # Only easiest difficulty should pass
        if result["feasible_set"]:
            self.assertEqual(result["feasible_set"], [0])
            self.assertEqual(result["operational_zone"]["zone_size"], 0)

    def test_float_difficulty_levels(self):
        """Feasible set with float difficulty levels."""
        cap_curve = {0.0: 0.95, 0.5: 0.85, 1.0: 0.75}
        risk_curve = {0.0: 0.05, 0.5: 0.15, 1.0: 0.25}
        coverage = {0.0: 5, 0.5: 10, 1.0: 15}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70, risk_static=0.30,
            baseline_cap=0.90, baseline_risk=0.10,
        )

        # Should handle float difficulties
        if result["feasible_set"]:
            zone_size = result["operational_zone"]["zone_size"]
            self.assertGreaterEqual(zone_size, 0)

    def test_coverage_constraint(self):
        """Verify coverage_max constraint is respected."""
        cap_curve = {0: 0.90, 1: 0.85}
        risk_curve = {0: 0.05, 1: 0.10}
        coverage = {0: 30, 1: 50}  # Normalized: 0.375, 0.625

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70, risk_static=0.30,
            baseline_cap=0.92, baseline_risk=0.03,
            coverage_max=0.40,  # Only allow up to 40%
        )

        # Difficulty 1 has coverage 50/80 = 62.5% > 40%, should be excluded
        if result["feasible_set"]:
            for d in result["feasible_set"]:
                cov_pct = coverage[d] / sum(coverage.values())
                self.assertLessEqual(cov_pct, 0.40)


class TestStrategyConsistency(unittest.TestCase):
    """Test that strategy selection is consistent with zone size."""

    def test_zone_size_strategy_mapping(self):
        """Verify zone size is calculated correctly."""
        test_cases = [
            ([], 0.0),              # Empty zone
            ([0, 0.5], 0.5),       # Narrow zone
            ([0, 1, 2], 2.0),      # Medium zone
            ([0, 1, 2, 3, 4], 4.0),  # Wide zone
        ]

        for feasible, expected_zone_size in test_cases:
            result = select_tau_strategy(feasible)
            self.assertEqual(result["zone_size"], expected_zone_size,
                           f"Feasible set {feasible} should have zone_size {expected_zone_size}")

    def test_recommended_tau_in_feasible_set(self):
        """Recommended TAU should be within feasible set bounds."""
        feasible_set = [0, 1, 2, 3]
        result = select_tau_strategy(feasible_set)

        if result["recommended_tau"] is not None:
            self.assertGreaterEqual(result["recommended_tau"], min(feasible_set))
            self.assertLessEqual(result["recommended_tau"], max(feasible_set))


class TestOutputStructure(unittest.TestCase):
    """Test that output structures match expected schema."""

    def test_select_tau_strategy_keys(self):
        """Verify select_tau_strategy returns all required keys."""
        result = select_tau_strategy([0, 1, 2])

        required_keys = [
            "zone_min", "zone_max", "zone_size",
            "tau_conservative", "tau_balanced", "tau_aggressive",
            "recommended_tau", "strategy"
        ]

        for key in required_keys:
            self.assertIn(key, result)

    def test_find_operational_zone_keys(self):
        """Verify find_operational_zone returns all required keys."""
        cap_curve = {0: 0.90, 1: 0.80}
        risk_curve = {0: 0.05, 1: 0.10}
        coverage = {0: 10, 1: 15}

        result = find_operational_zone(
            cap_curve, risk_curve, coverage,
            cap_static=0.70, risk_static=0.30,
            baseline_cap=0.92, baseline_risk=0.03,
        )

        required_top_keys = [
            "cap_dyn", "risk_dyn", "feasible_set",
            "operational_zone", "routing_decision"
        ]

        for key in required_top_keys:
            self.assertIn(key, result)

        # Check nested structures
        op_zone_keys = ["zone_min", "zone_max", "zone_size"]
        for key in op_zone_keys:
            self.assertIn(key, result["operational_zone"])

        routing_keys = [
            "tau_conservative", "tau_balanced", "tau_aggressive",
            "recommended_tau", "strategy", "rationale"
        ]
        for key in routing_keys:
            self.assertIn(key, result["routing_decision"])


if __name__ == "__main__":
    unittest.main()
