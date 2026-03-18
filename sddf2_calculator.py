#!/usr/bin/env python3
"""
SDDF-2 Multi-Dimensional Capability-Aware Deployment Framework
Calculates: Capability (A,R,S,F,Cov) × Operational (Latency,FLOPs,Memory,Tokens,FailureRate)
"""

import json
import os
import re
import ast
import statistics
from pathlib import Path
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_PATH = Path("benchmark_output")
MODELS = ["phi3_mini", "llama_llama-3.3-70b-versatile", "qwen2.5_1.5b", "tinyllama_1.1b"]
TASKS = ["text_generation", "code_generation", "classification", "maths",
         "summarization", "retrieval_grounded", "instruction_following", "information_extraction"]

# Model specs for FLOPs/Memory calculation
MODEL_SPECS = {
    "phi3_mini": {"params": 3.8e9, "layers": 32, "hidden_dim": 3072},
    "llama_llama-3.3-70b-versatile": {"params": 70e9, "layers": 80, "hidden_dim": 8192},
    "qwen2.5_1.5b": {"params": 1.5e9, "layers": 28, "hidden_dim": 1536},
    "tinyllama_1.1b": {"params": 1.1e9, "layers": 22, "hidden_dim": 2048}
}

# ============================================================================
# CAPABILITY METRICS FUNCTIONS
# ============================================================================

def calculate_accuracy(task, outputs):
    """A: Accuracy as validity proxy"""
    valid_count = sum(1 for o in outputs if o.get('valid', False))
    return valid_count / len(outputs) if outputs else 0

def calculate_robustness(task, outputs):
    """R: Performance retention from easy (bin0) to hard (bin4)"""
    if not outputs:
        return float('nan')

    # Group by difficulty bin
    bins = defaultdict(list)
    for output in outputs:
        bin_id = output.get('bin', 0)
        bins[bin_id].append(output.get('valid', False))

    # Get pass rates
    pass_rates = {}
    for b in range(5):
        bin_outputs = bins.get(b, [])
        if bin_outputs:
            pass_rates[b] = sum(bin_outputs) / len(bin_outputs)
        else:
            pass_rates[b] = None

    # Calculate R = a4/a0
    a0 = pass_rates.get(0)
    a4 = pass_rates.get(4)

    if a0 is None or a0 == 0:
        return float('nan')  # Undefined
    if a4 is None:
        return float('nan')

    R = min(a4 / a0, 1.0)  # Clamp to [0,1]
    return R

def calculate_consistency(task, outputs):
    """S: Coefficient of variation normalized to [0,1]"""
    if not outputs:
        return float('nan')

    lengths = []
    for output in outputs:
        raw = output.get('raw_output', '')
        if raw:
            lengths.append(len(str(raw)))

    if not lengths or len(lengths) < 2:
        return float('nan')

    mean_len = statistics.mean(lengths)
    if mean_len == 0:
        return float('nan')

    std_len = statistics.stdev(lengths)
    cv = std_len / mean_len
    S = 1 / (1 + cv)
    return S

def calculate_format_validity(task, outputs):
    """F: Format validity from validation_checks"""
    valid_format = sum(1 for o in outputs if o.get('valid', False))
    return valid_format / len(outputs) if outputs else 0

