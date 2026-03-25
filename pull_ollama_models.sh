#!/bin/bash

# Pull the 3 SLM models for the benchmark
echo "Pulling Ollama models for SLM benchmark..."
echo ""

echo "[1/3] Pulling phi3:mini..."
ollama pull phi3:mini
echo ""

echo "[2/3] Pulling qwen2.5:1.5b..."
ollama pull qwen2.5:1.5b
echo ""

echo "[3/3] Pulling tinyllama:1.1b..."
ollama pull tinyllama:1.1b
echo ""

echo "Done! Models ready for benchmarking."
echo ""
echo "Verify with: ollama list"
