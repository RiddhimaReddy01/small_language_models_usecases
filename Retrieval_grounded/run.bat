@echo off
REM Retrieval-Grounded QA Benchmark - Run script (Windows)
REM Usage: run.bat [quick ^| gemini ^| full]

cd /d "%~dp0"

if "%1"=="quick" (
    echo Quick run with tiny config
    python cli/run_experiment.py --config configs/config.tiny.yaml
) else if "%1"=="gemini" (
    echo Smoke run with minimal config
    python cli/run_experiment.py --config configs/config.smoke.yaml
) else (
    echo Full run with default config
    python cli/run_experiment.py --config configs/config.yaml
)
