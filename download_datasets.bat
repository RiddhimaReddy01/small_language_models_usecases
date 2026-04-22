@echo off
REM Benchmark 2024: Official Datasets Download Script (Windows Batch)
REM Quick download using HuggingFace CLI
REM Requires: pip install huggingface-hub

setlocal enabledelayedexpansion

set "OUTPUT_DIR=%1"
if "!OUTPUT_DIR!"=="" (
    set "OUTPUT_DIR=."
)

echo ==================================================
echo Benchmark 2024: Official Datasets Download
echo ==================================================
echo Output Directory: !OUTPUT_DIR!
echo.

mkdir "!OUTPUT_DIR!" 2>nul

REM Function to download dataset
:download_dataset
set "dataset_id=%~1"
set "name=%~2"
set "size=%~3"

if "!dataset_id!"=="internal" (
    echo ❌ SKIPPED: !name! ^(Internal/Proprietary^)
    exit /b 0
)

echo ⏳ Downloading: !name! ^(!dataset_id!^)...
huggingface-cli download "!dataset_id!" --repo-type dataset --cache-dir "!OUTPUT_DIR!" >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Success: !name!
) else (
    echo ❌ Failed: !name!
)
exit /b !errorlevel!

REM ============================================================================
REM MATHS DATASETS
REM ============================================================================
:maths_section
echo.
echo 📚 MATHS - Multi-step arithmetic and algebraic reasoning
call :download_dataset "openai/gsm8k" "GSM8K (OpenAI)" "~500 MB"
call :download_dataset "heegyu/MATH_Subset" "MATH (DeepMind)" "~1.5 GB"
call :download_dataset "svamp" "SVAMP (Patel et al.)" "~50 MB"

REM ============================================================================
REM CLASSIFICATION DATASETS
REM ============================================================================
:classification_section
echo.
echo 📂 CLASSIFICATION - Text categorization
call :download_dataset "ag_news" "AG News" "~120 MB"
call :download_dataset "dbpedia_14" "DBpedia" "~630 MB"
call :download_dataset "imdb" "IMDB" "~80 MB"
call :download_dataset "yahoo_answers_qa" "Yahoo Answers" "~1.5 GB"

REM ============================================================================
REM INFORMATION EXTRACTION
REM ============================================================================
:extraction_section
echo.
echo 📋 INFORMATION EXTRACTION - Structured field extraction
call :download_dataset "huggingface/sroie" "SROIE" "~100 MB"

REM ============================================================================
REM RETRIEVAL GROUNDED
REM ============================================================================
:retrieval_section
echo.
echo 🔍 RETRIEVAL GROUNDED - Context-aware QA
call :download_dataset "rajpurkar/squad" "SQuAD" "~30 MB"
call :download_dataset "LLukas22/nq-simplified" "Natural Questions" "~138 MB"

REM ============================================================================
REM CODE GENERATION
REM ============================================================================
:codegen_section
echo.
echo 💻 CODE GENERATION - Python function generation
call :download_dataset "openai_humaneval" "HumanEval" "~20 MB"
call :download_dataset "google/mbpp" "MBPP" "~30 MB"

REM ============================================================================
REM SUMMARIZATION
REM ============================================================================
:summarization_section
echo.
echo 📑 SUMMARIZATION - Document summarization
call :download_dataset "cnn_dailymail" "CNN/DailyMail" "~2.5 GB"
call :download_dataset "samsum" "SamSum (alternative)" "~100 MB"

REM ============================================================================
REM INTERNAL DATASETS
REM ============================================================================
:internal_section
echo.
echo 🔒 INSTRUCTION FOLLOWING ^& TEXT GENERATION ^(Internal^)
echo ❌ SKIPPED: Enterprise gold sets (proprietary)

echo.
echo ==================================================
echo ✅ Download Complete!
echo Datasets saved to: !OUTPUT_DIR!
echo ==================================================

endlocal
