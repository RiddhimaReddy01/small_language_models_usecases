"""Shared pipeline utilities for instruction-following evaluation."""
import json
import os
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

import psutil
import torch
from datasets import load_dataset
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from sddf.ingest import normalize_instruction_following_results
from sddf.pipeline import run_sddf_postprocess

from instruction_following.constraint_validators import ConstraintValidator

if TYPE_CHECKING:
    from instruction_following.gemini_wrapper import GeminiClient

DEFAULT_INFERENCE_PARAMS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "do_sample": False,
    "max_new_tokens": 120,
}

FAST_MODELS = [
    "Qwen/Qwen2.5-Coder-0.5B",
    "deepseek-ai/deepseek-coder-1.3b-base",
]

FULL_MODELS = [
    "Qwen/Qwen2.5-Coder-0.5B",
    "deepseek-ai/deepseek-coder-1.3b-base",
    "Qwen/Qwen2.5-Coder-1.5B",
]

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_fallback_dataset(num_samples: int) -> List[Dict]:
    """Generate a tiny deterministic fallback dataset."""
    prompts = [
        {
            "instruction": "What is machine learning? Answer in exactly 15 words.",
            "constraints": [{"type": "length", "length_type": "exactly", "value": 15}],
        },
        {
            "instruction": "List benefits of Python as bullet points.",
            "constraints": [{"type": "format", "format": "bullets"}],
        },
        {
            "instruction": "Explain AI without using 'intelligence' or 'learning'.",
            "constraints": [{"type": "exclusion", "words": ["intelligence", "learning"]}],
        },
        {
            "instruction": "Describe climate change in under 40 words.",
            "constraints": [{"type": "length", "length_type": "at_most", "value": 40}],
        },
        {
            "instruction": "Write about Python programming and include 'efficient'.",
            "constraints": [{"type": "inclusion", "words": ["efficient"]}],
        },
    ]
    return (prompts * ((num_samples // len(prompts)) + 1))[:num_samples]


def load_dataset_sample(num_samples: int, dataset_name: str = "google/IFEval") -> List[Dict]:
    """Load a deterministic sample from the evaluation dataset."""
    print(f"Loading dataset: {dataset_name}")
    try:
        dataset = load_dataset(dataset_name, split="train")
        sampled = dataset.select(range(min(num_samples, len(dataset))))
        prompts = [
            {
                "instruction": item["prompt"] if "prompt" in item else item["instruction"],
                "constraints": item.get("constraints", []),
            }
            for item in sampled
        ]
        print(f"Loaded {len(prompts)} prompts from {dataset_name}")
        return prompts
    except Exception as exc:
        print(f"Using fallback dataset because loading failed: {exc}")
        return generate_fallback_dataset(num_samples)


def load_local_model(model_name: str, device: str):
    """Load a local Hugging Face model for inference."""
    print(f"Loading local model: {model_name}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float32,
            device_map=device,
            low_cpu_mem_usage=True,
        )
        model.eval()
        torch.set_grad_enabled(False)
        return model, tokenizer
    except Exception as exc:
        print(f"Skipping {model_name}: {exc}")
        return None, None


def generate_local_response(model, tokenizer, instruction: str, device: str, inference_params: Dict) -> Tuple[str, float, int]:
    """Generate a response from a local model."""
    prompt = f"Follow the instruction exactly.\n\nInstruction:\n{instruction}\n\nResponse:"
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    start_time = time.time()

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            temperature=inference_params["temperature"],
            top_p=inference_params["top_p"],
            do_sample=inference_params["do_sample"],
            max_new_tokens=inference_params["max_new_tokens"],
            pad_token_id=tokenizer.pad_token_id,
        )

    latency = time.time() - start_time
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "Response:" in response:
        response = response.split("Response:")[-1].strip()

    output_tokens = outputs.shape[1] - inputs["input_ids"].shape[1]
    return response, latency, output_tokens


def init_result(model_name: str, num_prompts: int, is_baseline: bool = False) -> Dict:
    """Create an empty result payload."""
    return {
        "model": model_name,
        "num_prompts": num_prompts,
        "is_baseline": is_baseline,
        "capability_metrics": {
            "pass_rate": 0.0,
            "constraint_satisfaction_rate": 0.0,
            "format_compliance": 0.0,
            "length_compliance": 0.0,
            "lexical_compliance": 0.0,
        },
        "reliability_metrics": {
            "constraint_violation_rate": 0.0,
            "format_error_rate": 0.0,
            "overgeneration_rate": 0.0,
            "undergeneration_rate": 0.0,
        },
        "operational_metrics": {
            "avg_latency_sec": 0.0,
            "avg_tokens_per_second": 0.0,
            "avg_memory_usage_mb": 0.0,
            "avg_output_tokens": 0.0,
        },
        "responses": [],
    }


def finalize_result(results: Dict, counts: Dict) -> Dict:
    """Populate aggregate metrics from counters."""
    n = counts["evaluated_prompts"]
    total_constraints = counts["total_constraints"]

    if n == 0:
        return results

    results["num_prompts"] = n
    results["capability_metrics"]["pass_rate"] = counts["full_passes"] / n
    results["capability_metrics"]["constraint_satisfaction_rate"] = (
        counts["total_satisfied"] / total_constraints if total_constraints > 0 else 1.0
    )
    results["capability_metrics"]["format_compliance"] = (
        counts["format_satisfied"] / counts["format_total"] if counts["format_total"] > 0 else 1.0
    )
    results["capability_metrics"]["length_compliance"] = (
        counts["length_satisfied"] / counts["length_total"] if counts["length_total"] > 0 else 1.0
    )
    results["capability_metrics"]["lexical_compliance"] = (
        counts["lexical_satisfied"] / counts["lexical_total"] if counts["lexical_total"] > 0 else 1.0
    )

    results["reliability_metrics"]["constraint_violation_rate"] = (
        counts["constraint_violations"] / (total_constraints if total_constraints > 0 else 1)
    )
    results["reliability_metrics"]["format_error_rate"] = counts["format_errors"] / n
    results["reliability_metrics"]["overgeneration_rate"] = counts["overgeneration_count"] / n
    results["reliability_metrics"]["undergeneration_rate"] = counts["undergeneration_count"] / n

    results["operational_metrics"]["avg_latency_sec"] = counts["total_latency"] / n
    results["operational_metrics"]["avg_tokens_per_second"] = (
        counts["total_tokens"] / counts["total_latency"] if counts["total_latency"] > 0 else 0.0
    )
    results["operational_metrics"]["avg_memory_usage_mb"] = (
        sum(counts["memory_usage"]) / len(counts["memory_usage"]) if counts["memory_usage"] else 0.0
    )
    results["operational_metrics"]["avg_output_tokens"] = counts["total_tokens"] / n
    return results


def init_counters() -> Dict:
    """Create accumulator counters for evaluation."""
    return {
        "full_passes": 0,
        "total_satisfied": 0,
        "total_constraints": 0,
        "format_satisfied": 0,
        "format_total": 0,
        "length_satisfied": 0,
        "length_total": 0,
        "lexical_satisfied": 0,
        "lexical_total": 0,
        "constraint_violations": 0,
        "format_errors": 0,
        "overgeneration_count": 0,
        "undergeneration_count": 0,
        "total_latency": 0.0,
        "total_tokens": 0,
        "memory_usage": [],
        "evaluated_prompts": 0,
    }


def record_response(results: Dict, counts: Dict, instruction: str, response: str, latency: float, output_tokens: int, constraints: List[Dict]) -> None:
    """Update counters and store a single response."""
    satisfied, total, detailed_metrics = ConstraintValidator.validate_constraints(response, constraints)
    instruction_words = len(instruction.split())
    response_words = len(response.split())

    if response_words > instruction_words * 5:
        counts["overgeneration_count"] += 1
    if response_words < 3:
        counts["undergeneration_count"] += 1

    if satisfied == total:
        counts["full_passes"] += 1

    counts["total_satisfied"] += satisfied
    counts["total_constraints"] += total
    counts["format_satisfied"] += detailed_metrics["format_satisfied"]
    counts["format_total"] += detailed_metrics["format_total"]
    counts["length_satisfied"] += detailed_metrics["length_satisfied"]
    counts["length_total"] += detailed_metrics["length_total"]
    counts["lexical_satisfied"] += detailed_metrics["lexical_satisfied"]
    counts["lexical_total"] += detailed_metrics["lexical_total"]
    counts["constraint_violations"] += len(detailed_metrics["constraint_violations"])
    counts["total_latency"] += latency
    counts["total_tokens"] += output_tokens
    counts["evaluated_prompts"] += 1

    if any(v.get("type") == "format" for v in detailed_metrics["constraint_violations"]):
        counts["format_errors"] += 1

    results["responses"].append(
        {
            "instruction": instruction,
            "response": response,
            "constraints_satisfied": satisfied,
            "total_constraints": total,
            "pass": satisfied == total,
            "latency_sec": latency,
            "output_tokens": output_tokens,
        }
    )


def evaluate_local_model(model_name: str, prompts: List[Dict], device: str, inference_params: Dict) -> Optional[Dict]:
    """Evaluate one local model across prompts."""
    model, tokenizer = load_local_model(model_name, device)
    if model is None or tokenizer is None:
        return None

    results = init_result(model_name, len(prompts), is_baseline=False)
    counts = init_counters()
    process = psutil.Process(os.getpid())

    for prompt_data in tqdm(prompts, desc=model_name):
        instruction = prompt_data["instruction"]
        constraints = prompt_data.get("constraints", [])

        mem_before = process.memory_info().rss / 1024 / 1024
        response, latency, output_tokens = generate_local_response(
            model, tokenizer, instruction, device, inference_params
        )
        mem_after = process.memory_info().rss / 1024 / 1024
        counts["memory_usage"].append((mem_after - mem_before) / 2)

        record_response(results, counts, instruction, response, latency, output_tokens, constraints)

    del model
    del tokenizer
    torch.cuda.empty_cache()
    return finalize_result(results, counts)


def evaluate_gemini_model(gemini_client: "GeminiClient", prompts: List[Dict]) -> Optional[Dict]:
    """Evaluate Gemini across prompts until deprecated or exhausted."""
    if not gemini_client.is_available():
        print(f"Gemini unavailable, skipping baseline for {gemini_client.model_name}")
        return None

    results = init_result(f"{gemini_client.model_name} [BASELINE]", len(prompts), is_baseline=True)
    counts = init_counters()

    for prompt_data in tqdm(prompts, desc=gemini_client.model_name):
        if not gemini_client.is_available():
            print(f"[DEPRECATION] {gemini_client.model_name} unavailable - stopping evaluation")
            break

        instruction = prompt_data["instruction"]
        constraints = prompt_data.get("constraints", [])
        response, latency, output_tokens = gemini_client.generate(instruction)

        if response is None:
            continue

        record_response(results, counts, instruction, response, latency, output_tokens, constraints)

    if counts["evaluated_prompts"] == 0:
        return None

    results = finalize_result(results, counts)
    if gemini_client.deprecated and gemini_client.error_message:
        results["note"] = gemini_client.error_message
    return results


def print_metrics_table(all_results: Sequence[Dict]) -> None:
    """Print concise capability/reliability and operational tables."""
    if not all_results:
        print("No results to display.")
        return

    print("\n" + "=" * 140)
    print("CAPABILITY + RELIABILITY METRICS")
    print("=" * 140)
    print(
        f"{'Model':<40} {'Prompts':<8} {'Pass':<8} {'CSR':<8} {'Format':<8} {'Length':<8} "
        f"{'Lexical':<8} {'Viol.':<8} {'FmtErr':<8} {'Over':<8} {'Under':<8}"
    )
    print("-" * 140)
    for result in all_results:
        capability = result["capability_metrics"]
        reliability = result["reliability_metrics"]
        print(
            f"{result['model']:<40} {result['num_prompts']:<8} "
            f"{capability['pass_rate']:<8.1%} {capability['constraint_satisfaction_rate']:<8.1%} "
            f"{capability['format_compliance']:<8.1%} {capability['length_compliance']:<8.1%} "
            f"{capability['lexical_compliance']:<8.1%} {reliability['constraint_violation_rate']:<8.1%} "
            f"{reliability['format_error_rate']:<8.1%} {reliability['overgeneration_rate']:<8.1%} "
            f"{reliability['undergeneration_rate']:<8.1%}"
        )

    print("\n" + "=" * 110)
    print("OPERATIONAL METRICS")
    print("=" * 110)
    print(f"{'Model':<40} {'Latency(s)':<12} {'Tok/s':<12} {'Memory(MB)':<12} {'OutTok':<12}")
    print("-" * 110)
    for result in all_results:
        operational = result["operational_metrics"]
        print(
            f"{result['model']:<40} {operational['avg_latency_sec']:<12.3f} "
            f"{operational['avg_tokens_per_second']:<12.2f} {operational['avg_memory_usage_mb']:<12.2f} "
            f"{operational['avg_output_tokens']:<12.1f}"
        )


def save_results(all_results: Sequence[Dict], output_path: str) -> None:
    """Write results to disk."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(list(all_results), handle, indent=2)
    sddf_rows = normalize_instruction_following_results(list(all_results))
    run_sddf_postprocess(sddf_rows, task="instruction_following", output_dir=os.path.dirname(output_path) or ".")
    print(f"\nSaved results to {output_path}")


def run_pipeline(
    models: Sequence[str],
    num_prompts: int,
    device: str,
    output_path: str,
    inference_params: Optional[Dict] = None,
    include_gemini: bool = False,
    gemini_api_key: Optional[str] = None,
    gemini_model: Optional[str] = None,
    dataset_name: str = "google/IFEval",
) -> List[Dict]:
    """Run the evaluation pipeline and return results."""
    prompts = load_dataset_sample(num_prompts, dataset_name=dataset_name)
    results = []
    inference_params = inference_params or DEFAULT_INFERENCE_PARAMS
    gemini_model = gemini_model or DEFAULT_GEMINI_MODEL
    gemini_client = None

    if include_gemini:
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when --include-gemini is used.")
        from instruction_following.gemini_wrapper import GeminiClient

        gemini_client = GeminiClient(gemini_api_key, gemini_model)

    for model_name in models:
        if include_gemini and model_name == gemini_model:
            gemini_result = evaluate_gemini_model(gemini_client, prompts)
            if gemini_result:
                results.append(gemini_result)
            continue

        local_result = evaluate_local_model(model_name, prompts, device, inference_params)
        if local_result:
            results.append(local_result)

    print_metrics_table(results)
    save_results(results, output_path)
    return results
