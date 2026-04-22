#!/bin/bash
# Benchmark 2024: Official Datasets Download Script (Bash)
# Quick download using HuggingFace CLI
# Requires: pip install huggingface-hub

set -e

OUTPUT_DIR="${1:-.}"
SKIP_LARGE="${2:-false}"

echo "=================================================="
echo "Benchmark 2024: Official Datasets Download"
echo "=================================================="
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to download dataset
download_dataset() {
    local dataset_id=$1
    local name=$2
    local size=$3

    # Skip large datasets if requested
    if [[ "$SKIP_LARGE" == "true" ]] && [[ "$size" == *"GB"* ]]; then
        echo "⊘ SKIPPED: $name ($size)"
        return 0
    fi

    if [[ "$dataset_id" == "internal" ]]; then
        echo "❌ SKIPPED: $name (Internal/Proprietary)"
        return 0
    fi

    echo "⏳ Downloading: $name ($dataset_id)..."
    if huggingface-cli download "$dataset_id" --repo-type dataset --cache-dir "$OUTPUT_DIR" > /dev/null 2>&1; then
        echo "✅ Success: $name"
        return 0
    else
        echo "❌ Failed: $name"
        return 1
    fi
}

# ============================================================================
# MATHS DATASETS
# ============================================================================
echo ""
echo "📚 MATHS - Multi-step arithmetic and algebraic reasoning"
download_dataset "openai/gsm8k" "GSM8K (OpenAI)" "~500 MB"
download_dataset "heegyu/MATH_Subset" "MATH (DeepMind)" "~1.5 GB"
download_dataset "svamp" "SVAMP (Patel et al.)" "~50 MB"

# ============================================================================
# CLASSIFICATION DATASETS
# ============================================================================
echo ""
echo "📂 CLASSIFICATION - Text categorization"
download_dataset "ag_news" "AG News" "~120 MB"
download_dataset "dbpedia_14" "DBpedia" "~630 MB"
download_dataset "imdb" "IMDB" "~80 MB"
download_dataset "yahoo_answers_qa" "Yahoo Answers" "~1.5 GB"

# ============================================================================
# INFORMATION EXTRACTION
# ============================================================================
echo ""
echo "📋 INFORMATION EXTRACTION - Structured field extraction"
download_dataset "huggingface/sroie" "SROIE" "~100 MB"

# ============================================================================
# RETRIEVAL GROUNDED
# ============================================================================
echo ""
echo "🔍 RETRIEVAL GROUNDED - Context-aware QA"
download_dataset "rajpurkar/squad" "SQuAD" "~30 MB"
download_dataset "LLukas22/nq-simplified" "Natural Questions" "~138 MB"

# ============================================================================
# CODE GENERATION
# ============================================================================
echo ""
echo "💻 CODE GENERATION - Python function generation"
download_dataset "openai_humaneval" "HumanEval" "~20 MB"
download_dataset "google/mbpp" "MBPP" "~30 MB"

# ============================================================================
# SUMMARIZATION
# ============================================================================
echo ""
echo "📑 SUMMARIZATION - Document summarization"
download_dataset "cnn_dailymail" "CNN/DailyMail" "~2.5 GB"
download_dataset "samsum" "SamSum (alternative)" "~100 MB"

# ============================================================================
# INTERNAL DATASETS
# ============================================================================
echo ""
echo "🔒 INSTRUCTION FOLLOWING & TEXT GENERATION (Internal)"
echo "❌ SKIPPED: Enterprise gold sets (proprietary)"

echo ""
echo "=================================================="
echo "✅ Download Complete!"
echo "Datasets saved to: $OUTPUT_DIR"
echo "=================================================="
