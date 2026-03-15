import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from src.data_loaders import load_dataset_config
from src.metrics import accuracy, agreement, is_correct, mean_latency, normalize_answer
from src.parsers import extract_final_answer
from src.prompts import build_perturbed_question, build_prompt
from src.runners import GeminiRunner, HuggingFaceRunner, LocalSLMRunner, RunnerConfigError


def load_config(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def make_runner(model_cfg, dry_run: bool):
    if model_cfg.get("type") == "gemini":
        return GeminiRunner(
            model_id=model_cfg.get("id", "api"),
            api_url_env=model_cfg.get("api_url_env"),
            api_key_env=model_cfg.get("api_key_env"),
            dry_run=dry_run,
        )
    if model_cfg.get("type") == "huggingface":
        return HuggingFaceRunner(
            model_id=model_cfg.get("id", "hf"),
            hf_model=model_cfg.get("hf_model"),
            api_key_env=model_cfg.get("api_key_env", "HF_API_KEY"),
            dry_run=dry_run,
        )
    return LocalSLMRunner(
        model_id=model_cfg.get("id", "local"),
        endpoint_env=model_cfg.get("endpoint_env"),
        provider_model=model_cfg.get("provider_model"),
        dry_run=dry_run,
    )


def execute_variant(runner, prompt: str, timeout_seconds: int, dataset_name: str, gold: str, request_id: str):
    response = runner.run(prompt, timeout=timeout_seconds, request_id=request_id)
    prediction = extract_final_answer(response.get("text"))
    return {
        "request_id": request_id,
        "status": response.get("status"),
        "mode": response.get("mode"),
        "latency": response.get("latency"),
        "error": response.get("error"),
        "text": response.get("text"),
        "prediction": prediction,
        "normalized_prediction": normalize_answer(prediction, dataset_name),
        "gold": gold,
        "normalized_gold": normalize_answer(gold, dataset_name),
        "correct": is_correct(prediction, gold, dataset_name),
    }


def score_repeat_runs(base_record, repeat_records, dataset_name: str):
    if not repeat_records:
        return {"count": 0, "accuracy": 0.0, "consistency": 0.0}
    comparison_values = [base_record.get("prediction")] + [record.get("prediction") for record in repeat_records]
    return {
        "count": len(repeat_records),
        "accuracy": accuracy(repeat_records, dataset_name),
        "consistency": agreement(comparison_values, dataset_name),
    }


def score_perturbation_runs(base_record, perturbation_records, dataset_name: str):
    if not perturbation_records:
        return {"count": 0, "accuracy": 0.0, "agreement_with_base": 0.0}
    comparison_values = [base_record.get("prediction")] + [record.get("prediction") for record in perturbation_records]
    return {
        "count": len(perturbation_records),
        "accuracy": accuracy(perturbation_records, dataset_name),
        "agreement_with_base": agreement(comparison_values, dataset_name),
    }


def evaluate_sample(idx, sample, runner, dataset_name: str, protocol_cfg, timeout_seconds: int):
    question = sample["question"]
    gold = sample.get("answer")
    base_prompt = build_prompt(question)
    base_record = execute_variant(
        runner, base_prompt, timeout_seconds, dataset_name, gold, request_id=f"{dataset_name}:{runner.model_id}:{idx}:base"
    )
    repeat_records = []
    repeat_total = max(0, int(protocol_cfg.get("repeats_on_subset", 0)) - 1)
    if idx < int(protocol_cfg.get("repeats_on_subset", 0)):
        for repeat_idx in range(repeat_total):
            repeat_records.append(
                execute_variant(
                    runner,
                    base_prompt,
                    timeout_seconds,
                    dataset_name,
                    gold,
                    request_id=f"{dataset_name}:{runner.model_id}:{idx}:repeat:{repeat_idx}",
                )
            )
    perturbation_records = []
    repeat_subset = int(protocol_cfg.get("repeats_on_subset", 0))
    perturb_limit = int(protocol_cfg.get("robustness_perturbations", 0))
    if repeat_subset <= idx < repeat_subset + perturb_limit:
        perturb_prompt = build_prompt(build_perturbed_question(question, "paraphrase"))
        perturbation_records.append(
            execute_variant(
                runner,
                perturb_prompt,
                timeout_seconds,
                dataset_name,
                gold,
                request_id=f"{dataset_name}:{runner.model_id}:{idx}:perturb:paraphrase",
            )
        )
    return {
        "idx": idx,
        "question": question,
        "difficulty": sample.get("difficulty"),
        "source": sample.get("source"),
        "base": base_record,
        "repeats": repeat_records,
        "perturbations": perturbation_records,
        "repeat_metrics": score_repeat_runs(base_record, repeat_records, dataset_name),
        "perturbation_metrics": score_perturbation_runs(base_record, perturbation_records, dataset_name),
    }


def summarize_records(records, dataset_name: str):
    base_records = [record["base"] for record in records]
    repeat_records = [item for record in records for item in record["repeats"]]
    perturb_records = [item for record in records for item in record["perturbations"]]
    failed_records = [item for item in base_records + repeat_records + perturb_records if item.get("status") != "ok"]
    repeat_groups = sum(1 for record in records if record["repeat_metrics"]["count"] > 0)
    perturb_groups = sum(1 for record in records if record["perturbation_metrics"]["count"] > 0)
    return {
        "n": len(records),
        "accuracy": accuracy(base_records, dataset_name),
        "latency": mean_latency(base_records),
        "repeat_accuracy": accuracy(repeat_records, dataset_name) if repeat_records else 0.0,
        "repeat_consistency": (
            sum(record["repeat_metrics"]["consistency"] for record in records if record["repeat_metrics"]["count"] > 0)
            / max(1, repeat_groups)
        ),
        "perturbation_accuracy": accuracy(perturb_records, dataset_name) if perturb_records else 0.0,
        "perturbation_agreement": (
            sum(record["perturbation_metrics"]["agreement_with_base"] for record in records if record["perturbation_metrics"]["count"] > 0)
            / max(1, perturb_groups)
        ),
        "failure_count": len(failed_records),
    }


def run_once(dataset_cfg, model_cfg, protocol_cfg, runner_cfg, seed: int, dry_run: bool):
    dataset_seed = seed + sum(ord(ch) for ch in f"{dataset_cfg['name']}:{model_cfg['id']}")
    samples = load_dataset_config(dataset_cfg["path"], dataset_cfg["sample_size"], seed=dataset_seed)
    runner = make_runner(model_cfg, dry_run=dry_run)
    timeout_seconds = int(runner_cfg.get("timeout_seconds", 60))
    concurrency = max(1, int(runner_cfg.get("concurrency", 1)))
    records = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {
            executor.submit(evaluate_sample, idx, sample, runner, dataset_cfg["name"], protocol_cfg, timeout_seconds): idx
            for idx, sample in enumerate(samples)
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                records.append(future.result())
            except RunnerConfigError:
                raise
            except Exception as exc:
                sample = samples[idx]
                records.append(
                    {
                        "idx": idx,
                        "question": sample.get("question"),
                        "difficulty": sample.get("difficulty"),
                        "source": sample.get("source"),
                        "base": {
                            "request_id": f"{dataset_cfg['name']}:{model_cfg['id']}:{idx}:base",
                            "status": "error",
                            "mode": "dry_run" if dry_run else "live",
                            "latency": 0.0,
                            "error": str(exc),
                            "text": None,
                            "prediction": None,
                            "normalized_prediction": None,
                            "gold": sample.get("answer"),
                            "normalized_gold": normalize_answer(sample.get("answer"), dataset_cfg["name"]),
                            "correct": False,
                        },
                        "repeats": [],
                        "perturbations": [],
                        "repeat_metrics": {"count": 0, "accuracy": 0.0, "consistency": 0.0},
                        "perturbation_metrics": {"count": 0, "accuracy": 0.0, "agreement_with_base": 0.0},
                    }
                )
    records.sort(key=lambda record: record["idx"])
    return {
        "model": model_cfg["id"],
        "dataset": dataset_cfg["name"],
        "seed": dataset_seed,
        "mode": "dry_run" if dry_run else "live",
        "summary": summarize_records(records, dataset_cfg["name"]),
        "records": records,
    }


def run_benchmark(config_path: str | Path, output_path: str | Path, seed: int = 12345, dry_run: bool = False):
    cfg = load_config(config_path)
    results = []
    models = cfg.get("models", [])
    datasets = cfg.get("datasets", [])
    protocol_cfg = cfg.get("protocol", {})
    runner_cfg = cfg.get("runner", {})
    api_models = [model for model in models if model.get("type") in {"api", "gemini", "huggingface"}]
    local_models = [model for model in models if model.get("type") == "local"]
    ordered = api_models + local_models
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for model_cfg in ordered:
        for dataset_cfg in datasets:
            print(f"Running {model_cfg['id']} on {dataset_cfg['name']} ({dataset_cfg['sample_size']} samples, dry_run={dry_run})")
            experiment = run_once(dataset_cfg, model_cfg, protocol_cfg, runner_cfg, seed, dry_run)
            print(json.dumps({"model": experiment["model"], "dataset": experiment["dataset"], **experiment["summary"]}))
            results.append(experiment)
            partial_output = {
                "seed": seed,
                "mode": "dry_run" if dry_run else "live",
                "config_path": str(config_path),
                "experiments": results,
                "progress": f"{len(results)}/{len(ordered) * len(datasets)} experiments complete",
            }
            output_path.write_text(json.dumps(partial_output, indent=2), encoding="utf-8")
    output = {"seed": seed, "mode": "dry_run" if dry_run else "live", "config_path": str(config_path), "experiments": results}
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Saved final results to {output_path}")
    return output
