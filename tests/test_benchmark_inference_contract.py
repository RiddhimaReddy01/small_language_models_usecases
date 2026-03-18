#!/usr/bin/env python3
"""
Benchmark Inference Pipeline Contract Tests

Validates all 10 requirements for publication-ready benchmarking:
1. Per-query structured metadata
2. Immutable run metadata
3. Hardware capture
4. Prompt/version tracking
5. Dataset manifest
6. Failure taxonomy labels
7. Completion summary by bin
8. Validation after generation
9. Graceful partial task completion
10. Final report-generation hook
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark_inference_pipeline import (
    QueryRecord,
    RunManifest,
    HardwareInfo,
    PromptConfig,
    DatasetManifest,
    BenchmarkInferenceEngine,
    generate_sddf_ready_output,
    REQUIRED_QUERY_FIELDS,
    FAILURE_TAXONOMY,
)


# ============================================================================
# REQUIREMENT 1: Per-Query Structured Metadata
# ============================================================================

class TestPerQueryMetadata(unittest.TestCase):
    """Requirement 1: Every saved record includes mandatory fields"""

    def test_required_fields_exist(self):
        """All required fields must be defined"""
        self.assertEqual(REQUIRED_QUERY_FIELDS, {
            "task", "bin", "sample_id", "model", "model_size", "backend",
            "timestamp", "status", "latency_sec", "prompt", "raw_output",
            "parsed_output", "valid", "error"
        })

    def test_query_record_has_all_required_fields(self):
        """QueryRecord dataclass includes all required fields"""
        record = QueryRecord(
            task="test_task",
            bin=0,
            sample_id="sample_0",
            model="test_model",
            model_size="1B",
            backend="ollama",
            timestamp="2024-01-01T00:00:00",
            status="success",
            latency_sec=1.5,
            prompt="test prompt",
            raw_output="test output",
            parsed_output={"key": "value"},
            valid=True,
            error=None
        )

        # Convert to dict and verify all required fields present
        record_dict = record.to_dict()
        for field in REQUIRED_QUERY_FIELDS:
            self.assertIn(field, record_dict, f"Missing required field: {field}")
            # error and parsed_output can be None for valid outputs
            if field not in {"error", "parsed_output"}:
                self.assertIsNotNone(record_dict[field], f"Field {field} is None")

    def test_query_record_validation(self):
        """QueryRecord.validate_required_fields() works correctly"""
        # Valid record
        record = QueryRecord(
            task="test", bin=0, sample_id="s0", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01T00:00:00", status="success",
            latency_sec=1.0, prompt="p", raw_output="o", parsed_output={},
            valid=True, error=None
        )
        is_valid, missing = record.validate_required_fields()
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

        # Invalid record (missing critical field)
        record_invalid = QueryRecord(
            task=None,  # Required, must not be None
            bin=0, sample_id="s0", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01", status="success",
            latency_sec=1.0, prompt="p", raw_output="o", parsed_output={},
            valid=True, error=None
        )
        is_valid, missing = record_invalid.validate_required_fields()
        self.assertFalse(is_valid)
        self.assertIn("task", missing)

    def test_query_record_to_dict(self):
        """QueryRecord.to_dict() includes all required fields"""
        record = QueryRecord(
            task="classification", bin=2, sample_id="ex_100",
            model="llama-2-7b", model_size="7B", backend="ollama",
            timestamp="2024-01-01T10:30:45", status="success",
            latency_sec=2.3, prompt="classify: x", raw_output="positive",
            parsed_output={"label": "positive"}, valid=True, error=None
        )
        d = record.to_dict()
        for field in REQUIRED_QUERY_FIELDS:
            self.assertIn(field, d)


# ============================================================================
# REQUIREMENT 2: Immutable Run Metadata
# ============================================================================

class TestImmutableRunMetadata(unittest.TestCase):
    """Requirement 2: Per-run folder with complete audit trail"""

    def test_run_manifest_structure(self):
        """RunManifest has all required audit fields"""
        manifest = RunManifest(
            task="test_task",
            model_name="test_model",
            total_samples=100,
            total_completed=80,
            total_failed=10,
            total_invalid=10
        )

        # Check required files
        self.assertIsNotNone(manifest.run_id)
        self.assertEqual(manifest.task, "test_task")
        self.assertEqual(manifest.model_name, "test_model")
        self.assertIsNotNone(manifest.timestamp_start)

    def test_run_manifest_saves_to_json(self):
        """RunManifest.save() creates valid JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = RunManifest(task="test", model_name="model")
            manifest_path = Path(tmpdir) / "run_manifest.json"

            manifest.save(manifest_path)

            # Verify file exists and is valid JSON
            self.assertTrue(manifest_path.exists())
            with open(manifest_path) as f:
                data = json.load(f)

            # Verify required fields
            self.assertIn("run_id", data)
            self.assertIn("task", data)
            self.assertIn("timestamp_start", data)
            self.assertIn("timestamp_end", data)

    def test_run_artifact_contract(self):
        """Complete run produces all required artifact files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create mock engine
            dataset_manifest = DatasetManifest(
                task="test",
                source_dataset="test_dataset",
                selection_method="random",
                binning_rule="quantile(5)",
                seed=42,
                target_per_bin={0: 10},
                samples_included={0: ["s0", "s1"]}
            )

            prompt_config = PromptConfig(
                task="test",
                template_version="v1.0",
                system_prompt="test",
                instruction_wrapper="Q: {input}\nA:",
                temperature=0.7,
                top_p=0.9,
                max_tokens=100,
                stop_tokens=[],
                parsing_rules={}
            )

            # Check files would be created
            self.assertIsNotNone(dataset_manifest)
            self.assertIsNotNone(prompt_config)

            # Verify they can be saved
            dataset_manifest.save(output_dir / "dataset_manifest.json")
            prompt_config.save(output_dir / "prompt_config.json")

            # Verify files exist
            self.assertTrue((output_dir / "dataset_manifest.json").exists())
            self.assertTrue((output_dir / "prompt_config.json").exists())


# ============================================================================
# REQUIREMENT 3: Hardware Capture
# ============================================================================

class TestHardwareCapture(unittest.TestCase):
    """Requirement 3: Record actual hardware facts per run"""

    def test_hardware_info_captures_cpu(self):
        """HardwareInfo captures CPU model"""
        hw = HardwareInfo.capture()
        self.assertIsNotNone(hw.cpu_model)
        self.assertNotEqual(hw.cpu_model, "")
        self.assertGreater(hw.cpu_count, 0)

    def test_hardware_info_captures_ram(self):
        """HardwareInfo captures RAM"""
        hw = HardwareInfo.capture()
        self.assertGreater(hw.ram_gb, 0)

    def test_hardware_info_captures_os(self):
        """HardwareInfo captures OS info"""
        hw = HardwareInfo.capture()
        self.assertIsNotNone(hw.platform)
        self.assertIsNotNone(hw.platform_version)

    def test_hardware_info_captures_python(self):
        """HardwareInfo captures Python version"""
        hw = HardwareInfo.capture()
        self.assertIsNotNone(hw.python_version)
        self.assertIn(".", hw.python_version)

    def test_hardware_info_captures_ollama(self):
        """HardwareInfo captures Ollama version if available"""
        hw = HardwareInfo.capture(backend="ollama")
        # May be None if ollama not installed
        if hw.ollama_version is not None:
            self.assertIsInstance(hw.ollama_version, str)

    def test_hardware_info_saves_json(self):
        """HardwareInfo.save() produces valid JSON with all fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            hw = HardwareInfo.capture()
            hw_path = Path(tmpdir) / "hardware.json"

            hw.save(hw_path)

            with open(hw_path) as f:
                data = json.load(f)

            # Verify required fields
            self.assertIn("cpu_model", data)
            self.assertIn("cpu_count", data)
            self.assertIn("ram_gb", data)
            self.assertIn("platform", data)
            self.assertIn("python_version", data)
            self.assertIn("timestamp_captured", data)


