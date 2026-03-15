"""Run only the Gemini baseline against the first fast preset prompt slice."""
import os
import sys
import time

from pipeline_core import DEFAULT_GEMINI_MODEL, run_pipeline


def main():
    start = time.time()
    print("=" * 100)
    print("GEMINI BASELINE EVALUATION")
    print("=" * 100)

    run_pipeline(
        models=[os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)],
        num_prompts=20,
        device="cpu",
        output_path="results_with_baseline.json",
        include_gemini=True,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
    )

    elapsed = time.time() - start
    print(f"\nTotal runtime: {elapsed:.0f}s ({elapsed/60:.1f}m)")


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY before running evaluate_gemini_only.py")
    main()
