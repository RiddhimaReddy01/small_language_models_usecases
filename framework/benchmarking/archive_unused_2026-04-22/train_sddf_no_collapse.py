from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NEGATIONS = {"no", "not", "never", "none", "nothing", "neither", "nor", "without", "cannot", "can't", "won't"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
FORMAT_KEYWORDS = {"json", "yaml", "xml", "table", "bullet", "list", "format", "schema", "markdown", "csv"}
ALGO_KEYWORDS = {
    "algorithm",
    "complexity",
    "sort",
    "search",
    "binary",
    "graph",
    "tree",
    "dynamic",
    "programming",
    "hash",
    "stack",
    "queue",
    "dfs",
    "bfs",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _sentence_count(text: str) -> int:
    count = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    return max(1, count)


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    vowels = "aeiouy"
    cnt = 0
    prev = False
    for ch in w:
        is_vowel = ch in vowels
        if is_vowel and not prev:
            cnt += 1
        prev = is_vowel
    if w.endswith("e") and cnt > 1:
        cnt -= 1
    return max(1, cnt)


def _readability_fk(text: str) -> float:
    words = _tokenize(text)
    wc = max(1, len(words))
    sc = _sentence_count(text)
    syll = sum(_syllables(w) for w in words)
    return 0.39 * (wc / sc) + 11.8 * (syll / wc) - 15.59


def _readability_fog(text: str) -> float:
    words = _tokenize(text)
    wc = max(1, len(words))
    sc = _sentence_count(text)
    complex_words = sum(1 for w in words if _syllables(w) >= 3)
    return 0.4 * ((wc / sc) + 100.0 * (complex_words / wc))


def _entity_count(text: str) -> int:
    return len(re.findall(r"\b[A-Z][a-zA-Z]+\b", text))


def _feature_vector(task: str, prompt: str, features: list[str]) -> list[float]:
    tokens = _tokenize(prompt)
    token_count = len(tokens)
    sentence_count = _sentence_count(prompt)
    avg_sentence_length = token_count / max(1, sentence_count)
    entity_count = _entity_count(prompt)
    values: dict[str, float] = {
        "token_count": float(token_count),
        "sentence_count": float(sentence_count),
        "avg_sentence_length": float(avg_sentence_length),
        "readability_fk": float(_readability_fk(prompt)),
        "readability_fog": float(_readability_fog(prompt)),
        "negation_count": float(sum(1 for t in tokens if t in NEGATIONS)),
        "modal_verb_count": float(sum(1 for t in tokens if t in MODALS)),
        "clause_count": float(prompt.count(",") + prompt.count(";") + prompt.count(":")),
        "entity_count": float(entity_count),
        "entity_density": float(entity_count / max(1, token_count)),
        "entity_type_diversity": float(min(entity_count, 6)),
        "format_keyword_count": float(sum(1 for t in tokens if t in FORMAT_KEYWORDS)),
        "algorithm_keyword_count": float(sum(1 for t in tokens if t in ALGO_KEYWORDS)),
        "numeric_density": float(len(re.findall(r"\d", prompt)) / max(1, token_count)),
        "symbol_count": float(len(re.findall(r"[+\-*/=<>^%(){}\[\]]", prompt))),
        "context_length": float(token_count),
        "question_length": float(token_count),
        "source_length": float(token_count),
    }
    # Task-aware fallback for context/source/question style prompts.
    if task == "retrieval_grounded":
        values["context_length"] = float(len(_tokenize(prompt.split("Question", 1)[0])))
        values["question_length"] = float(token_count - values["context_length"])
    if task == "summarization":
        values["source_length"] = float(len(_tokenize(prompt.split("Summary", 1)[0])))
    return [float(values.get(name, 0.0)) for name in features]


def _label_is_fail(row: dict[str, Any]) -> int:
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            rows.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return rows


def _zscore_fit(x: list[list[float]]) -> tuple[list[float], list[float]]:
    cols = len(x[0])
    means = []
    stds = []
    for j in range(cols):
        col = [r[j] for r in x]
        mean = sum(col) / len(col)
        var = sum((v - mean) ** 2 for v in col) / len(col)
        std = math.sqrt(var)
        means.append(mean)
        stds.append(std)
    return means, stds


def _zscore_apply(x: list[list[float]], means: list[float], stds: list[float]) -> list[list[float]]:
    out: list[list[float]] = []
    for row in x:
        out.append([(v - m) / (s if s > 0 else 1.0) for v, m, s in zip(row, means, stds)])
    return out


def _sigmoid(z: float) -> float:
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class FitResult:
    weights: list[float]
    bias: float


def _fit_logistic_l2(x: list[list[float]], y: list[int], l2: float, lr: float, steps: int) -> FitResult:
    d = len(x[0])
    w = [0.0] * d
    b = 0.0
    n = len(x)
    for _ in range(steps):
        grad_w = [0.0] * d
        grad_b = 0.0
        for xi, yi in zip(x, y):
            z = sum(a * b_ for a, b_ in zip(xi, w)) + b
            p = _sigmoid(z)
            err = p - yi
            grad_b += err
            for j in range(d):
                grad_w[j] += err * xi[j]
        grad_b /= n
        for j in range(d):
            grad_w[j] = grad_w[j] / n + l2 * w[j]
            w[j] -= lr * grad_w[j]
        b -= lr * grad_b
    return FitResult(weights=w, bias=b)


def _predict_prob(x: list[list[float]], fit: FitResult) -> list[float]:
    return [_sigmoid(sum(a * b for a, b in zip(row, fit.weights)) + fit.bias) for row in x]


def _safe_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def train_one(
    task: str,
    model_name: str,
    model_dir: Path,
    feature_names: list[str],
    l2: float,
    lr: float,
    steps: int,
) -> dict[str, Any]:
    split_rows = {s: _read_jsonl(model_dir / f"{s}.jsonl") for s in ("train", "val", "test")}
    if not split_rows["train"]:
        raise ValueError("Missing train rows")

    x_raw: dict[str, list[list[float]]] = {}
    y: dict[str, list[int]] = {}
    for split in ("train", "val", "test"):
        rows = split_rows[split]
        x_raw[split] = [_feature_vector(task, str(r.get("prompt", "")), feature_names) for r in rows]
        y[split] = [_label_is_fail(r) for r in rows]

    # Guardrail 1: target collapse.
    if len(set(y["train"])) < 2:
        raise ValueError("Target collapse on train split: failure label has only one class")

    # Guardrail 2: raw feature null/constant/near-zero variance checks.
    eps = 1e-9
    for j, name in enumerate(feature_names):
        col = [row[j] for row in x_raw["train"]]
        if any(v is None for v in col):
            raise ValueError(f"Feature '{name}' contains null values on train")
        vmin = min(col)
        vmax = max(col)
        if abs(vmax - vmin) <= eps:
            raise ValueError(f"Feature '{name}' is constant on train")
        mean = _safe_mean(col)
        var = _safe_mean([(v - mean) ** 2 for v in col])
        if var <= eps:
            raise ValueError(f"Feature '{name}' has near-zero variance on train")

    means, stds = _zscore_fit(x_raw["train"])
    x = {s: _zscore_apply(x_raw[s], means, stds) for s in ("train", "val", "test")}

    # Guardrail 3: post-normalization collapse.
    for j, name in enumerate(feature_names):
        col = [row[j] for row in x["train"]]
        if abs(max(col) - min(col)) <= eps:
            raise ValueError(f"Feature '{name}' collapsed after normalization")

    fit = _fit_logistic_l2(x["train"], y["train"], l2=l2, lr=lr, steps=steps)
    preds = {s: _predict_prob(x[s], fit) for s in ("train", "val", "test")}

    def split_metrics(split: str) -> dict[str, float]:
        p = preds[split]
        yy = y[split]
        pred_bin = [1 if v >= 0.5 else 0 for v in p]
        acc = _safe_mean([1.0 if a == b else 0.0 for a, b in zip(pred_bin, yy)])
        return {
            "n": float(len(yy)),
            "positive_rate": _safe_mean([float(v) for v in yy]),
            "avg_pred_fail_prob": _safe_mean(p),
            "accuracy_at_0p5": acc,
        }

    return {
        "task": task,
        "model": model_name,
        "features": feature_names,
        "normalization": {"mean": means, "std": stds},
        "weights": fit.weights,
        "bias": fit.bias,
        "metrics": {s: split_metrics(s) for s in ("train", "val", "test")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Train SDDF per task/model with explicit no-collapse feature guardrails.")
    parser.add_argument("--splits-root", default="model_runs/clean_deterministic_splits")
    parser.add_argument("--weights-root", default="model_runs/benchmarking/feature_ablation/weights")
    parser.add_argument("--output-dir", default="model_runs/clean_deterministic_splits/sddf_artifacts")
    parser.add_argument("--l2", type=float, default=0.05)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--steps", type=int, default=400)
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    weights_root = Path(args.weights_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {"runs": [], "errors": []}

    for task_dir in sorted([p for p in splits_root.iterdir() if p.is_dir() and (p / "split_query_ids.json").exists()]):
        task = task_dir.name
        weights_file = weights_root / f"{task}__all.json"
        if not weights_file.exists():
            report["errors"].append({"task": task, "model": "*", "error": "Missing feature definition file"})
            continue
        feature_names = list(json.loads(weights_file.read_text(encoding="utf-8")).keys())
        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            model_name = model_dir.name
            try:
                artifact = train_one(
                    task=task,
                    model_name=model_name,
                    model_dir=model_dir,
                    feature_names=feature_names,
                    l2=args.l2,
                    lr=args.lr,
                    steps=args.steps,
                )
                model_out_dir = out_dir / task
                model_out_dir.mkdir(parents=True, exist_ok=True)
                (model_out_dir / f"{model_name}.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
                report["runs"].append({"task": task, "model": model_name, "status": "ok"})
            except Exception as exc:  # guardrail failures should be explicit in report
                report["errors"].append({"task": task, "model": model_name, "error": str(exc)})

    (out_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report: {out_dir / 'training_report.json'}")
    print(f"Successes: {len(report['runs'])}, Errors: {len(report['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
