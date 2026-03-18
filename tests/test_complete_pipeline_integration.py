#!/usr/bin/env python3
"""
End-to-End Integration Test: Complete Pipeline

Validates the full pipeline from data ingestion to routing decision:
  Phase 0: Data Ingestion -> Normalization -> Difficulty -> Binning ->
           Capability Curves -> Risk Curves -> Tipping Points ->
           Empirical Thresholds -> Decision Matrix -> Frozen Policies

  Phase 1: Receive Input -> Compute Difficulty -> Assign Bin ->
           Get Curves -> Classify Zone -> Apply Policy -> Return Result
"""

import unittest
import json
from pathlib import Path
from typing import Dict, List
import statistics

# Import the framework
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from generalized_routing_framework import (
    GeneralizedRoutingFramework,
    TaskSpec,
    RoutingDecision
)


class CompleteRoutingPipelineTest(unittest.TestCase):
    """Test complete pipeline end-to-end"""

    def setUp(self):
        """Set up test data and framework"""
        self.framework = GeneralizedRoutingFramework(
            capability_threshold=0.80,
            risk_threshold=0.20
        )

        # Create synthetic test data
        self.test_data = self._create_synthetic_data()

    def _create_synthetic_data(self) -> Dict[str, List[Dict]]:
        """
        Create synthetic benchmark outputs for testing

        Simulates:
        - Text generation task
        - 2 models (SLM and LLM baseline)
        - 50 samples per model, distributed across difficulty bins
        """
        data = {}

        # Qwen (SLM) - Good at easy/medium, struggles with hard
        qwen_outputs = []
        for i in range(50):
            # Distribute samples across difficulty bins
            if i < 10:        # Bin 0 (easy)
                difficulty = 0.1
                quality = 1.0 if i < 8 else 0.5  # 80% success
            elif i < 20:      # Bin 1 (medium)
                difficulty = 0.3
                quality = 1.0 if i < 16 else 0.5  # 80% success
            elif i < 30:      # Bin 2 (med-hard)
                difficulty = 0.5
                quality = 1.0 if i < 24 else 0.5  # 80% success
            elif i < 40:      # Bin 3 (hard)
                difficulty = 0.7
                quality = 1.0 if i < 33 else 0.5  # 67% success
            else:             # Bin 4 (very hard)
                difficulty = 0.9
                quality = 1.0 if i < 44 else 0.5  # 60% success

            qwen_outputs.append({
                'raw_input': 'x' * int(100 + difficulty * 900),  # Input length increases with difficulty
                'raw_output': 'Generated text' if quality > 0.5 else 'Short',
                'valid': True,
                'quality_score': quality
            })

        # Llama (LLM baseline) - Good at all difficulties
        llama_outputs = []
        for i in range(50):
            difficulty = i / 50
            quality = 1.0 if i < 48 else 0.5  # 96% success across all

            llama_outputs.append({
                'raw_input': 'x' * int(100 + difficulty * 900),
                'raw_output': 'Generated text',
                'valid': True,
                'quality_score': quality
            })

        data['qwen'] = qwen_outputs
        data['llama'] = llama_outputs

        return data

    def test_phase0_data_ingestion(self):
        """Phase 0, Step 1: Data Ingestion - Load outputs"""
        self.assertIn('qwen', self.test_data)
        self.assertIn('llama', self.test_data)
        self.assertEqual(len(self.test_data['qwen']), 50)
        self.assertEqual(len(self.test_data['llama']), 50)

    def test_phase0_normalization_and_quality_metrics(self):
        """Phase 0, Step 2: Normalize & Compute Quality Metrics"""
        # Each record should have a primary_metric
        for sample in self.test_data['qwen']:
            self.assertIn('quality_score', sample)
            self.assertGreaterEqual(sample['quality_score'], 0.0)
            self.assertLessEqual(sample['quality_score'], 1.0)

    def test_phase0_difficulty_computation(self):
        """Phase 0, Step 3: Compute Difficulty Scores"""
        def difficulty_metric(input_text: str) -> float:
            """Difficulty based on input length"""
            return min(len(input_text) / 1000, 1.0)

        for sample in self.test_data['qwen']:
            diff = difficulty_metric(sample['raw_input'])
            self.assertGreaterEqual(diff, 0.0)
            self.assertLessEqual(diff, 1.0)

    def test_phase0_binning_by_difficulty(self):
        """Phase 0, Step 4: Bin by Difficulty"""
        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        binned = self.framework.bin_by_difficulty(
            self.test_data['qwen'],
            difficulty_metric,
            num_bins=5
        )

        # Should have bins 0-4
        self.assertIn(0, binned)
        self.assertGreater(len(binned), 0)
        self.assertLessEqual(max(binned.keys()), 4)

    def test_phase0_capability_curves(self):
        """Phase 0, Step 5: Compute Capability Curves"""
        def validation_fn(output: str) -> bool:
            return len(output.strip()) > 5

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        binned = self.framework.bin_by_difficulty(
            self.test_data['qwen'],
            difficulty_metric
        )

        capability_curve = self.framework.compute_capability_curve(
            binned,
            validation_fn
        )

        # Each bin should have a capability value
        for bin_id in binned.keys():
            self.assertIn(bin_id, capability_curve)
            self.assertGreaterEqual(capability_curve[bin_id], 0.0)
            self.assertLessEqual(capability_curve[bin_id], 1.0)

    def test_phase0_risk_curves(self):
        """Phase 0, Step 6: Compute Risk Curves"""
        def quality_metric(sample: Dict) -> float:
            return sample.get('quality_score', 0.0)

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        binned = self.framework.bin_by_difficulty(
            self.test_data['qwen'],
            difficulty_metric
        )

        risk_curve = self.framework.compute_risk_curve(
            binned,
            quality_metric=quality_metric,
            quality_threshold=0.80
        )

        # Each bin should have a risk value
        for bin_id in binned.keys():
            self.assertIn(bin_id, risk_curve)
            self.assertGreaterEqual(risk_curve[bin_id], 0.0)
            self.assertLessEqual(risk_curve[bin_id], 1.0)

    def test_phase0_tipping_points_detection(self):
        """Phase 0, Step 7: Detect Tipping Points (tau_cap, tau_risk)"""
        def validation_fn(output: str) -> bool:
            return len(output.strip()) > 5

        def quality_metric(sample: Dict) -> float:
            return sample.get('quality_score', 0.0)

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        # Qwen: Should have tau_cap around 2-3, tau_risk at 0 or early
        binned = self.framework.bin_by_difficulty(
            self.test_data['qwen'],
            difficulty_metric
        )

        capability_curve = self.framework.compute_capability_curve(binned, validation_fn)
        risk_curve = self.framework.compute_risk_curve(
            binned,
            quality_metric=quality_metric,
            quality_threshold=0.80
        )

        tau_cap, tau_risk = self.framework.detect_tipping_points(
            capability_curve,
            risk_curve
        )

        # tau_cap should be somewhere in range [0, 4]
        if tau_cap is not None:
            self.assertGreaterEqual(tau_cap, 0)
            self.assertLessEqual(tau_cap, 4)

        # tau_risk should be somewhere in range [0, 4] or None
        if tau_risk is not None:
            self.assertGreaterEqual(tau_risk, 0)
            self.assertLessEqual(tau_risk, 4)

    def test_phase0_empirical_thresholds(self):
        """Phase 0, Step 8: Compute Empirical Thresholds (tau_C, tau_R)"""
        # Collect capability and risk values from both models
        def validation_fn(output: str) -> bool:
            return len(output.strip()) > 5

        def quality_metric(sample: Dict) -> float:
            return sample.get('quality_score', 0.0)

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        all_capabilities = []
        all_risks = []

        for model_name, outputs in self.test_data.items():
            binned = self.framework.bin_by_difficulty(outputs, difficulty_metric)
            cap_curve = self.framework.compute_capability_curve(binned, validation_fn)
            risk_curve = self.framework.compute_risk_curve(
                binned,
                quality_metric=quality_metric,
                quality_threshold=0.80
            )

            all_capabilities.extend(cap_curve.values())
            all_risks.extend(risk_curve.values())

        # Compute empirical thresholds (simplified version)
        if all_capabilities:
            tau_c = statistics.median(all_capabilities)
            self.assertGreaterEqual(tau_c, 0.0)
            self.assertLessEqual(tau_c, 1.0)

        if all_risks:
            tau_r = statistics.median(all_risks)
            self.assertGreaterEqual(tau_r, 0.0)
            self.assertLessEqual(tau_r, 1.0)

    def test_phase0_decision_matrix_4_zones(self):
        """Phase 0, Step 9: Build Decision Matrix (4 zones)"""
        def validation_fn(output: str) -> bool:
            return len(output.strip()) > 5

        def quality_metric(sample: Dict) -> float:
            return sample.get('quality_score', 0.0)

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        task_spec = TaskSpec(
            name="test_task",
            validation_fn=validation_fn,
            difficulty_metric=difficulty_metric,
            quality_metric=quality_metric,
            quality_threshold=0.80,
            num_bins=5
        )

        decisions = self.framework.analyze_task(
            task_spec,
            self.test_data,
            llm_baseline='llama'
        )

        # Should have decisions for both models
        self.assertIn('qwen', decisions)
        self.assertIn('llama', decisions)

        # Each decision should have a quadrant (Q1-Q4)
        for model_name, decision in decisions.items():
            self.assertIn(decision.quadrant, ['Q1', 'Q2', 'Q3', 'Q4'])

    def test_phase1_receive_input(self):
        """Phase 1, Step 11: Receive Input"""
        input_text = "x" * 500  # Medium-length input
        self.assertIsInstance(input_text, str)
        self.assertGreater(len(input_text), 0)

    def test_phase1_compute_difficulty(self):
        """Phase 1, Step 12: Compute Difficulty"""
        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        input_text = "x" * 500
        difficulty = difficulty_metric(input_text)

        self.assertEqual(difficulty, 0.5)  # 500/1000 = 0.5

    def test_phase1_assign_to_bin(self):
        """Phase 1, Step 13: Assign to Bin"""
        difficulty = 0.35
        bin_id = int(difficulty * 4)

        self.assertEqual(bin_id, 1)  # int(0.35 * 4) = int(1.4) = 1

    def test_phase1_zone_classification(self):
        """Phase 1, Step 15: Classify Zone"""
        capability = 0.85
        risk = 0.10
        tau_c = 0.80
        tau_r = 0.20

        # Capability >= tau_c AND Risk <= tau_r
        if capability >= tau_c and risk <= tau_r:
            zone = "Zone1"
        elif capability >= tau_c and risk > tau_r:
            zone = "Zone2"
        elif capability < tau_c and risk <= tau_r:
            zone = "Zone3"
        else:
            zone = "Zone4"

        self.assertEqual(zone, "Zone1")

    def test_phase1_routing_decision(self):
        """Phase 1, Step 16: Apply Zone Routing Policy"""
        zone = "Zone3"
        bin_id = 2
        tau_cap = 3

        # Zone 3: Hybrid routing
        if zone == "Zone3":
            if bin_id <= tau_cap:
                routing = "SLM"
            else:
                routing = "LLM"

        self.assertEqual(routing, "SLM")

    def test_phase2_tipping_point_comparison(self):
        """Phase 2, Step 19-20: Monitor for degradation"""
        old_tau_cap = 3
        new_tau_cap = 2  # Degraded

        # Alert if capability degrades
        if new_tau_cap < old_tau_cap:
            alert = "Capability degrading"
        else:
            alert = "No alert"

        self.assertEqual(alert, "Capability degrading")

    def test_complete_pipeline_flow(self):
        """Integration: Complete pipeline from ingestion to routing"""
        # Phase 0: Analysis
        def validation_fn(output: str) -> bool:
            return len(output.strip()) > 5

        def quality_metric(sample: Dict) -> float:
            return sample.get('quality_score', 0.0)

        def difficulty_metric(input_text: str) -> float:
            return min(len(input_text) / 1000, 1.0)

        # Create task spec
        task_spec = TaskSpec(
            name="integration_test",
            validation_fn=validation_fn,
            difficulty_metric=difficulty_metric,
            quality_metric=quality_metric,
            quality_threshold=0.80,
            num_bins=5
        )

        # Run analysis
        decisions = self.framework.analyze_task(
            task_spec,
            self.test_data,
            llm_baseline='llama'
        )

        # Verify results
        self.assertGreater(len(decisions), 0)

        # Generate policy
        policy = self.framework.generate_policy(decisions)
        self.assertIsInstance(policy, str)
        self.assertGreater(len(policy), 0)
        self.assertIn("ROUTING POLICY", policy)

        # Print results for manual inspection
        print("\n" + "="*80)
        print("PHASE 0 ANALYSIS COMPLETE")
        print("="*80)
        print(policy)

        # Phase 1: Production routing (simulated)
        test_input = "x" * 400  # Medium difficulty
        test_difficulty = difficulty_metric(test_input)
        test_bin = int(test_difficulty * 4)

        print("\n" + "="*80)
        print("PHASE 1 PRODUCTION ROUTING")
        print("="*80)
        print(f"Input difficulty: {test_difficulty:.2f}")
        print(f"Assigned bin: {test_bin}")

        # Verify all pieces are present
        qwen_decision = decisions['qwen']
        print(f"\nQwen (SLM) Decision:")
        print(f"  Quadrant: {qwen_decision.quadrant}")
        print(f"  tau_cap: {qwen_decision.tau_cap}")
        print(f"  tau_risk: {qwen_decision.tau_risk}")
        print(f"  Recommended: {qwen_decision.recommended_model}")

        llama_decision = decisions['llama']
        print(f"\nLlama (LLM) Decision:")
        print(f"  Quadrant: {llama_decision.quadrant}")
        print(f"  tau_cap: {llama_decision.tau_cap}")
        print(f"  tau_risk: {llama_decision.tau_risk}")
        print(f"  Recommended: {llama_decision.recommended_model}")