def calculate_coverage(task, outputs):
    """Cov: Task-specific coverage contracts"""
    if not outputs:
        return float('nan')

    valid_cov = 0

    for output in outputs:
        raw = output.get('raw_output', '')
        if not raw:
            continue

        is_valid = False

        if task == "classification":
            # Single word, likely a label
            words = raw.strip().split()
            if len(words) == 1 and len(words[0]) > 0:
                is_valid = True

        elif task == "code_generation":
            # Parses + has def/class/import + length >= 50
            try:
                ast.parse(raw)
                has_code = "def " in raw or "class " in raw or "import " in raw
                if has_code and len(raw) >= 50:
                    is_valid = True
            except:
                pass

        elif task == "summarization":
            # 80 <= length <= 2000 chars
            if 80 <= len(raw) <= 2000:
                is_valid = True

        elif task == "information_extraction":
            # Valid JSON
            try:
                json.loads(raw)
                is_valid = True
            except:
                pass

        elif task == "maths":
            # Contains extractable final number
            if re.search(r'\d+\.?\d*', raw):
                is_valid = True

        elif task == "retrieval_grounded":
            # Substantive: >= 80 chars, not just copy of prompt
            prompt = output.get('prompt', '')
            if len(raw) >= 80 and raw.strip() != prompt.strip():
                is_valid = True

        elif task == "instruction_following":
            # Use validity flag (format constraints specific to each sample)
            is_valid = output.get('valid', False)

        elif task == "text_generation":
            # Use validity flag (completion is coverage)
            is_valid = output.get('valid', False)

        if is_valid:
            valid_cov += 1

    return valid_cov / len(outputs) if outputs else 0

# ============================================================================
# OPERATIONAL METRICS FUNCTIONS
# ============================================================================

def calculate_latency(outputs):
    """Average inference latency in seconds"""
    latencies = [o.get('latency_sec', 0) for o in outputs if o.get('latency_sec')]
    return statistics.mean(latencies) if latencies else 0

def calculate_tokens(outputs):
    """Average total tokens (input + output)"""
    # Estimate: prompt chars / 4 + output chars / 4
    total_tokens = []
    for output in outputs:
        prompt = output.get('prompt', '')
        raw = output.get('raw_output', '')
        input_tokens = len(prompt) / 4  # Rough estimate
        output_tokens = len(raw) / 4
        total_tokens.append(input_tokens + output_tokens)

    return statistics.mean(total_tokens) if total_tokens else 0

def calculate_flops(model_name, outputs):
    """FLOPs = 2 × params × total_tokens"""
    specs = MODEL_SPECS.get(model_name)
    if not specs:
        return 0

    params = specs['params']
    avg_tokens = calculate_tokens(outputs)

    flops = 2 * params * avg_tokens
    return flops

def calculate_memory(model_name, outputs):
    """Memory = Model weights (FP16) + KV cache"""
    specs = MODEL_SPECS.get(model_name)
    if not specs:
        return 0

    # Model weights (FP16 = 2 bytes)
    weights_gb = (specs['params'] * 2) / (1024**3)

    # KV cache = 2 × layers × seq_length × hidden_dim × 2 bytes
    avg_tokens = calculate_tokens(outputs)
    seq_length = avg_tokens  # Approximate
    kv_cache_bytes = 2 * specs['layers'] * seq_length * specs['hidden_dim'] * 2
    kv_cache_gb = kv_cache_bytes / (1024**3)

    total_memory_gb = weights_gb + kv_cache_gb
    return total_memory_gb

def calculate_failure_rate(outputs):
    """Failure rate = 1 - (valid count / total)"""
    valid_count = sum(1 for o in outputs if o.get('valid', False))
    return 1 - (valid_count / len(outputs)) if outputs else 1

# ============================================================================
# MAIN CALCULATION ENGINE
# ============================================================================

def load_outputs(task, model):
    """Load all outputs for a task/model combination"""
    path = BASE_PATH / task / model / "outputs.jsonl"
    results = []

    if not path.exists():
        return results

    try:
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except Exception as e:
        print(f"Error loading {task}/{model}: {e}")

    return results

