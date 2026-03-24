from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from datasets import load_dataset

from .config import BUILTIN_SAMPLE_PLANS, DEFAULT_LABEL_COLUMNS, DEFAULT_SEED, DEFAULT_TEXT_COLUMNS, UserDatasetConfig


def _first_existing_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def infer_text_column(df: pd.DataFrame, explicit_name: str | None = None) -> str:
    if explicit_name:
        if explicit_name not in df.columns:
            raise ValueError(f"Text column '{explicit_name}' not found in uploaded data")
        return explicit_name

    inferred = _first_existing_column(df, DEFAULT_TEXT_COLUMNS)
    if inferred:
        return inferred

    text_columns = df.select_dtypes(include=["object", "string"]).columns.tolist()
    if not text_columns:
        raise ValueError("No text-like column found in uploaded data")

    return text_columns[0]


def infer_label_column(df: pd.DataFrame, explicit_name: str | None = None) -> str:
    if explicit_name:
        if explicit_name not in df.columns:
            raise ValueError(f"Label column '{explicit_name}' not found in uploaded data")
        return explicit_name

    inferred = _first_existing_column(df, DEFAULT_LABEL_COLUMNS)
    if inferred:
        return inferred

    raise ValueError(
        "Could not infer the label column. Pass --label-column when running a custom dataset."
    )


