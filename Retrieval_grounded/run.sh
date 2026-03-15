#!/bin/bash
# Retrieval-Grounded QA Benchmark - Run script (Unix/macOS)
# Usage: ./run.sh [quick|gemini|full]

set -e
cd "$(dirname "$0")"

case "${1:-full}" in
  quick)
    echo "Quick run: single SLM + Gemini"
    python run.py --models Qwen/Qwen2.5-Coder-0.5B-Instruct --baseline-gemini
    ;;
  gemini)
    echo "Gemini only (requires GEMINI_API_KEY)"
    python run.py --gemini-only
    ;;
  full|*)
    echo "Full run: all SLMs + Gemini"
    python run.py --baseline-gemini
    ;;
esac
