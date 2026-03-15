@echo off
REM Retrieval-Grounded QA Benchmark - Run script (Windows)
REM Usage: run.bat [quick ^| gemini ^| full]

cd /d "%~dp0"

if "%1"=="quick" (
    echo Quick run: single SLM + Gemini
    python run.py --models Qwen/Qwen2.5-Coder-0.5B-Instruct --baseline-gemini
) else if "%1"=="gemini" (
    echo Gemini only (requires GEMINI_API_KEY)
    python run.py --gemini-only
) else (
    echo Full run: all SLMs
    python run.py
)
