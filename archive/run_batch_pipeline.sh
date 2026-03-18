#!/bin/bash
# Batch Inference Pipeline Orchestrator
# Runs all tasks sequentially with auto-checkpointing & resume

set -e  # Exit on error

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_BASE="${REPO_ROOT}/inference_output"
CHECKPOINT_DIR="${OUTPUT_BASE}/.checkpoints"
BACKEND="ollama"  # or "transformers"
LOG_FILE="${OUTPUT_BASE}/pipeline.log"

# Models & Tasks
declare -A TASK_MODELS=(
    ["text_generation"]="Qwen/Qwen2.5-0.5B-Instruct"
    ["code_generation"]="Qwen/Qwen2.5-Coder-0.5B-Instruct"
    ["maths"]="meta-llama/Llama-3.2-1B-Instruct"
    ["classification"]="microsoft/Phi-3-mini-4k-instruct"
    ["summarization"]="Qwen/Qwen2.5-0.5B-Instruct"
    ["retrieval_grounded"]="Qwen/Qwen2.5-Coder-0.5B-Instruct"
    ["instruction_following"]="meta-llama/Llama-3.2-1B-Instruct"
    ["information_extraction"]="microsoft/Phi-3-mini-4k-instruct"
)

# Create output directory
mkdir -p "${OUTPUT_BASE}"

# ============================================================================
# LOGGING
# ============================================================================

log() {
    local level=$1
    shift
    local msg="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${msg}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

# ============================================================================
# HEALTH CHECKS
# ============================================================================

check_ollama() {
    if ! command -v ollama &> /dev/null; then
        log_error "Ollama not found. Install from: https://ollama.ai"
        return 1
    fi

    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        log_error "Ollama is not running. Start with: ollama serve"
        return 1
    fi

    log_info "Ollama is running"
    return 0
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found"
        return 1
    fi

    log_info "Python 3 found: $(python3 --version)"
    return 0
}

# ============================================================================
# INFERENCE JOB
# ============================================================================

run_inference_job() {
    local task=$1
    local model=$2
    local examples_csv=$3

    if [[ ! -f "${examples_csv}" ]]; then
        log_error "Examples file not found: ${examples_csv}"
        return 1
    fi

    log_info "Starting inference: task=${task}, model=${model}"

    python3 "${REPO_ROOT}/batch_inference_pipeline.py" \
        "${task}" \
        "${model}" \
        "${examples_csv}" \
        "${OUTPUT_BASE}/${task}" \
        "${BACKEND}" \
        2>&1 | tee -a "${LOG_FILE}"

    if [[ $? -eq 0 ]]; then
        log_success "Completed: ${task}"
        return 0
    else
        log_error "Failed: ${task}"
        return 1
    fi
}

# ============================================================================
# MAIN PIPELINE
# ============================================================================

main() {
    log_info "=========================================="
    log_info "Batch Inference Pipeline Started"
    log_info "=========================================="
    log_info "Backend: ${BACKEND}"
    log_info "Output: ${OUTPUT_BASE}"
    log_info "Checkpoint: ${CHECKPOINT_DIR}"

    # Health checks
    log_info "Running health checks..."
    check_python || exit 1

    if [[ "${BACKEND}" == "ollama" ]]; then
        check_ollama || exit 1
    fi

    # Create checkpoint directory
    mkdir -p "${CHECKPOINT_DIR}"

    # Run inference jobs
    local success_count=0
    local fail_count=0
    local total_count=${#TASK_MODELS[@]}

    for task in "${!TASK_MODELS[@]}"; do
        model="${TASK_MODELS[${task}]}"

        # Find examples CSV for this task
        local examples_csv=""
        if [[ -f "${REPO_ROOT}/${task}/rebin_results.csv" ]]; then
            examples_csv="${REPO_ROOT}/${task}/rebin_results.csv"
        elif [[ -f "${REPO_ROOT}/${task}/comprehensive_300.csv" ]]; then
            examples_csv="${REPO_ROOT}/${task}/comprehensive_300.csv"
        else
            log_error "No examples CSV found for ${task}"
            ((fail_count++))
            continue
        fi

        log_info "========== Task: ${task} =========="
        if run_inference_job "${task}" "${model}" "${examples_csv}"; then
            ((success_count++))
        else
            ((fail_count++))
        fi

        log_info ""
    done

    # Summary
    log_info "=========================================="
    log_info "Pipeline Summary"
    log_info "=========================================="
    log_info "Total tasks: ${total_count}"
    log_info "Successful: ${success_count}"
    log_info "Failed: ${fail_count}"
    log_info "Output directory: ${OUTPUT_BASE}"
    log_info "Log file: ${LOG_FILE}"

    if [[ ${fail_count} -eq 0 ]]; then
        log_success "All tasks completed successfully!"
        return 0
    else
        log_error "${fail_count} task(s) failed. Check log for details."
        return 1
    fi
}

# ============================================================================
# RESUME EXISTING JOB
# ============================================================================

resume_pipeline() {
    log_info "Attempting to resume interrupted pipeline..."

    if [[ ! -d "${CHECKPOINT_DIR}" ]]; then
        log_error "No checkpoints found. Cannot resume."
        return 1
    fi

    local checkpoint_count=$(find "${CHECKPOINT_DIR}" -name "*.checkpoint.json" | wc -l)
    if [[ ${checkpoint_count} -eq 0 ]]; then
        log_error "No valid checkpoints found."
        return 1
    fi

    log_info "Found ${checkpoint_count} checkpoint(s). Resuming..."
    main  # Re-run main, will skip completed examples via manifest
}

# ============================================================================
# ENTRY POINT
# ============================================================================

if [[ "$1" == "--resume" ]]; then
    resume_pipeline
elif [[ "$1" == "--help" ]]; then
    cat << EOF
Batch Inference Pipeline Orchestrator

Usage:
  ./run_batch_pipeline.sh               # Run new pipeline
  ./run_batch_pipeline.sh --resume      # Resume interrupted pipeline
  ./run_batch_pipeline.sh --help        # Show this help

Configuration:
  Edit TASK_MODELS in this script to change models/tasks
  Set BACKEND to "ollama" or "transformers"
  Output directory: ${OUTPUT_BASE}
  Checkpoint directory: ${CHECKPOINT_DIR}

Features:
  - Auto-checkpointing after every query
  - Resume from interruption
  - Automatic retry on failure
  - Detailed logging
  - Query deduplication (no re-running)

EOF
else
    main
fi
