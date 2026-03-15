"""
Run real Gemini API evaluation without the SDK.
Uses direct REST API calls to get genuine Gemini responses.
"""
import json
import os
import time
from pathlib import Path

import requests

from eval_pipeline.data_loaders import load_dataset_config
from eval_pipeline.metrics import is_correct
from eval_pipeline.parsers import extract_final_answer


MODEL_ID = "gemini-2.5-flash"
API_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
ROOT = Path(__file__).resolve().parent.parent
RAW_RESULTS_DIR = ROOT / "results" / "raw"


def build_prompt(question: str) -> str:
    return f"""Solve this math problem step by step, then provide your final answer.

Problem: {question}

Please format your final answer as:
Final Answer: [your answer]"""


def call_gemini(api_key: str, prompt: str):
    last_error = None
    for attempt in range(5):
        start = time.time()
        response = requests.post(
            API_TEMPLATE.format(model=MODEL_ID, key=api_key),
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=120,
        )
        latency = time.time() - start
        if response.status_code == 429:
            last_error = f"HTTP 429: {response.text[:300]}"
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return text, latency, None
    return None, 0, last_error or "HTTP 429 after retries"


def evaluate_gemini(api_key: str, dataset_name: str, sample_size: int = 30):
    print(f"\n{'=' * 80}")
    print(f"Evaluating Gemini on {dataset_name} ({sample_size} samples)")
    print(f"{'=' * 80}")

    samples = load_dataset_config(f"data/{dataset_name.lower()}.jsonl", sample_size, seed=12345)
    records = []

    for idx, sample in enumerate(samples):
        question = sample["question"]
        gold = sample.get("answer")
        prompt = build_prompt(question)

        try:
            output_text, latency, api_error = call_gemini(api_key, prompt)
            if api_error:
                raise RuntimeError(api_error)

            prediction = extract_final_answer(output_text)
            correct = is_correct(prediction, gold, dataset_name)

            records.append(
                {
                    "idx": idx,
                    "question": question,
                    "gold": gold,
                    "prediction": prediction,
                    "correct": correct,
                    "latency": latency,
                    "output": output_text[:200],
                }
            )

            status = "[OK]" if correct else "[X]"
            print(f"  [{idx + 1:2}/{sample_size}] {status} Latency: {latency:.2f}s | Pred: {prediction}")
            time.sleep(1)

        except Exception as e:
            print(f"  [{idx + 1:2}/{sample_size}] [X] ERROR: {str(e)[:120]}")
            records.append(
                {
                    "idx": idx,
                    "question": question,
                    "gold": gold,
                    "prediction": None,
                    "correct": False,
                    "latency": 0,
                    "error": str(e),
                }
            )

    correct_count = sum(1 for r in records if r["correct"])
    accuracy = correct_count / len(records) * 100 if records else 0
    avg_latency = sum(r.get("latency", 0) for r in records) / len(records) if records else 0

    print(f"\n{dataset_name} Results:")
    print(f"  Accuracy: {accuracy:.1f}% ({correct_count}/{len(records)})")
    print(f"  Avg Latency: {avg_latency:.2f}s")
    print(f"  Throughput: {60 / avg_latency:.2f} queries/min" if avg_latency else "  Throughput: 0.00 queries/min")

    return {
        "dataset": dataset_name,
        "accuracy": accuracy / 100,
        "latency": avg_latency,
        "records": records,
    }


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Enter Gemini API Key: ")

    print("\nStarting Real Gemini API Evaluation...")
    print(f"API Key: {api_key[:12]}...")

    results = []
    for dataset in ["gsm8k", "svamp"]:
        results.append(evaluate_gemini(api_key, dataset.upper(), sample_size=30))

    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": "gemini_2_5_flash_real",
        "mode": "live_api",
        "results": results,
    }

    RAW_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = RAW_RESULTS_DIR / "results_gemini_real_api.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 80}")

    print("\nSummary:")
    for result in results:
        print(
            f"  {result['dataset']:8} | Accuracy: {result['accuracy'] * 100:5.1f}% | "
            f"Latency: {result['latency']:6.2f}s"
        )


if __name__ == "__main__":
    main()