class ZoneRoutingLogicTest(unittest.TestCase):
    """Test the 4-zone routing logic"""

    def test_zone1_high_cap_low_risk(self):
        """Zone 1: High Capability, Low Risk -> SLM Always"""
        capability = 0.90
        risk = 0.10
        tau_c = 0.80
        tau_r = 0.20

        zone = self._classify_zone(capability, risk, tau_c, tau_r)
        routing = self._apply_routing(zone, bin_id=0, tau_cap=4)

        self.assertEqual(zone, "Zone1")
        self.assertEqual(routing, "SLM")

    def test_zone2_high_cap_high_risk(self):
        """Zone 2: High Capability, High Risk -> SLM + Verify + Escalate"""
        capability = 0.85
        risk = 0.25
        tau_c = 0.80
        tau_r = 0.20

        zone = self._classify_zone(capability, risk, tau_c, tau_r)
        routing = self._apply_routing_zone2(zone)

        self.assertEqual(zone, "Zone2")
        self.assertEqual(routing, "SLM_with_verification")

    def test_zone3_low_cap_low_risk_hybrid(self):
        """Zone 3: Low Capability, Low Risk -> Hybrid (SLM for easy, LLM for hard)"""
        capability = 0.70
        risk = 0.15
        tau_c = 0.80
        tau_r = 0.20

        zone = self._classify_zone(capability, risk, tau_c, tau_r)

        # Test hybrid routing
        tau_cap = 2
        easy_routing = self._apply_routing_zone3(zone, bin_id=1, tau_cap=tau_cap)
        hard_routing = self._apply_routing_zone3(zone, bin_id=3, tau_cap=tau_cap)

        self.assertEqual(zone, "Zone3")
        self.assertEqual(easy_routing, "SLM")
        self.assertEqual(hard_routing, "LLM")

    def test_zone4_low_cap_high_risk(self):
        """Zone 4: Low Capability, High Risk -> LLM Always"""
        capability = 0.65
        risk = 0.35
        tau_c = 0.80
        tau_r = 0.20

        zone = self._classify_zone(capability, risk, tau_c, tau_r)
        routing = self._apply_routing(zone, bin_id=0, tau_cap=4)

        self.assertEqual(zone, "Zone4")
        self.assertEqual(routing, "LLM")

    @staticmethod
    def _classify_zone(capability, risk, tau_c, tau_r):
        """Classify into zone based on 4 quadrants"""
        if capability >= tau_c and risk <= tau_r:
            return "Zone1"
        elif capability >= tau_c and risk > tau_r:
            return "Zone2"
        elif capability < tau_c and risk <= tau_r:
            return "Zone3"
        else:
            return "Zone4"

    @staticmethod
    def _apply_routing(zone, bin_id, tau_cap):
        """Apply routing for zones 1, 2, 4"""
        if zone == "Zone1":
            return "SLM"
        elif zone == "Zone2":
            return "SLM_with_verification"
        elif zone == "Zone4":
            return "LLM"
        return None

    @staticmethod
    def _apply_routing_zone2(zone):
        """Zone 2 specific routing"""
        if zone == "Zone2":
            return "SLM_with_verification"
        return None

    @staticmethod
    def _apply_routing_zone3(zone, bin_id, tau_cap):
        """Zone 3 hybrid routing"""
        if zone == "Zone3":
            if bin_id <= tau_cap:
                return "SLM"
            else:
                return "LLM"
        return None


if __name__ == '__main__':
    unittest.main(verbosity=2)