def calculate_sddf2_metrics():
    """Calculate all SDDF-2 metrics"""

    # Store results
    capability_metrics = {}  # {task: {model: {A, R, S, F, Cov}}}
    operational_metrics = {}  # {task: {model: {Latency, FLOPs, Memory, Tokens, FailureRate}}}

    print("=" * 90)
    print("SDDF-2 CALCULATION ENGINE")
    print("=" * 90)

    for task in TASKS:
        print(f"\nProcessing {task}...")
        capability_metrics[task] = {}
        operational_metrics[task] = {}

        for model in MODELS:
            outputs = load_outputs(task, model)

            if not outputs:
                print(f"  {model}: NO DATA")
                continue

            # Capability metrics
            A = calculate_accuracy(task, outputs)
            R = calculate_robustness(task, outputs)
            S = calculate_consistency(task, outputs)
            F = calculate_format_validity(task, outputs)
            Cov = calculate_coverage(task, outputs)

            capability_metrics[task][model] = {
                'A': A, 'R': R, 'S': S, 'F': F, 'Cov': Cov,
                'samples': len(outputs),
                'valid_count': sum(1 for o in outputs if o.get('valid'))
            }

            # Operational metrics
            Latency = calculate_latency(outputs)
            Tokens = calculate_tokens(outputs)
            FLOPs = calculate_flops(model, outputs)
            Memory = calculate_memory(model, outputs)
            FailureRate = calculate_failure_rate(outputs)

            operational_metrics[task][model] = {
                'Latency': Latency,
                'Tokens': Tokens,
                'FLOPs': FLOPs,
                'Memory': Memory,
                'FailureRate': FailureRate
            }

            print(f"  {model:40} | A={A:.3f} R={R:.3f} S={S:.3f} F={F:.3f} Cov={Cov:.3f}")

    return capability_metrics, operational_metrics

def generate_capability_table(capability_metrics):
    """Generate comprehensive capability metrics table"""

    print("\n" + "=" * 120)
    print("SDDF-2 CAPABILITY METRICS: (A, R, S, F, Cov) - All metrics in [0,1]")
    print("=" * 120)

    # Header
    header = f"{'Task':<25}"
    for model in MODELS:
        header += f" | {model[:20]:<20}"
    print(header)
    print("-" * 120)

    # Metrics rows
    for metric in ['A', 'R', 'S', 'F', 'Cov']:
        row = f"{metric} (Accuracy/Robust/Consist/Format/Coverage)"[:25].ljust(25)
        for model in MODELS:
            values = []
            for task in TASKS:
                if task in capability_metrics and model in capability_metrics[task]:
                    m = capability_metrics[task][model].get(metric, float('nan'))
                    if isinstance(m, float):
                        if m != m:  # NaN check
                            values.append("—")
                        else:
                            values.append(f"{m:.3f}")
                    else:
                        values.append(str(m))
                else:
                    values.append("—")

            avg_str = ", ".join(values[:4])  # Show first 4 tasks as sample
            row += f" | {avg_str[:20]:<20}"

        print(row)

    # Per-task detailed view
    print("\n" + "=" * 120)
    print("PER-TASK CAPABILITY BREAKDOWN")
    print("=" * 120)

    for task in TASKS:
        print(f"\n{task.upper()}")
        print("-" * 120)
        header = f"{'Model':<30} | {'A':<8} | {'R':<8} | {'S':<8} | {'F':<8} | {'Cov':<8} | {'Valid/Total':<15}"
        print(header)
        print("-" * 120)

        for model in MODELS:
            if task in capability_metrics and model in capability_metrics[task]:
                metrics = capability_metrics[task][model]
                A = metrics.get('A', 0)
                R = metrics.get('R', float('nan'))
                S = metrics.get('S', float('nan'))
                F = metrics.get('F', 0)
                Cov = metrics.get('Cov', float('nan'))
                valid = metrics.get('valid_count', 0)
                total = metrics.get('samples', 0)

                # Format NaN as "—"
                r_str = "—" if (isinstance(R, float) and R != R) else f"{R:.3f}"
                s_str = "—" if (isinstance(S, float) and S != S) else f"{S:.3f}"
                cov_str = "—" if (isinstance(Cov, float) and Cov != Cov) else f"{Cov:.3f}"

                print(f"{model:<30} | {A:>6.3f} | {r_str:>6} | {s_str:>6} | {F:>6.3f} | {cov_str:>6} | {valid}/{total:<13}")