# ============================================================================
# REQUIREMENT 4: Prompt/Version Tracking
# ============================================================================

class TestPromptVersionTracking(unittest.TestCase):
    """Requirement 4: Save exact prompt version and decoding params"""

    def test_prompt_config_stores_template_version(self):
        """PromptConfig tracks template version"""
        config = PromptConfig(
            task="test",
            template_version="v1.0",
            system_prompt="system",
            instruction_wrapper="Q: {input}\nA:",
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            stop_tokens=[],
            parsing_rules={}
        )
        self.assertEqual(config.template_version, "v1.0")

    def test_prompt_config_stores_decoding_params(self):
        """PromptConfig stores all decoding parameters"""
        config = PromptConfig(
            task="test",
            template_version="v1.0",
            system_prompt="system",
            instruction_wrapper="Q: {input}\nA:",
            temperature=0.8,
            top_p=0.95,
            max_tokens=200,
            stop_tokens=["[END]", "###"],
            parsing_rules={"type": "json"}
        )

        self.assertEqual(config.temperature, 0.8)
        self.assertEqual(config.top_p, 0.95)
        self.assertEqual(config.max_tokens, 200)
        self.assertEqual(config.stop_tokens, ["[END]", "###"])
        self.assertEqual(config.parsing_rules["type"], "json")

    def test_prompt_config_hash_detects_changes(self):
        """PromptConfig.hash() detects prompt changes"""
        config1 = PromptConfig(
            task="test",
            template_version="v1.0",
            system_prompt="system",
            instruction_wrapper="Q: {input}\nA:",
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            stop_tokens=[],
            parsing_rules={}
        )

        config2 = PromptConfig(
            task="test",
            template_version="v1.0",
            system_prompt="different system",
            instruction_wrapper="Q: {input}\nA:",
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
            stop_tokens=[],
            parsing_rules={}
        )

        self.assertNotEqual(config1.hash(), config2.hash())

    def test_prompt_config_saves_completely(self):
        """PromptConfig.save() preserves all parameters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PromptConfig(
                task="classification",
                template_version="v2.1",
                system_prompt="You classify text.",
                instruction_wrapper="Text: {input}\nClass:",
                temperature=0.75,
                top_p=0.92,
                max_tokens=150,
                stop_tokens=["\n", "END"],
                parsing_rules={"enum": ["positive", "negative", "neutral"]}
            )

            config_path = Path(tmpdir) / "prompt_config.json"
            config.save(config_path)

            with open(config_path) as f:
                data = json.load(f)

            self.assertEqual(data["template_version"], "v2.1")
            self.assertEqual(data["temperature"], 0.75)
            self.assertEqual(data["parsing_rules"]["enum"], ["positive", "negative", "neutral"])


# ============================================================================
# REQUIREMENT 5: Dataset Manifest
# ============================================================================

class TestDatasetManifest(unittest.TestCase):
    """Requirement 5: Save full dataset selection traceability"""

    def test_dataset_manifest_tracks_source(self):
        """DatasetManifest records source dataset"""
        manifest = DatasetManifest(
            task="summarization",
            source_dataset="CNN/DailyMail",
            selection_method="stratified",
            binning_rule="quantile(5)",
            seed=42,
            target_per_bin={0: 10, 1: 10},
            samples_included={0: ["s0", "s1"], 1: ["s2", "s3"]}
        )
        self.assertEqual(manifest.source_dataset, "CNN/DailyMail")

    def test_dataset_manifest_tracks_selection_method(self):
        """DatasetManifest records selection method"""
        manifest = DatasetManifest(
            task="test",
            source_dataset="dataset",
            selection_method="stratified_by_difficulty",
            binning_rule="quantile(5)",
            seed=42,
            target_per_bin={0: 10},
            samples_included={0: ["s0"]}
        )
        self.assertEqual(manifest.selection_method, "stratified_by_difficulty")

    def test_dataset_manifest_tracks_binning(self):
        """DatasetManifest records binning rule"""
        manifest = DatasetManifest(
            task="test",
            source_dataset="dataset",
            selection_method="random",
            binning_rule="uniform(5)",
            seed=42,
            target_per_bin={0: 10, 1: 10, 2: 10},
            samples_included={0: [], 1: [], 2: []}
        )
        self.assertEqual(manifest.binning_rule, "uniform(5)")

    def test_dataset_manifest_tracks_sample_ids(self):
        """DatasetManifest records which samples were selected"""
        sample_ids = {
            0: ["sample_000", "sample_001"],
            1: ["sample_100", "sample_101", "sample_102"]
        }
        manifest = DatasetManifest(
            task="test",
            source_dataset="dataset",
            selection_method="random",
            binning_rule="quantile(5)",
            seed=42,
            target_per_bin={0: 2, 1: 3},
            samples_included=sample_ids
        )

        for bin_id, ids in sample_ids.items():
            self.assertEqual(manifest.samples_included[bin_id], ids)

    def test_dataset_manifest_saves_completely(self):
        """DatasetManifest.save() preserves all metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = DatasetManifest(
                task="code_generation",
                source_dataset="HumanEval",
                selection_method="stratified_by_difficulty",
                binning_rule="quantile(5)",
                seed=123,
                target_per_bin={0: 5, 1: 5, 2: 5},
                samples_included={0: ["he_0"], 1: ["he_1"], 2: ["he_2"]}
            )

            manifest_path = Path(tmpdir) / "dataset_manifest.json"
            manifest.save(manifest_path)

            with open(manifest_path) as f:
                data = json.load(f)

            self.assertEqual(data["source_dataset"], "HumanEval")
            self.assertEqual(data["seed"], 123)
            self.assertEqual(data["samples_included"]["0"], ["he_0"])


