from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from math import sqrt

import numpy as np
import pandas as pd
import spacy
import textstat
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


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
CONSTRAINT_KEYWORDS = {"must", "should", "exactly", "only", "at least", "at most", "required", "format", "return"}
RELATION_KEYWORDS = {"from", "to", "by", "with", "in", "on", "for", "between", "belongs", "contains"}
CREATIVITY_KEYWORDS = {"creative", "story", "poem", "imagine", "fiction", "narrative", "style", "tone"}
TOPIC_HINT_KEYWORDS = {"about", "topic", "theme", "subject", "domain"}
DISCOURSE_MARKERS = {"however", "therefore", "moreover", "meanwhile", "thus", "overall", "in conclusion"}
POSITIVE_WORDS = {"good", "great", "excellent", "amazing", "love", "positive", "best", "happy"}
NEGATIVE_WORDS = {"bad", "terrible", "awful", "hate", "negative", "worst", "sad", "angry"}
NEGATIONS = {"no", "not", "never", "none", "nothing", "neither", "nor", "without", "cannot", "can't", "won't"}
MATH_SYMBOLS = set("+-*/=<>^%")
CODE_SYMBOLS = set("+-*/=<>^%(){}[]:;_")


class FeatureExtractorV2:
    def __init__(self, embedding_model: str, disable_embeddings: bool) -> None:
        self.nlp = self._load_spacy()
        self.embedding_model_name = embedding_model
        self.embeddings_enabled = not disable_embeddings
        self._embedder: SentenceTransformer | None = None
        self._emb_cache: dict[str, np.ndarray] = {}

    def _load_spacy(self):
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
            return nlp

    def _ensure_embedder(self) -> bool:
        if not self.embeddings_enabled:
            return False
        if self._embedder is not None:
            return True
        try:
            self._embedder = SentenceTransformer(self.embedding_model_name)
            return True
        except Exception:
            self.embeddings_enabled = False
            return False

    def _embed(self, text: str) -> np.ndarray | None:
        if not self._ensure_embedder():
            return None
        key = text.strip()
        if key in self._emb_cache:
            return self._emb_cache[key]
        vec = self._embedder.encode([key], normalize_embeddings=True, convert_to_numpy=True)[0]
        self._emb_cache[key] = vec
        return vec

    def _cosine(self, a: str, b: str) -> float:
        va = self._embed(a)
        vb = self._embed(b)
        if va is None or vb is None:
            return 0.0
        return float(np.dot(va, vb))

    def _split_context_query(self, prompt: str, task: str) -> tuple[str, str]:
        def _fallback_segments(text: str) -> tuple[str, str]:
            doc_local = self.nlp(text)
            sents_local = [s.text.strip() for s in doc_local.sents if s.text.strip()]
            if len(sents_local) >= 2:
                context_local = " ".join(sents_local[:-1]).strip()
                query_local = sents_local[-1].strip()
                if context_local and query_local:
                    return context_local, query_local
            toks_local = [t.text for t in doc_local if not t.is_space]
            if len(toks_local) >= 8:
                split_at_local = max(1, int(len(toks_local) * 0.7))
                context_local = " ".join(toks_local[:split_at_local]).strip()
                query_local = " ".join(toks_local[split_at_local:]).strip()
                if context_local and query_local:
                    return context_local, query_local
            return text, ""

        lower = prompt.lower()
        query_markers = ["question:", "query:", "instruction:", "task:"]
        if task == "summarization":
            query_markers = ["summary:", "summarize", "write a summary"]
        idx = -1
        for marker in query_markers:
            j = lower.find(marker)
            if j != -1 and (idx == -1 or j < idx):
                idx = j
        if idx == -1:
            return _fallback_segments(prompt)
        context = prompt[:idx].strip()
        query = prompt[idx:].strip()
        if not context or not query:
            return _fallback_segments(prompt)
        return context, query

    def _token_strings(self, doc) -> list[str]:
        out: list[str] = []
        for t in doc:
            if t.is_space:
                continue
            out.append(t.text.lower())
        return out

    def _safe_readability(self, fn_name: str, text: str) -> float:
        try:
            fn = getattr(textstat, fn_name)
            return float(fn(text))
        except Exception:
            return 0.0

    def _bm25_scores(self, context: str, query: str) -> tuple[float, float]:
        if not context or not query:
            return 0.0, 0.0
        cdoc = self.nlp(context)
        qdoc = self.nlp(query)
        corpus = []
        for sent in cdoc.sents:
            toks = [t.text.lower() for t in sent if (not t.is_space and not t.is_punct)]
            if toks:
                corpus.append(toks)
        if not corpus:
            return 0.0, 0.0
        query_tokens = [t.text.lower() for t in qdoc if (not t.is_space and not t.is_punct)]
        if not query_tokens:
            return 0.0, 0.0
        bm = BM25Okapi(corpus)
        scores = bm.get_scores(query_tokens)
        if scores.size == 0:
            return 0.0, 0.0
        return float(np.max(scores)), float(np.mean(scores))

    def _overlap_ratio(self, a_tokens: list[str], b_tokens: list[str]) -> float:
        aset = set(a_tokens)
        bset = set(b_tokens)
        if not aset or not bset:
            return 0.0
        inter = len(aset.intersection(bset))
        return float(inter / max(1, len(aset)))

    def extract(self, task: str, prompt: str) -> dict[str, float]:
        doc = self.nlp(prompt)
        toks = [t for t in doc if not t.is_space]
        words = [t for t in toks if t.is_alpha]
        tokens_lower = [t.text.lower() for t in toks]
        word_lower = [t.text.lower() for t in words]
        n_tokens = len(toks)
        n_words = len(words)
        sents = list(doc.sents) if doc.has_annotation("SENT_START") else [doc]
        n_sents = max(1, len(sents))

        context_text, query_text = self._split_context_query(prompt, task=task)
        context_doc = self.nlp(context_text) if context_text else None
        query_doc = self.nlp(query_text) if query_text else doc
        context_tokens = self._token_strings(context_doc) if context_doc is not None else []
        query_tokens = self._token_strings(query_doc)

        pos_counts = {"NOUN": 0, "VERB": 0, "ADJ": 0, "ADV": 0}
        dep_depth = []
        imperative_roots = 0
        for sent in sents:
            root = sent.root if hasattr(sent, "root") else None
            if root is not None and root.pos_ == "VERB":
                imperative_roots += 1
            for t in sent:
                if t.pos_ in pos_counts:
                    pos_counts[t.pos_] += 1
                if hasattr(t, "ancestors"):
                    dep_depth.append(len(list(t.ancestors)))

        entity_count = len(doc.ents)
        entity_type_count = len(set(ent.label_ for ent in doc.ents))

        avg_word_length = float(np.mean([len(w.text) for w in words])) if words else 0.0
        avg_sentence_length = float(n_tokens / n_sents)
        type_token_ratio = float(len(set(word_lower)) / max(1, n_words))

        stopword_ratio = float(sum(1 for t in words if t.is_stop) / max(1, n_words))
        noun_ratio = float(pos_counts["NOUN"] / max(1, n_words))
        verb_ratio = float(pos_counts["VERB"] / max(1, n_words))
        adj_ratio = float(pos_counts["ADJ"] / max(1, n_words))
        dep_tree_depth_mean = float(np.mean(dep_depth)) if dep_depth else 0.0

        negation_count = float(sum(1 for t in tokens_lower if t in NEGATIONS))
        modal_verb_ratio = float(sum(1 for t in tokens_lower if t in {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}) / max(1, n_words))
        format_keyword_density = float(sum(1 for t in tokens_lower if t in FORMAT_KEYWORDS) / max(1, n_words))
        algorithm_keyword_density = float(sum(1 for t in tokens_lower if t in ALGO_KEYWORDS) / max(1, n_words))
        relation_keyword_density = float(sum(1 for t in tokens_lower if t in RELATION_KEYWORDS) / max(1, n_words))
        creativity_keyword_density = float(sum(1 for t in tokens_lower if t in CREATIVITY_KEYWORDS) / max(1, n_words))
        topic_keyword_density = float(sum(1 for t in tokens_lower if t in TOPIC_HINT_KEYWORDS) / max(1, n_words))
        discourse_marker_density = float(sum(1 for t in tokens_lower if t in DISCOURSE_MARKERS) / max(1, n_words))

        constraint_hits = 0
        lower_prompt = prompt.lower()
        for k in CONSTRAINT_KEYWORDS:
            if k in lower_prompt:
                constraint_hits += 1
        constraint_keyword_density = float(constraint_hits / max(1, n_words))

        sentiment_score = float(
            sum(1 for t in tokens_lower if t in POSITIVE_WORDS) - sum(1 for t in tokens_lower if t in NEGATIVE_WORDS)
        ) / max(1, n_words)

        digit_ratio = float(sum(1 for ch in prompt if ch.isdigit()) / max(1, len(prompt)))
        math_symbol_density = float(sum(1 for ch in prompt if ch in MATH_SYMBOLS) / max(1, len(prompt)))
        code_symbol_density = float(sum(1 for ch in prompt if ch in CODE_SYMBOLS) / max(1, len(prompt)))
        equation_marker_density = float((prompt.count("=") + prompt.count("==")) / max(1, len(prompt)))
        quantity_mention_density = float(sum(1 for t in tokens_lower if any(ch.isdigit() for ch in t)) / max(1, n_words))
        slot_marker_density = float((prompt.count(":") + prompt.count("->")) / max(1, len(prompt)))
        list_marker_density = float((prompt.count("- ") + prompt.count("* ")) / max(1, n_sents))
        step_marker_density = float((lower_prompt.count("step ") + lower_prompt.count("first") + lower_prompt.count("then")) / max(1, n_sents))
        question_mark_density = float(prompt.count("?") / max(1, n_sents))
        citation_marker_density = float((prompt.count("[") + prompt.count("]") + lower_prompt.count("source")) / max(1, n_sents))
        summary_instruction_density = float((lower_prompt.count("summarize") + lower_prompt.count("summary")) / max(1, n_sents))

        context_token_count = float(len(context_tokens))
        query_token_count = float(len(query_tokens))
        source_token_count = float(len(context_tokens) if task == "summarization" and context_tokens else n_tokens)
        compression_ratio_proxy = float(query_token_count / max(1.0, source_token_count))
        context_query_overlap_ratio = self._overlap_ratio(query_tokens, context_tokens)
        bm25_max, bm25_mean = self._bm25_scores(context=context_text, query=query_text)
        emb_cos = self._cosine(query_text, context_text) if context_text else 0.0

        return {
            "token_count": float(n_tokens),
            "type_token_ratio": type_token_ratio,
            "avg_word_length": avg_word_length,
            "sentence_count": float(n_sents),
            "avg_sentence_length": avg_sentence_length,
            "flesch_reading_ease": self._safe_readability("flesch_reading_ease", prompt),
            "flesch_kincaid_grade": self._safe_readability("flesch_kincaid_grade", prompt),
            "gunning_fog": self._safe_readability("gunning_fog", prompt),
            "smog_index": self._safe_readability("smog_index", prompt),
            "stopword_ratio": stopword_ratio,
            "noun_ratio": noun_ratio,
            "verb_ratio": verb_ratio,
            "adj_ratio": adj_ratio,
            "dep_tree_depth_mean": dep_tree_depth_mean,
            "entity_count": float(entity_count),
            "entity_type_count": float(entity_type_count),
            "entity_density": float(entity_count / max(1, n_words)),
            "negation_count": negation_count,
            "sentiment_lexicon_score": sentiment_score,
            "modal_verb_ratio": modal_verb_ratio,
            "format_keyword_density": format_keyword_density,
            "algorithm_keyword_density": algorithm_keyword_density,
            "constraint_keyword_density": constraint_keyword_density,
            "relation_keyword_density": relation_keyword_density,
            "creativity_keyword_density": creativity_keyword_density,
            "topic_keyword_density": topic_keyword_density,
            "discourse_marker_density": discourse_marker_density,
            "digit_ratio": digit_ratio,
            "math_symbol_density": math_symbol_density,
            "code_symbol_density": code_symbol_density,
            "equation_marker_density": equation_marker_density,
            "quantity_mention_density": quantity_mention_density,
            "slot_marker_density": slot_marker_density,
            "list_marker_density": list_marker_density,
            "step_marker_density": step_marker_density,
            "imperative_root_ratio": float(imperative_roots / max(1, n_sents)),
            "question_mark_density": question_mark_density,
            "citation_marker_density": citation_marker_density,
            "summary_instruction_density": summary_instruction_density,
            "context_token_count": context_token_count,
            "query_token_count": query_token_count,
            "source_token_count": source_token_count,
            "compression_ratio_proxy": compression_ratio_proxy,
            "context_query_overlap_ratio": context_query_overlap_ratio,
            "bm25_query_context_max": bm25_max,
            "bm25_query_context_mean": bm25_mean,
            "embedding_query_context_cosine": emb_cos,
        }


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


