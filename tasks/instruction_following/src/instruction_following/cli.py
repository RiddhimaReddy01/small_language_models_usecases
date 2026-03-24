"""CLI entrypoint for the instruction-following evaluation pipeline."""
import argparse
import os
import time

from instruction_following.pipeline_core import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_INFERENCE_PARAMS,
    FAST_MODELS,
    FULL_MODELS,
    run_pipeline,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Run instruction-following evaluation.")
    parser.add_argument(
        "--preset",
        choices=["fast", "full"],
        default="fast",
        help="Named local-model preset to run.",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        help="Optional explicit list of model ids. Prefix hosted HF models with 'hf_api:'. Overrides --preset.",
    )
    parser.add_argument("--num-prompts", type=int, default=None, help="Number of prompts to evaluate.")
    parser.add_argument("--device", default="cpu", help="Torch device map, e.g. cpu or cuda.")
    parser.add_argument("--output", default=None, help="Output JSON path.")
    parser.add_argument("--dataset", default="google/IFEval", help="Dataset name to load.")
    parser.add_argument("--include-gemini", action="store_true", help="Include a Gemini baseline run.")
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL, help="Gemini model id.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_INFERENCE_PARAMS["max_new_tokens"])
    parser.add_argument("--temperature", type=float, default=DEFAULT_INFERENCE_PARAMS["temperature"])
    parser.add_argument("--top-p", type=float, default=DEFAULT_INFERENCE_PARAMS["top_p"])
    return parser.parse_args()


def main():
    args = parse_args()
    models = args.models if args.models else (FAST_MODELS if args.preset == "fast" else FULL_MODELS)
    if args.include_gemini and args.gemini_model not in models:
        models = list(models) + [args.gemini_model]

    num_prompts = args.num_prompts if args.num_prompts is not None else (20 if args.preset == "fast" else 40)
    output = args.output if args.output else (
        "results/results_with_baseline.json" if args.include_gemini else "results/results_detailed.json"
    )
    inference_params = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "do_sample": False,
        "max_new_tokens": args.max_new_tokens,
    }

    start = time.time()
    print("=" * 100)
    print("INSTRUCTION FOLLOWING EVALUATION")
    print("=" * 100)
    print(f"Preset: {args.preset} | Prompts: {num_prompts} | Device: {args.device}")
    print(f"Models: {models}")
    print()

    run_pipeline(
        models=models,
        num_prompts=num_prompts,
        device=args.device,
        output_path=output,
        inference_params=inference_params,
        include_gemini=args.include_gemini,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=args.gemini_model,
        dataset_name=args.dataset,
    )

    elapsed = time.time() - start
    print(f"\nTotal runtime: {elapsed:.0f}s ({elapsed/60:.1f}m)")


if __name__ == "__main__":
    main()
