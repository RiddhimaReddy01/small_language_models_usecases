from __future__ import annotations

import csv
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tqdm import tqdm


class Evaluator:
    def __init__(self, model_wrapper, num_workers=1, output_file="results/live_results.csv"):
        self.model = model_wrapper
        self.num_workers = num_workers
        self.results = []
        self.output_file = output_file
        self.lock = threading.Lock()

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["dataset", "text", "true_label", "prediction", "latency", "is_valid", "status"])

    def run_evaluation(self, dataset_name, df, labels, task_type):
        print(f"\nRunning evaluation for {dataset_name} ({task_type})...")

        start_cpu = psutil.cpu_percent(interval=None)
        start_mem = psutil.virtual_memory().used
        start_time = time.time()
        dataset_results = []

        tasks = []
        for _, row in df.iterrows():
            text = row.get("text") or row.get("sentence") or row.get("description")
            label = row["label"]
            tasks.append((text, label, labels))

        if self.num_workers <= 1:
            for text, label, task_labels in tqdm(tasks, total=len(tasks), desc=f"Evaluating {dataset_name}"):
                result = self._predict_one(dataset_name, text, label, task_labels)
                self.results.append(result)
                dataset_results.append(result)
        else:
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = [executor.submit(self._predict_one, dataset_name, t, l, lbs) for t, l, lbs in tasks]
                for future in tqdm(futures, total=len(futures), desc=f"Evaluating {dataset_name}"):
                    result = future.result()
                    self.results.append(result)
                    dataset_results.append(result)

        end_time = time.time()
        end_cpu = psutil.cpu_percent(interval=None)
        end_mem = psutil.virtual_memory().used
        latencies = [result["latency"] for result in dataset_results]

        ops_metrics = {
            "dataset": dataset_name,
            "total_samples": len(df),
            "total_time": end_time - start_time,
            "throughput": len(df) / (end_time - start_time) if end_time > start_time else 0,
            "latency_mean": np.mean(latencies) if latencies else 0,
            "latency_p95": np.percentile(latencies, 95) if latencies else 0,
            "cpu_util_avg": (start_cpu + end_cpu) / 2,
            "mem_usage_delta_mb": (end_mem - start_mem) / (1024 * 1024),
            "parse_failure_rate": sum(1 for result in dataset_results if not result["is_valid"]) / len(df),
        }
        return ops_metrics, dataset_results

    def _predict_one(self, dataset_name, text, true_label_idx, labels):
        result = {
            "text": text,
            "true_label": labels[true_label_idx] if isinstance(true_label_idx, (int, np.integer)) else true_label_idx,
            "prediction": None,
            "latency": 0,
            "is_valid": False,
            "dataset": dataset_name,
        }

        model_result = self.model.predict(text, labels)
        result["prediction"] = model_result["prediction"]
        result["latency"] = model_result["latency"]
        result["status"] = model_result["status"]

        normalized_prediction = self._match_prediction_to_label(result["prediction"], labels)
        if normalized_prediction:
            result["is_valid"] = True
            result["prediction"] = normalized_prediction

        self._save_incremental(result)
        return result

    def _match_prediction_to_label(self, prediction, labels):
        if not prediction or not isinstance(prediction, str):
            return None

        cleaned_prediction = prediction.strip().splitlines()[0].strip()
        cleaned_prediction = cleaned_prediction.strip("`\"' \t\r\n:.-")

        for label in labels:
            if cleaned_prediction.lower() == label.lower():
                return label

        normalized_prediction = re.sub(r"[^a-z0-9/+\- ]", " ", cleaned_prediction.lower())
        normalized_prediction = re.sub(r"\s+", " ", normalized_prediction).strip()

        matches = []
        for label in labels:
            normalized_label = re.sub(r"[^a-z0-9/+\- ]", " ", label.lower())
            normalized_label = re.sub(r"\s+", " ", normalized_label).strip()
            if normalized_label and re.search(rf"(?<!\w){re.escape(normalized_label)}(?!\w)", normalized_prediction):
                matches.append(label)

        if len(matches) == 1:
            return matches[0]
        return None

    def _save_incremental(self, result):
        with self.lock:
            with open(self.output_file, "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        result.get("dataset", "Unknown"),
                        result["text"],
                        result["true_label"],
                        result["prediction"],
                        result["latency"],
                        result["is_valid"],
                        result["status"],
                    ]
                )

    def calculate_capability_metrics(self, dataset_results):
        if not dataset_results:
            return {
                "accuracy": 0,
                "macro_f1": 0,
                "weighted_f1": 0,
                "precision": 0,
                "recall": 0,
                "validity_rate": 0,
            }

        y_true = [result["true_label"] for result in dataset_results]
        y_pred = [result["prediction"] if result["is_valid"] else "INVALID" for result in dataset_results]
        all_labels = list(set(y_true) | set(y_pred))

        return {
            "accuracy": accuracy_score(y_true, y_pred),
            "macro_f1": f1_score(y_true, y_pred, average="macro", labels=all_labels),
            "weighted_f1": f1_score(y_true, y_pred, average="weighted", labels=all_labels),
            "precision": precision_score(y_true, y_pred, average="macro", labels=all_labels, zero_division=0),
            "recall": recall_score(y_true, y_pred, average="macro", labels=all_labels, zero_division=0),
            "validity_rate": sum(1 for result in dataset_results if result["is_valid"]) / len(dataset_results),
        }


def save_results(all_results, ops_metrics, capability_metrics, output_dir="results", run_metadata=None):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())

    pd.DataFrame(all_results).to_csv(f"{output_dir}/raw_results_{timestamp}.csv", index=False)
    summary = {
        "metadata": run_metadata or {},
        "operational": ops_metrics,
        "capability": capability_metrics,
    }
    with open(f"{output_dir}/metrics_summary_{timestamp}.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=4)

    print(f"\nResults saved to {output_dir}/")
    return timestamp