def generate_operational_table(operational_metrics):
    """Generate operational metrics table"""

    print("\n" + "=" * 140)
    print("SDDF-2 OPERATIONAL METRICS: (Latency, FLOPs, Memory, Tokens, FailureRate)")
    print("=" * 140)

    for task in TASKS:
        print(f"\n{task.upper()}")
        print("-" * 140)
        header = f"{'Model':<30} | {'Latency(s)':<12} | {'FLOPs(T)':<15} | {'Memory(GB)':<12} | {'Tokens':<10} | {'FailRate':<10}"
        print(header)
        print("-" * 140)

        for model in MODELS:
            if task in operational_metrics and model in operational_metrics[task]:
                op = operational_metrics[task][model]
                latency = op.get('Latency', 0)
                flops = op.get('FLOPs', 0) / 1e12  # Convert to Trillion FLOPs
                memory = op.get('Memory', 0)
                tokens = op.get('Tokens', 0)
                fail_rate = op.get('FailureRate', 0)

                print(f"{model:<30} | {latency:>10.2f} | {flops:>13.2f} | {memory:>10.2f} | {tokens:>8.0f} | {fail_rate:>8.3f}")

def generate_performance_ratios(capability_metrics):
    """Generate SLM/LLM performance ratios for routing"""

    print("\n" + "=" * 120)
    print("PERFORMANCE RATIOS: p = SLM_metric / LLM_metric")
    print("(Higher = SLM performs better relative to Llama baseline)")
    print("=" * 120)

    llm = "llama_llama-3.3-70b-versatile"
    slms = ["phi3_mini", "qwen2.5_1.5b", "tinyllama_1.1b"]

    for task in TASKS:
        print(f"\n{task.upper()}")
        print("-" * 120)
        header = f"{'SLM':<30} | {'A Ratio':<10} | {'R Ratio':<10} | {'S Ratio':<10} | {'F Ratio':<10} | {'Cov Ratio':<10} | {'Best?':<8}"
        print(header)
        print("-" * 120)

        llm_metrics = capability_metrics.get(task, {}).get(llm, {})

        for slm in slms:
            slm_metrics = capability_metrics.get(task, {}).get(slm, {})

            if not slm_metrics or not llm_metrics:
                continue

            # Calculate ratios (SLM/LLM)
            a_ratio = slm_metrics.get('A', 0) / (llm_metrics.get('A', 1) or 1)

            r_llm = llm_metrics.get('R', 1)
            r_slm = slm_metrics.get('R', 1)
            r_ratio = r_slm / r_llm if (r_llm == r_llm and r_slm == r_slm and r_llm > 0) else float('nan')

            s_llm = llm_metrics.get('S', 1)
            s_slm = slm_metrics.get('S', 1)
            s_ratio = s_slm / s_llm if (s_llm == s_llm and s_slm == s_slm and s_llm > 0) else float('nan')

            f_ratio = slm_metrics.get('F', 0) / (llm_metrics.get('F', 1) or 1)
            cov_ratio = slm_metrics.get('Cov', 0) / (llm_metrics.get('Cov', 1) or 1)

            # Format with NaN handling
            r_str = "—" if (isinstance(r_ratio, float) and r_ratio != r_ratio) else f"{r_ratio:.3f}"
            s_str = "—" if (isinstance(s_ratio, float) and s_ratio != s_ratio) else f"{s_ratio:.3f}"

            # Determine if SLM is "best" (max ratio)
            valid_ratios = [x for x in [a_ratio, r_ratio, s_ratio, f_ratio, cov_ratio] if isinstance(x, float) and x == x]
            is_best = "[OK]" if valid_ratios and max(valid_ratios) > 0.85 else "    "

            print(f"{slm:<30} | {a_ratio:>8.3f} | {r_str:>8} | {s_str:>8} | {f_ratio:>8.3f} | {cov_ratio:>8.3f} | {is_best:>6}")

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)

    # Calculate all metrics
    capability_metrics, operational_metrics = calculate_sddf2_metrics()

    # Generate output tables
    generate_capability_table(capability_metrics)
    generate_operational_table(operational_metrics)
    generate_performance_ratios(capability_metrics)

    print("\n" + "=" * 120)
    print("SDDF-2 CALCULATION COMPLETE")
    print("=" * 120)