# ============================================================================
# REQUIREMENT 6: Failure Taxonomy Labels
# ============================================================================

class TestFailureTaxonomy(unittest.TestCase):
    """Requirement 6: Structured failure analysis"""

    def test_failure_taxonomy_defined(self):
        """Failure taxonomy includes required categories"""
        required_categories = {
            "reasoning_failure", "format_violation", "hallucination",
            "truncation", "refusal", "invalid_parse", "timeout_runtime"
        }
        self.assertTrue(required_categories.issubset(set(FAILURE_TAXONOMY.keys())))

    def test_query_record_stores_failure_category(self):
        """QueryRecord can store failure category"""
        record = QueryRecord(
            task="test", bin=0, sample_id="s0", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01", status="failed",
            latency_sec=0.5, prompt="p", raw_output="", parsed_output={},
            valid=False, error="Parse failed", failure_category="invalid_parse"
        )
        self.assertEqual(record.failure_category, "invalid_parse")
        self.assertIn(record.failure_category, FAILURE_TAXONOMY)


# ============================================================================
# REQUIREMENT 7: Completion Summary by Bin
# ============================================================================

class TestCompletionSummaryByBin(unittest.TestCase):
    """Requirement 7: Per-bin coverage tracking"""

    def test_run_manifest_tracks_completion_by_bin(self):
        """RunManifest.completion_by_bin tracks target/success/failed/pending"""
        manifest = RunManifest(task="test", model_name="model")
        manifest.completion_by_bin = {
            0: {"target": 10, "success": 10, "failed": 0, "pending": 0},
            1: {"target": 10, "success": 8, "failed": 2, "pending": 0},
            2: {"target": 10, "success": 5, "failed": 0, "pending": 5}
        }

        self.assertEqual(manifest.completion_by_bin[0]["success"], 10)
        self.assertEqual(manifest.completion_by_bin[1]["failed"], 2)
        self.assertEqual(manifest.completion_by_bin[2]["pending"], 5)

    def test_run_manifest_coverage_report(self):
        """RunManifest.coverage_report() computes per-bin coverage"""
        manifest = RunManifest(task="test", model_name="model")
        manifest.completion_by_bin = {
            0: {"target": 10, "success": 10, "failed": 0, "pending": 0},
            1: {"target": 10, "success": 5, "failed": 3, "pending": 2}
        }

        report = manifest.coverage_report()

        self.assertEqual(report[0]["coverage_pct"], 100.0)
        self.assertTrue(report[0]["is_complete"])

        self.assertEqual(report[1]["coverage_pct"], 50.0)
        self.assertFalse(report[1]["is_complete"])


