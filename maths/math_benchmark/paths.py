from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
OUTPUTS_DIR = ROOT / "outputs"
RAW_RESULTS_DIR = OUTPUTS_DIR / "predictions"
REPORTS_DIR = OUTPUTS_DIR / "metrics"
LOGS_DIR = OUTPUTS_DIR / "logs"
LEGACY_RESULTS_DIR = ROOT / "results"
LEGACY_RAW_RESULTS_DIR = LEGACY_RESULTS_DIR / "raw"
LEGACY_REPORTS_DIR = LEGACY_RESULTS_DIR / "reports"