def get_diverse_stratified_sample(
    dataset: pd.DataFrame | list[dict],
    num_samples_per_class: int,
    label_column: str = "label",
    text_column: str | None = None,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """
    Perform label-balanced sampling with light diversity controls.

    This removes duplicate texts within a label and spreads selections across
    short, medium, and long examples where possible.
    """
    df = pd.DataFrame(dataset).copy()
    if df.empty:
        return df

    text_column = infer_text_column(df, text_column)
    df[text_column] = df[text_column].fillna("").astype(str)
    df["_normalized_text"] = (
        df[text_column].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    )

    sampled_groups = []
    for _, group in df.groupby(label_column, sort=False):
        group = group.drop_duplicates(subset="_normalized_text").copy()
        target = min(len(group), num_samples_per_class)

        if target == 0:
            continue
        if len(group) <= target:
            sampled_groups.append(group)
            continue

        group["_text_len"] = group[text_column].str.len()
        bucket_count = min(3, target)

        if bucket_count > 1 and group["_text_len"].nunique() > 1:
            group["_length_bucket"] = pd.qcut(
                group["_text_len"],
                q=bucket_count,
                labels=False,
                duplicates="drop",
            )
        else:
            group["_length_bucket"] = 0

        bucket_ids = list(pd.Series(group["_length_bucket"]).dropna().unique())
        bucket_ids.sort()

        selected_parts = []
        remaining = target

        for bucket_id in bucket_ids:
            bucket = group[group["_length_bucket"] == bucket_id]
            bucket_target = remaining // len(bucket_ids) if bucket_ids else 0
            if bucket_target == 0 and remaining > 0:
                bucket_target = 1

            take = min(len(bucket), bucket_target)
            if take > 0:
                selected_parts.append(bucket.sample(n=take, random_state=seed))
                remaining -= take

        selected = pd.concat(selected_parts).drop_duplicates() if selected_parts else group.iloc[0:0]

        if len(selected) < target:
            leftovers = group.drop(index=selected.index, errors="ignore")
            refill = min(len(leftovers), target - len(selected))
            if refill > 0:
                selected = pd.concat(
                    [selected, leftovers.sample(n=refill, random_state=seed)]
                )

        sampled_groups.append(selected)

    sampled_df = pd.concat(sampled_groups, ignore_index=True)
    sampled_df = sampled_df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return sampled_df.drop(columns=["_normalized_text", "_text_len", "_length_bucket"], errors="ignore")


def _load_tabular_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        if isinstance(raw, dict):
            if "data" in raw and isinstance(raw["data"], list):
                return pd.DataFrame(raw["data"])
            return pd.DataFrame(raw)
    raise ValueError("Unsupported file format. Use CSV, JSONL, or JSON.")


def _normalize_user_labels(df: pd.DataFrame, label_column: str, labels: list[str]) -> tuple[pd.DataFrame, list[str]]:
    normalized_df = df.copy()
    if labels:
        if pd.api.types.is_numeric_dtype(normalized_df[label_column]):
            normalized_df[label_column] = normalized_df[label_column].map(
                lambda value: labels[int(value)] if pd.notna(value) and int(value) < len(labels) else value
            )
        normalized_df[label_column] = normalized_df[label_column].astype(str)
        return normalized_df, labels

    normalized_df[label_column] = normalized_df[label_column].astype(str)
    inferred_labels = normalized_df[label_column].dropna().unique().tolist()
    return normalized_df, sorted(inferred_labels)


def load_uploaded_dataset(config: UserDatasetConfig) -> dict[str, dict]:
    if not config.path.exists():
        raise FileNotFoundError(f"Uploaded dataset not found: {config.path}")

    df = _load_tabular_file(config.path)
    if df.empty:
        raise ValueError("Uploaded dataset is empty")

    text_column = infer_text_column(df, config.text_column)
    label_column = infer_label_column(df, config.label_column)
    df, labels = _normalize_user_labels(df, label_column, config.labels)

    standardized = pd.DataFrame(
        {
            "text": df[text_column].fillna("").astype(str),
            "label": df[label_column],
        }
    )
    standardized = standardized[standardized["text"].str.strip() != ""].reset_index(drop=True)

    if config.sample_per_class:
        standardized = get_diverse_stratified_sample(
            standardized,
            num_samples_per_class=config.sample_per_class,
            label_column="label",
            text_column="text",
            seed=config.seed,
        )

    if config.max_samples and len(standardized) > config.max_samples:
        standardized = standardized.sample(n=config.max_samples, random_state=config.seed).reset_index(drop=True)

    return {
        config.dataset_name: {
            "data": standardized,
            "labels": labels,
            "type": config.task_type,
        }
    }


def load_builtin_datasets(sample_profile: str = "fast15") -> dict[str, dict]:
    if sample_profile not in BUILTIN_SAMPLE_PLANS:
        raise ValueError(f"Unknown sample profile: {sample_profile}")

    plan = BUILTIN_SAMPLE_PLANS[sample_profile]
    results: dict[str, dict] = {}

    if "SST-2" in plan:
        print("Loading SST-2...")
        sst2 = load_dataset("glue", "sst2", split="validation")
        results["SST-2"] = {
            "data": get_diverse_stratified_sample(sst2, plan["SST-2"], "label", seed=DEFAULT_SEED),
            "labels": ["negative", "positive"],
            "type": "Sentiment",
        }

    if "Emotion" in plan:
        print("Loading Emotion...")
        emotion = load_dataset("dair-ai/emotion", split="test")
        results["Emotion"] = {
            "data": get_diverse_stratified_sample(emotion, plan["Emotion"], "label", seed=DEFAULT_SEED),
            "labels": ["sadness", "joy", "love", "anger", "fear", "surprise"],
            "type": "Emotion",
        }

    if "AG News" in plan:
        print("Loading AG News...")
        ag_news = load_dataset("ag_news", split="test")
        results["AG News"] = {
            "data": get_diverse_stratified_sample(ag_news, plan["AG News"], "label", seed=DEFAULT_SEED),
            "labels": ["World", "Sports", "Business", "Sci/Tech"],
            "type": "Topic",
        }

    if "BANKING77" in plan:
        print("Loading BANKING77...")
        banking77 = None
        for dataset_name in ("PolyAI/banking77", "banking77"):
            try:
                banking77 = load_dataset(dataset_name, split="test")
                break
            except Exception as exc:
                print(f"Failed to load {dataset_name}: {exc}")

        if banking77 is not None:
            results["BANKING77"] = {
                "data": get_diverse_stratified_sample(banking77, plan["BANKING77"], "label", seed=DEFAULT_SEED),
                "labels": banking77.features["label"].names,
                "type": "Intent",
            }

    return results