# ============================================================================
# REQUIREMENT 8: Validation After Generation
# ============================================================================

class TestValidationAfterGeneration(unittest.TestCase):
    """Requirement 8: Output usability checks"""

    def test_query_record_has_valid_field(self):
        """QueryRecord has valid=True/False, not just status"""
        record_valid = QueryRecord(
            task="test", bin=0, sample_id="s0", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01", status="success",
            latency_sec=1.0, prompt="p", raw_output="valid output",
            parsed_output={"key": "value"}, valid=True, error=None
        )

        record_invalid = QueryRecord(
            task="test", bin=0, sample_id="s1", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01", status="success",
            latency_sec=1.0, prompt="p", raw_output="", parsed_output={},
            valid=False, error="Empty output"
        )

        self.assertTrue(record_valid.valid)
        self.assertFalse(record_invalid.valid)

    def test_query_record_stores_validation_checks(self):
        """QueryRecord stores detailed validation check results"""
        record = QueryRecord(
            task="test", bin=0, sample_id="s0", model="m", model_size="1B",
            backend="ollama", timestamp="2024-01-01", status="success",
            latency_sec=1.0, prompt="p", raw_output="output",
            parsed_output={}, valid=True,
            validation_checks={
                "non_empty": True,
                "parseable": True,
                "not_truncated": True,
                "has_expected_fields": True
            },
            validation_notes="All checks passed"
        )

        self.assertTrue(record.validation_checks["non_empty"])
        self.assertEqual(record.validation_notes, "All checks passed")