def _label_fail(row: dict[str, Any]) -> int:
    if "sddf_label" in row:
        return int(bool(row["sddf_label"]))
    status = str(row.get("status", "")).lower()
    valid = bool(row.get("valid", False))
    failure_category = row.get("failure_category")
    error = row.get("error")
    fail = (status != "success") or (not valid) or (failure_category not in (None, "", "none")) or (error not in (None, ""))
    return int(fail)


def _build_frame(task: str, rows: list[dict[str, Any]], feature_names: list[str], extractor: FeatureExtractorV2) -> pd.DataFrame:
    out = []
    for row in rows:
        prompt = str(row.get("prompt", ""))
        feat = extractor.extract(task=task, prompt=prompt)
        selected = {k: float(feat.get(k, 0.0)) for k in feature_names}
        selected["y"] = _label_fail(row)
        out.append(selected)
    return pd.DataFrame(out)


def _sanitize_features(
    x_train: pd.DataFrame,
    x_val: pd.DataFrame,
    feature_names: list[str],
    variance_threshold: float,
    corr_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, list[str]]]:
    # Governance: feature selection decisions are made from TRAIN only.
    dropped_null = [c for c in feature_names if x_train[c].isnull().any()]
    keep_1 = [c for c in feature_names if c not in dropped_null]
    if not keep_1:
        raise ValueError("All features dropped due to null values")

    vt = VarianceThreshold(threshold=variance_threshold)
    vt.fit(x_train[keep_1])
    keep_mask = vt.get_support()
    keep_2 = [f for i, f in enumerate(keep_1) if bool(keep_mask[i])]
    dropped_low_var = [f for f in keep_1 if f not in keep_2]
    if not keep_2:
        raise ValueError("All features dropped due to low variance")

    corr = x_train[keep_2].corr().abs().fillna(0.0)
    dropped_corr: list[str] = []
    keep_3: list[str] = []
    for col in keep_2:
        should_drop = False
        for prev in keep_3:
            if float(corr.loc[col, prev]) > corr_threshold:
                should_drop = True
                break
        if should_drop:
            dropped_corr.append(col)
        else:
            keep_3.append(col)
    if not keep_3:
        raise ValueError("All features dropped after correlation pruning")

    return (
        x_train[keep_3].copy(),
        x_val[keep_3].copy(),
        keep_3,
        {
            "null_or_nonfinite_train_only": dropped_null,
            "low_variance_train_only": dropped_low_var,
            "high_correlation_train_only": dropped_corr,
        },
    )


