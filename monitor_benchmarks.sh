#!/bin/bash
echo "[LIVE MONITOR - Press Ctrl+C to stop]"
echo ""

while true; do
    clear
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║             DUAL BENCHMARK EXECUTION MONITOR                  ║"
    echo "║  SLM (Local) + LLM (Cloud) Running in Parallel                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    echo "📊 SLM BENCHMARK PROGRESS (Local)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    RECORDS=$(find benchmark_output -name "outputs.jsonl" -type f -exec wc -l {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
    echo "Inference records: $RECORDS / 1200 ($(echo "scale=1; $RECORDS*100/1200" | bc)%)"
    
    echo ""
    echo "By Task:"
    for task in text_generation code_generation classification maths summarization retrieval_grounded instruction_following information_extraction; do
        COUNT=$(find benchmark_output/$task -name "outputs.jsonl" -type f -exec wc -l {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
        if [ -z "$COUNT" ] || [ "$COUNT" = "0" ]; then
            COUNT="0"
        fi
        printf "  %-25s %3d/150\n" "$task:" "$COUNT"
    done
    
    echo ""
    echo "☁️  GROQ BASELINE PROGRESS (Cloud)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    GROQ_RECORDS=$(find benchmark_output -path "*groq*" -name "outputs.jsonl" -type f -exec wc -l {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
    if [ -z "$GROQ_RECORDS" ] || [ "$GROQ_RECORDS" = "0" ]; then
        GROQ_RECORDS="0"
        echo "Status: Initializing API connection..."
    else
        echo "Inference records: $GROQ_RECORDS / 600 ($(echo "scale=1; $GROQ_RECORDS*100/600" | bc)%)"
    fi
    
    echo ""
    echo "⏱️  TIMING"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Expected SLM duration: 1.5-2 hours"
    echo "Expected Groq duration: 30-45 minutes"
    echo "Current time: $(date '+%H:%M:%S')"
    
    echo ""
    echo "[Refreshing every 10 seconds...]"
    sleep 10
done