# ============================================================================
# REQUIREMENT 9: Graceful Partial Task Completion
# ============================================================================

class TestGracefulPartialCompletion(unittest.TestCase):
    """Requirement 9: Resume with coverage awareness"""

    def test_outputs_jsonl_is_appendable(self):
        """outputs.jsonl can be resumed via append"""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_path = Path(tmpdir) / "outputs.jsonl"

            # First batch
            records1 = [
                QueryRecord(task="t", bin=0, sample_id="s0", model="m",
                           model_size="1B", backend="ollama",
                           timestamp="2024-01-01", status="success",
                           latency_sec=1.0, prompt="p", raw_output="o",
                           parsed_output={}, valid=True, error=None)
            ]

            for record in records1:
                with open(outputs_path, "a") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")

            # Second batch (resume)
            records2 = [
                QueryRecord(task="t", bin=1, sample_id="s1", model="m",
                           model_size="1B", backend="ollama",
                           timestamp="2024-01-01", status="success",
                           latency_sec=1.0, prompt="p", raw_output="o",
                           parsed_output={}, valid=True, error=None)
            ]

            for record in records2:
                with open(outputs_path, "a") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")

            # Verify both batches present
            with open(outputs_path) as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["sample_id"], "s0")
            self.assertEqual(json.loads(lines[1])["sample_id"], "s1")

    def test_coverage_check_detects_incomplete_bins(self):
        """Coverage detection identifies underfilled bins"""
        manifest = RunManifest(task="test", model_name="model")
        manifest.completion_by_bin = {
            0: {"target": 10, "success": 10, "failed": 0, "pending": 0},
            1: {"target": 10, "success": 5, "failed": 2, "pending": 3},  # Incomplete
            2: {"target": 10, "success": 0, "failed": 0, "pending": 10}   # Not started
        }

        report = manifest.coverage_report()

        self.assertTrue(report[0]["is_complete"])
        self.assertFalse(report[1]["is_complete"])
        self.assertFalse(report[2]["is_complete"])