def _calibrate_threshold(y_val: np.ndarray, p_val: np.ndarray) -> float:
    best_t = 0.5
    best_f1 = -1.0
    for t in np.linspace(0.05, 0.95, 19):
        pred = (p_val >= t).astype(int)
        f1 = f1_score(y_val, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t


def _safe_auc(y_true: np.ndarray, p: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, p))


def _safe_pr_auc(y_true: np.ndarray, p: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(average_precision_score(y_true, p))


def _ece(y_true: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = float(len(y_true))
    if total <= 0:
        return 0.0
    e = 0.0
    for i in range(bins):
        lo = edges[i]
        hi = edges[i + 1]
        if i < bins - 1:
            mask = (p >= lo) & (p < hi)
        else:
            mask = (p >= lo) & (p <= hi)
        count = int(np.sum(mask))
        if count == 0:
            continue
        conf = float(np.mean(p[mask]))
        acc = float(np.mean(y_true[mask]))
        e += (count / total) * abs(acc - conf)
    return float(e)


def _split_metrics(y_true: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, Any]:
    pred = (p >= threshold).astype(int)
    return {
        "n": float(len(y_true)),
        "positive_rate": float(np.mean(y_true)),
        "avg_pred_fail_prob": float(np.mean(p)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "accuracy": float(np.mean(pred == y_true)),
        "roc_auc": _safe_auc(y_true, p),
        "pr_auc": _safe_pr_auc(y_true, p),
        "brier": float(brier_score_loss(y_true, p)),
        "ece_10bin": _ece(y_true, p, bins=10),
    }


def train_task_model(
    task: str,
    model: str,
    model_dir: Path,
    feature_names: list[str],
    extractor: FeatureExtractorV2,
    class_weight: str,
    seed: int,
    variance_threshold: float,
    corr_threshold: float,
) -> dict[str, Any]:
    train_rows = _read_jsonl(model_dir / "train.jsonl")
    val_rows = _read_jsonl(model_dir / "val.jsonl")
    if not train_rows or not val_rows:
        raise ValueError("Missing one or more split files (train/val)")

    df_train = _build_frame(task, train_rows, feature_names, extractor)
    df_val = _build_frame(task, val_rows, feature_names, extractor)

    x_train = df_train[feature_names].copy()
    x_val = df_val[feature_names].copy()
    y_train = df_train["y"].astype(int).to_numpy()
    y_val = df_val["y"].astype(int).to_numpy()

    if len(np.unique(y_train)) < 2:
        raise ValueError("Target collapse on train: only one class present")

    x_train, x_val, selected_features, dropped = _sanitize_features(
        x_train=x_train,
        x_val=x_val,
        feature_names=feature_names,
        variance_threshold=variance_threshold,
        corr_threshold=corr_threshold,
    )

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_val_s = scaler.transform(x_val)

    post_const = [selected_features[i] for i in range(len(selected_features)) if float(np.ptp(x_train_s[:, i])) <= 1e-12]
    if post_const:
        raise ValueError(f"Features collapsed after scaling: {post_const}")

    clf = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="liblinear",
        class_weight=(class_weight if class_weight != "none" else None),
        max_iter=1000,
        random_state=seed,
    )
    clf.fit(x_train_s, y_train)

    abs_w = np.abs(clf.coef_[0])
    if float(abs_w.max()) <= 1e-10:
        raise ValueError("Model weight collapse: all coefficients are effectively zero")

    p_train = clf.predict_proba(x_train_s)[:, 1]
    p_val = clf.predict_proba(x_val_s)[:, 1]
    tau = _calibrate_threshold(y_val=y_val, p_val=p_val)

    return {
        "task": task,
        "model": model,
        "seed": int(seed),
        "features": selected_features,
        "feature_selection": {
            "initial_count": len(feature_names),
            "final_count": len(selected_features),
            "dropped": dropped,
        },
        "tau": tau,
        "class_weight": class_weight,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "weights": clf.coef_[0].tolist(),
        "bias": float(clf.intercept_[0]),
        "metrics": {
            "train": _split_metrics(y_train, p_train, tau),
            "val": _split_metrics(y_val, p_val, tau),
        },
    }


def _run_one_job(
    task: str,
    model: str,
    model_dir_str: str,
    feature_names: list[str],
    class_weight: str,
    embedding_model: str,
    disable_embeddings: bool,
    seed: int,
    variance_threshold: float,
    corr_threshold: float,
) -> dict[str, Any]:
    model_dir = Path(model_dir_str)
    extractor = FeatureExtractorV2(embedding_model=embedding_model, disable_embeddings=disable_embeddings)
    artifact = train_task_model(
        task=task,
        model=model,
        model_dir=model_dir,
        feature_names=feature_names,
        extractor=extractor,
        class_weight=class_weight,
        seed=seed,
        variance_threshold=variance_threshold,
        corr_threshold=corr_threshold,
    )
    return artifact


def _ci95(values: list[float]) -> dict[str, float]:
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": float("nan"), "ci95": float("nan")}
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    if n == 1:
        return {"n": 1, "mean": mean, "ci95": 0.0}
    std = float(np.std(arr, ddof=1))
    ci = 1.96 * std / sqrt(n)
    return {"n": n, "mean": mean, "ci95": float(ci)}


def _load_feature_schema(feature_schema_path: Path, task: str) -> list[str]:
    schema = json.loads(feature_schema_path.read_text(encoding="utf-8"))
    if task not in schema:
        raise ValueError(f"Missing task in feature schema: {task}")
    features = schema[task]
    if not isinstance(features, list) or not features:
        raise ValueError(f"Invalid features list for task: {task}")
    return [str(f) for f in features]


def main() -> int:
    parser = argparse.ArgumentParser(description="SDDF train pipeline v3 with robust feature filtering, calibration metrics, and seed aggregation.")
    parser.add_argument("--splits-root", default="model_runs/sddf_training_splits_slm_only")
    parser.add_argument("--feature-schema-path", default="framework/benchmarking/sddf_feature_schema_v2.json")
    parser.add_argument("--output-dir", default="model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v2")
    parser.add_argument("--class-weight", default="balanced", choices=["balanced", "none"])
    parser.add_argument("--exclude-model-substrings", default="llama-3.3-70b-versatile")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--disable-embeddings", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seeds", default="42", help="Comma-separated random seeds, e.g. 42,43,44,45,46")
    parser.add_argument("--variance-threshold", type=float, default=1e-12)
    parser.add_argument("--corr-threshold", type=float, default=0.95)
    parser.add_argument("--overwrite-existing", action="store_true", help="Recompute artifacts even if output JSON already exists.")
    args = parser.parse_args()

    splits_root = Path(args.splits_root).resolve()
    feature_schema_path = Path(args.feature_schema_path).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    exclude_model_substrings = [s.strip() for s in str(args.exclude_model_substrings).split(",") if s.strip()]

    seed_values = [int(s.strip()) for s in str(args.seeds).split(",") if s.strip()]
    if not seed_values:
        raise ValueError("No valid seeds provided")

    report: dict[str, Any] = {
        "version": "v3",
        "runs": [],
        "errors": [],
        "skipped_existing": [],
        "feature_schema_path": str(feature_schema_path),
        "seeds": seed_values,
    }
    task_dirs = sorted([p for p in splits_root.iterdir() if p.is_dir() and (p / "split_query_ids.json").exists()])
    jobs: list[dict[str, Any]] = []
    for task_dir in task_dirs:
        task = task_dir.name
        try:
            feature_names = _load_feature_schema(feature_schema_path, task=task)
        except Exception as exc:
            report["errors"].append({"task": task, "model": "*", "error": str(exc)})
            continue
        for model_dir in sorted([p for p in task_dir.iterdir() if p.is_dir()]):
            if any(substr and substr in model_dir.name for substr in exclude_model_substrings):
                continue
            for seed in seed_values:
                artifact_path = out_dir / task / f"{model_dir.name}__seed{seed}.json"
                if artifact_path.exists() and not bool(args.overwrite_existing):
                    report["skipped_existing"].append(
                        {
                            "task": task,
                            "model": model_dir.name,
                            "seed": seed,
                            "artifact": str(artifact_path),
                        }
                    )
                    continue
                jobs.append(
                    {
                        "task": task,
                        "model": model_dir.name,
                        "model_dir": str(model_dir),
                        "feature_names": feature_names,
                        "seed": seed,
                    }
                )

    if args.jobs <= 1:
        extractor = FeatureExtractorV2(embedding_model=args.embedding_model, disable_embeddings=bool(args.disable_embeddings))
        for job in jobs:
            try:
                artifact = train_task_model(
                    task=job["task"],
                    model=job["model"],
                    model_dir=Path(job["model_dir"]),
                    feature_names=job["feature_names"],
                    extractor=extractor,
                    class_weight=args.class_weight,
                    seed=job["seed"],
                    variance_threshold=args.variance_threshold,
                    corr_threshold=args.corr_threshold,
                )
                task_out = out_dir / job["task"]
                task_out.mkdir(parents=True, exist_ok=True)
                artifact_path = task_out / f"{job['model']}__seed{job['seed']}.json"
                artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
                report["runs"].append({"task": job["task"], "model": job["model"], "seed": job["seed"], "artifact": str(artifact_path)})
            except Exception as exc:
                report["errors"].append({"task": job["task"], "model": job["model"], "seed": job["seed"], "error": str(exc)})
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            fut_to_job = {
                ex.submit(
                    _run_one_job,
                    job["task"],
                    job["model"],
                    job["model_dir"],
                    job["feature_names"],
                    args.class_weight,
                    args.embedding_model,
                    bool(args.disable_embeddings),
                    int(job["seed"]),
                    float(args.variance_threshold),
                    float(args.corr_threshold),
                ): job
                for job in jobs
            }
            for fut in as_completed(fut_to_job):
                job = fut_to_job[fut]
                try:
                    artifact = fut.result()
                    task_out = out_dir / job["task"]
                    task_out.mkdir(parents=True, exist_ok=True)
                    artifact_path = task_out / f"{job['model']}__seed{job['seed']}.json"
                    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
                    report["runs"].append({"task": job["task"], "model": job["model"], "seed": job["seed"], "artifact": str(artifact_path)})
                except Exception as exc:
                    report["errors"].append({"task": job["task"], "model": job["model"], "seed": job["seed"], "error": str(exc)})

    seed_aggregates: dict[tuple[str, str], dict[str, list[float]]] = {}
    for run in report["runs"]:
        artifact_path = Path(run["artifact"])
        try:
            art = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        key = (str(run["task"]), str(run["model"]))
        if key not in seed_aggregates:
            seed_aggregates[key] = {
                "train_f1": [],
                "val_f1": [],
                "val_roc_auc": [],
                "val_pr_auc": [],
                "val_brier": [],
                "val_ece_10bin": [],
            }
        m = art.get("metrics", {})
        tr = m.get("train", {})
        v = m.get("val", {})
        if isinstance(tr.get("f1"), (int, float)):
            seed_aggregates[key]["train_f1"].append(float(tr["f1"]))
        if isinstance(v.get("f1"), (int, float)):
            seed_aggregates[key]["val_f1"].append(float(v["f1"]))
        if isinstance(v.get("roc_auc"), (int, float)):
            seed_aggregates[key]["val_roc_auc"].append(float(v["roc_auc"]))
        if isinstance(v.get("pr_auc"), (int, float)):
            seed_aggregates[key]["val_pr_auc"].append(float(v["pr_auc"]))
        if isinstance(v.get("brier"), (int, float)):
            seed_aggregates[key]["val_brier"].append(float(v["brier"]))
        if isinstance(v.get("ece_10bin"), (int, float)):
            seed_aggregates[key]["val_ece_10bin"].append(float(v["ece_10bin"]))

    report["seed_aggregates"] = []
    for (task, model), metrics_dict in sorted(seed_aggregates.items()):
        agg = {"task": task, "model": model}
        for metric_name, values in metrics_dict.items():
            agg[metric_name] = _ci95(values)
        report["seed_aggregates"].append(agg)

    report_path = out_dir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote: {report_path}")
    print(f"Successes={len(report['runs'])} Errors={len(report['errors'])} SkippedExisting={len(report['skipped_existing'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
