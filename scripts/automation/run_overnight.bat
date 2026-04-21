@echo off
title SLM Overnight Inference Runner
cd /d "%~dp0"
echo ============================================================
echo  SLM Overnight Inference Runner
echo  Logs: logs\overnight_stdout.txt
echo  Resume-safe: restart this script any time to continue
echo ============================================================
echo.

.venv\Scripts\python -u tools\run_inference_overnight.py --ollama-only

echo.
echo ============================================================
echo  DONE. Press any key to close.
echo ============================================================
pause