# ============================================================================
# REQUIREMENT 10: Final Report-Generation Hook
# ============================================================================

class TestReportGenerationHook(unittest.TestCase):
    """Requirement 10: SDDF-ready output generation"""

    def test_sddf_ready_output_can_be_generated(self):
        """generate_sddf_ready_output() creates SDDF-ready CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create outputs.jsonl
            outputs = [
                {
                    "task": "test", "bin": 0, "sample_id": "s0", "model": "m",
                    "model_size": "1B", "backend": "ollama",
                    "timestamp": "2024-01-01", "status": "success",
                    "latency_sec": 1.0, "prompt": "p", "raw_output": "o",
                    "parsed_output": {}, "valid": True, "error": None
                },
                {
                    "task": "test", "bin": 1, "sample_id": "s1", "model": "m",
                    "model_size": "1B", "backend": "ollama",
                    "timestamp": "2024-01-01", "status": "success",
                    "latency_sec": 1.5, "prompt": "p", "raw_output": "o",
                    "parsed_output": {}, "valid": True, "error": None
                }
            ]

            with open(output_dir / "outputs.jsonl", "w") as f:
                for record in outputs:
                    f.write(json.dumps(record) + "\n")

            # Generate SDDF output
            sddf_path = generate_sddf_ready_output(output_dir)

            # Verify SDDF output exists and has expected structure
            self.assertTrue(sddf_path.exists())

            sddf_df = pd.read_csv(sddf_path)
            self.assertIn("bin", sddf_df.columns)
            self.assertIn("n_samples", sddf_df.columns)
            self.assertIn("success_rate", sddf_df.columns)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestFullPipelineContract(unittest.TestCase):
    """Integration: All 10 requirements work together"""

    def test_complete_run_produces_all_artifacts(self):
        """A complete run produces all required artifacts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Simulate a run with all components
            hardware = HardwareInfo.capture()
            prompt_config = PromptConfig(
                task="test", template_version="v1.0", system_prompt="sys",
                instruction_wrapper="Q: {input}\nA:", temperature=0.7,
                top_p=0.9, max_tokens=100, stop_tokens=[], parsing_rules={}
            )
            dataset = DatasetManifest(
                task="test", source_dataset="test_data", selection_method="random",
                binning_rule="quantile(5)", seed=42,
                target_per_bin={0: 5}, samples_included={0: ["s0"]}
            )

            # Save all artifacts
            hardware.save(output_dir / "hardware.json")
            prompt_config.save(output_dir / "prompt_config.json")
            dataset.save(output_dir / "dataset_manifest.json")

            # Create run manifest
            manifest = RunManifest(task="test", model_name="model")
            manifest.completion_by_bin = {0: {"target": 5, "success": 5, "failed": 0, "pending": 0}}
            manifest.save(output_dir / "run_manifest.json")

            # Create sample outputs
            outputs = [{"task": "test", "bin": 0, "sample_id": "s0", "model": "m",
                       "model_size": "1B", "backend": "ollama", "timestamp": "2024-01-01",
                       "status": "success", "latency_sec": 1.0, "prompt": "p",
                       "raw_output": "o", "parsed_output": {}, "valid": True, "error": None}]

            with open(output_dir / "outputs.jsonl", "w") as f:
                for o in outputs:
                    f.write(json.dumps(o) + "\n")

            # Verify all required files exist
            self.assertTrue((output_dir / "hardware.json").exists())
            self.assertTrue((output_dir / "prompt_config.json").exists())
            self.assertTrue((output_dir / "dataset_manifest.json").exists())
            self.assertTrue((output_dir / "run_manifest.json").exists())
            self.assertTrue((output_dir / "outputs.jsonl").exists())

            # Generate SDDF
            sddf_path = generate_sddf_ready_output(output_dir)
            self.assertTrue(sddf_path.exists())


if __name__ == "__main__":
    unittest.main()
