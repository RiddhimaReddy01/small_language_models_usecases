#!/bin/bash
# Retrieval-Grounded QA Benchmark - Run script (Unix/macOS)
# Usage: ./run.sh [quick|gemini|full]

set -e
cd "$(dirname "$0")"

case "${1:-full}" in
  quick)
    echo "Quick run: single SLM + Gemini"
    python cli/run_experiment.py --config configs/config.tiny.yaml
    ;;
  gemini)
    echo "Smoke run with minimal config"
    python cli/run_experiment.py --config configs/config.smoke.yaml
    ;;
  full|*)
    echo "Full run with default config"
    python cli/run_experiment.py --config configs/config.yaml
    ;;
esac
