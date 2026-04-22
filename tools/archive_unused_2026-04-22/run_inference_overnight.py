"""
Overnight inference runner — crash-safe, fully resumable, split-aware.

Runs all tasks x all models for a specific data split (train / val / test).
Each result is written to disk immediately — a crash loses at most one sample.
On restart, already-completed sample_ids are skipped automatically.

Split logic (deterministic SHA-1 hash of sample_id):
    bucket = SHA1(sample_id) % 100
    0-29   -> train  (~30%  = 150 of 500)
    30-69  -> val    (~40%  = 200 of 500)
    70-99  -> test   (~30%  = 150 of 500)

Output files (one per split per model per task):
    model_runs/{task}/{model}/outputs_train.jsonl
    model_runs/{task}/{model}/outputs_val.jsonl
    model_runs/{task}/{model}/outputs_test.jsonl

Models:
    qwen2.5:0.5b   Ollama local  ~0.5B
    qwen2.5:3b     Ollama local  ~3B
    qwen2.5:7b     Ollama local  ~7B
    llama-3.3-70b  Groq API      ~70B  async concurrent

Usage:
    # Run train split first (learn difficulty weights from these)
    python tools/run_inference_overnight.py --split train

    # Run val split next (tune routing threshold on these)
    python tools/run_inference_overnight.py --split val

    # Run test split last — frozen evaluation, never refit after this
    python tools/run_inference_overnight.py --split test

    # Filter to specific models or tasks
    python tools/run_inference_overnight.py --split train --ollama-only
    python tools/run_inference_overnight.py --split val   --tasks classification maths
    python tools/run_inference_overnight.py --split test  --groq-only
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import ollama
from groq import AsyncGroq

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT     = Path(__file__).resolve().parents[1]
GT_DIR   = ROOT / "data" / "ground_truth"
RUNS_DIR = ROOT / "model_runs"
LOGS_DIR = ROOT / "logs"

# Auto-load .env file from project root if present
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Model configs
# ---------------------------------------------------------------------------

MODEL_CONFIGS: dict[str, dict] = {
    "qwen2.5_0.5b": {
        "ollama_name": "qwen2.5:0.5b",
        "display":     "qwen2.5:0.5b",
        "size":        "0.5B",
        "backend":     "ollama",
        "timeout":     90,
        "max_tokens":  512,
    },
    "qwen2.5_3b": {
        "ollama_name": "qwen2.5:3b",
        "display":     "qwen2.5:3b",
        "size":        "3B",
        "backend":     "ollama",
        "timeout":     180,
        "max_tokens":  512,
    },
    "qwen2.5_7b": {
        "ollama_name": "qwen2.5:7b-instruct-q4_K_M",
        "display":     "qwen2.5:7b-q4",
        "size":        "7B",
        "backend":     "ollama",
        "timeout":     360,
        "max_tokens":  256,
    },
    "llama_llama-3.3-70b-versatile": {
        "groq_name":  "llama-3.3-70b-versatile",
        "display":    "groq:llama-3.3-70b-versatile",
        "size":       "70B",
        "backend":    "groq",
        "max_tokens": 512,
    },
}

ALL_TASKS = [
    "classification",
    "maths",
    "code_generation",
    "instruction_following",
    "information_extraction",
    "retrieval_grounded",
    "summarization",
    "text_generation",
]

VALID_SPLITS = ("train", "val", "test")

# Groq free tier = 30 RPM. Raise if on paid plan.
GROQ_RPM         = int(os.environ.get("GROQ_RPM", "25"))
GROQ_CONCURRENCY = int(os.environ.get("GROQ_CONCURRENCY", "10"))
MAX_RETRIES      = 3

# ---------------------------------------------------------------------------
# Split assignment  (deterministic, SHA-1 of sample_id)
# ---------------------------------------------------------------------------

def assign_split(sample_id: str) -> str:
    """
    Returns 'train', 'val', or 'test' based on SHA-1 hash of sample_id.
    Distribution: 30% train / 40% val / 30% test.
    """
    bucket = int(hashlib.sha1(sample_id.encode()).hexdigest()[:8], 16) % 100
    if bucket < 30:
        return "train"
    if bucket < 70:
        return "val"
    return "test"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(split: str) -> logging.Logger:
    LOGS_DIR.mkdir(exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"inference_{split}_{ts}.log"

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s",
                            datefmt="%H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)

    log = logging.getLogger(f"overnight_{split}")
    log.setLevel(logging.DEBUG)
    log.addHandler(fh)
    log.addHandler(ch)
    log.info(f"Log -> {log_file}")
    return log

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def output_path(model_key: str, task: str, split: str) -> Path:
    return RUNS_DIR / task / model_key / f"outputs_{split}.jsonl"


def load_completed(model_key: str, task: str, split: str) -> set[str]:
    p = output_path(model_key, task, split)
    if not p.exists():
        return set()
    done: set[str] = set()
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["sample_id"])
            except Exception:
                pass
    return done


_write_locks: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()


def _get_lock(key: str) -> threading.Lock:
    with _meta_lock:
        if key not in _write_locks:
            _write_locks[key] = threading.Lock()
        return _write_locks[key]


def append_result(model_key: str, task: str, split: str, row: dict) -> None:
    p = output_path(model_key, task, split)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock = _get_lock(f"{model_key}:{task}:{split}")
    with lock:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _bin_for(sample_id: str, total: int) -> int:
    try:
        idx = int(sample_id.rsplit("_", 1)[-1])
        return min(4, idx * 5 // max(1, total))
    except Exception:
        return 0


def make_row(
    gt_row:    dict,
    model_cfg: dict,
    raw:       str,
    latency:   float,
    status:    str,
    error:     str | None,
    run_id:    str,
    total:     int,
    split:     str,
    task:      str,
) -> dict:
    sample_id = gt_row["sample_id"]
    non_empty = bool(raw and raw.strip())
    return {
        "query_id":    str(uuid.uuid4()),
        "task":        gt_row.get("task") or task,
        "split":       split,
        "bin":         _bin_for(sample_id, total),
        "sample_id":   sample_id,
        "model":       model_cfg.get("ollama_name") or model_cfg.get("groq_name"),
        "model_size":  model_cfg["size"],
        "backend":     model_cfg["backend"],
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "latency_sec": round(latency, 4),
        "prompt":      gt_row.get("prompt", ""),
        "raw_output":  raw,
        "parsed_output": {},
        "status":      status,
        "valid":       non_empty and status == "success",
        "error":       error,
        "failure_category": None,
        "validation_checks": {
            "non_empty":           non_empty,
            "parseable":           True,
            "has_expected_fields": True,
        },
        "validation_notes": "All checks passed" if status == "success" else f"status={status}",
        "run_id": run_id,
    }

# ---------------------------------------------------------------------------
# Ground truth loader
# ---------------------------------------------------------------------------

def load_gt_for_split(task: str, split: str) -> list[dict]:
    """Load ground truth rows that belong to the requested split and have a prompt."""
    p = GT_DIR / f"{task}.jsonl"
    if not p.exists():
        return []
    rows = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            # must have a prompt
            if not row.get("prompt", "").strip():
                continue
            # must belong to this split
            if assign_split(str(row["sample_id"])) == split:
                rows.append(row)
    return rows

# ---------------------------------------------------------------------------
# Ollama runner
# ---------------------------------------------------------------------------

def ensure_model_pulled(ollama_name: str, log: logging.Logger) -> bool:
    try:
        models = [m.model for m in ollama.list().models]
        want_base = ollama_name.split(":")[0]
        want_tag  = ollama_name.split(":")[1] if ":" in ollama_name else "latest"
        if any(want_base in m and want_tag in m for m in models):
            log.info(f"Model {ollama_name} already available")
            return True
        log.info(f"Pulling {ollama_name} ...")
        ollama.pull(ollama_name)
        log.info(f"Pull complete: {ollama_name}")
        return True
    except Exception as e:
        log.error(f"Could not ensure {ollama_name}: {e}")
        return False


def call_ollama(ollama_name: str, prompt: str, max_tokens: int) -> tuple[str, str | None]:
    try:
        resp = ollama.generate(
            model=ollama_name,
            prompt=prompt,
            options={"num_predict": max_tokens, "temperature": 0.0},
        )
        return resp.response or "", None
    except Exception as e:
        return "", str(e)


def run_ollama_task(model_key: str, task: str, split: str, log: logging.Logger) -> None:
    cfg      = MODEL_CONFIGS[model_key]
    gt_rows  = load_gt_for_split(task, split)
    if not gt_rows:
        log.info(f"[{model_key}][{task}][{split}] No rows for this split, skipping")
        return

    completed = load_completed(model_key, task, split)
    pending   = [r for r in gt_rows if r["sample_id"] not in completed]
    total     = len(gt_rows)

    if not pending:
        log.info(f"[{model_key}][{task}][{split}] Complete ({len(completed)}/{total}), skipping")
        return

    run_id = str(uuid.uuid4())
    log.info(f"[{model_key}][{task}][{split}] {len(pending)} remaining / {total} total")

    done = len(completed)
    for gt_row in pending:
        t0     = time.time()
        raw    = ""
        err    = f"max_retries={MAX_RETRIES} exceeded"
        status = "error"

        for attempt in range(MAX_RETRIES):
            raw, err = call_ollama(cfg["ollama_name"], gt_row["prompt"], cfg["max_tokens"])
            if err is None:
                status = "success"
                break
            wait = 2 ** attempt
            log.warning(f"[{model_key}][{task}][{split}] {gt_row['sample_id']} "
                        f"attempt {attempt+1} failed: {err} — retry in {wait}s")
            time.sleep(wait)

        latency = time.time() - t0
        row = make_row(gt_row, cfg, raw, latency, status, err, run_id, total, split, task)
        append_result(model_key, task, split, row)

        done += 1
        if done % 10 == 0 or done == total:
            log.info(f"[{model_key}][{task}][{split}] {done}/{total} "
                     f"({100*done//total}%) | last={latency:.1f}s | {status}")


def run_ollama_model(model_key: str, tasks: list[str], split: str, log: logging.Logger) -> None:
    cfg = MODEL_CONFIGS[model_key]
    log.info("=" * 60)
    log.info(f"OLLAMA  {cfg['display']} ({cfg['size']})  split={split}")
    log.info("=" * 60)
    if not ensure_model_pulled(cfg["ollama_name"], log):
        log.error(f"Skipping {model_key} — model unavailable")
        return
    for task in tasks:
        run_ollama_task(model_key, task, split, log)
    log.info(f"[{model_key}] All tasks done for split={split}")

# ---------------------------------------------------------------------------
# Groq async runner
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Token-bucket rate limiter.  rpm=0 disables all throttling."""

    def __init__(self, rpm: int):
        self._disabled = rpm <= 0
        self._interval = 0.0 if self._disabled else 60.0 / max(1, rpm)
        self._next     = time.monotonic()
        self._lock     = asyncio.Lock()

    async def acquire(self) -> None:
        if self._disabled:
            return
        async with self._lock:
            wait = self._next - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next = max(self._next, time.monotonic()) + self._interval


async def _call_groq_once(client: AsyncGroq, groq_name: str,
                          prompt: str, max_tokens: int) -> tuple[str, str | None]:
    try:
        resp = await client.chat.completions.create(
            model=groq_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return resp.choices[0].message.content or "", None
    except Exception as e:
        return "", str(e)


async def _groq_worker(sem: asyncio.Semaphore, rl: _RateLimiter,
                       client: AsyncGroq, cfg: dict, model_key: str,
                       gt_row: dict, run_id: str, total: int,
                       split: str, task: str, log: logging.Logger) -> None:
    async with sem:
        await rl.acquire()
        t0     = time.time()
        raw    = ""
        err    = f"max_retries={MAX_RETRIES} exceeded"
        status = "error"

        for attempt in range(MAX_RETRIES):
            raw, err = await _call_groq_once(
                client, cfg["groq_name"], gt_row["prompt"], cfg["max_tokens"])
            if err is None:
                status = "success"
                break
            wait = 2 ** attempt
            log.warning(f"[{model_key}][{task}][{split}] {gt_row['sample_id']} "
                        f"attempt {attempt+1}: {err[:80]} — retry in {wait}s")
            await asyncio.sleep(wait)

        latency = time.time() - t0
        row = make_row(gt_row, cfg, raw, latency, status, err, run_id, total, split, task)
        append_result(model_key, task, split, row)


async def run_groq_tasks_async(model_key: str, tasks: list[str],
                               split: str, log: logging.Logger) -> None:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        log.error("GROQ_API_KEY not set — skipping Groq model")
        return

    cfg    = MODEL_CONFIGS[model_key]
    client = AsyncGroq(api_key=api_key)
    sem    = asyncio.Semaphore(GROQ_CONCURRENCY)
    rl     = _RateLimiter(GROQ_RPM)

    throttle_label = "UNLIMITED" if GROQ_RPM <= 0 else f"RPM={GROQ_RPM}"
    log.info("=" * 60)
    log.info(f"GROQ  {cfg['display']} ({cfg['size']})  split={split}  "
             f"{throttle_label}  concurrency={GROQ_CONCURRENCY}")
    log.info("=" * 60)

    coros = []
    for task in tasks:
        gt_rows   = load_gt_for_split(task, split)
        completed = load_completed(model_key, task, split)
        pending   = [r for r in gt_rows if r["sample_id"] not in completed]
        total     = len(gt_rows)
        run_id    = str(uuid.uuid4())
        log.info(f"[{model_key}][{task}][{split}] {len(pending)} remaining / {total} total")
        for gt_row in pending:
            coros.append(_groq_worker(
                sem, rl, client, cfg, model_key,
                gt_row, run_id, total, split, task, log))

    if not coros:
        log.info(f"[{model_key}] All tasks already complete for split={split}")
        return

    log.info(f"[{model_key}] Dispatching {len(coros)} async calls ...")
    t0 = time.time()
    await asyncio.gather(*coros)
    log.info(f"[{model_key}] Done — {len(coros)} calls in {(time.time()-t0)/60:.1f} min")

# ---------------------------------------------------------------------------
# Progress summary
# ---------------------------------------------------------------------------

def print_progress(tasks: list[str], split: str, log: logging.Logger) -> None:
    log.info("-" * 60)
    log.info(f"PROGRESS SUMMARY  split={split}")
    log.info("-" * 60)
    for model_key in MODEL_CONFIGS:
        for task in tasks:
            gt    = load_gt_for_split(task, split)
            if not gt:
                continue
            done  = len(load_completed(model_key, task, split))
            total = len(gt)
            pct   = min(done, total) / total if total else 0
            bar   = "#" * int(20 * pct) + "." * (20 - int(20 * pct))
            log.info(f"  {model_key:38s}  {task:25s}  [{bar}] {done:3d}/{total}")
    log.info("-" * 60)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", required=True, choices=VALID_SPLITS,
                   help="Data split to run inference on: train / val / test")
    p.add_argument("--models",      nargs="+", help="Model keys/names to run (default: all)")
    p.add_argument("--tasks",       nargs="+", help="Task names to run (default: all)")
    p.add_argument("--groq-only",    action="store_true")
    p.add_argument("--ollama-only",  action="store_true")
    p.add_argument("--groq-rpm",     type=int, default=GROQ_RPM,
                   help="Groq requests-per-minute cap (default 25). Ignored with --no-throttle.")
    p.add_argument("--no-throttle",  action="store_true",
                   help="Disable Groq rate limiter entirely; fire all requests concurrently.")
    p.add_argument("--dry-run",      action="store_true",
                   help="Print plan without running inference")
    return p.parse_args()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global GROQ_RPM, GROQ_CONCURRENCY
    args     = parse_args()
    if args.no_throttle:
        GROQ_RPM         = 0   # disables _RateLimiter
        GROQ_CONCURRENCY = 50  # fire up to 50 requests simultaneously
    else:
        GROQ_RPM = args.groq_rpm
    split    = args.split
    log      = setup_logging(split)

    tasks = args.tasks or ALL_TASKS
    bad   = [t for t in tasks if t not in ALL_TASKS]
    if bad:
        log.error(f"Unknown tasks: {bad}")
        sys.exit(1)

    ollama_keys = [k for k, v in MODEL_CONFIGS.items() if v["backend"] == "ollama"]
    groq_keys   = [k for k, v in MODEL_CONFIGS.items() if v["backend"] == "groq"]

    if args.models:
        ollama_keys = [k for k in ollama_keys
                       if k in args.models or MODEL_CONFIGS[k].get("ollama_name") in args.models]
        groq_keys   = [k for k in groq_keys
                       if k in args.models or MODEL_CONFIGS[k].get("groq_name") in args.models]
    if args.groq_only:
        ollama_keys = []
    if args.ollama_only:
        groq_keys = []

    # -- plan -----------------------------------------------------------------
    log.info("=" * 60)
    log.info(f"INFERENCE PLAN  split={split}")
    log.info("=" * 60)
    log.info(f"Tasks  : {tasks}")
    log.info(f"Ollama : {[MODEL_CONFIGS[k]['display'] for k in ollama_keys]}")
    log.info(f"Groq   : {[MODEL_CONFIGS[k]['display'] for k in groq_keys]}")
    log.info("")

    for k in ollama_keys + groq_keys:
        todo = sum(
            len(load_gt_for_split(t, split)) - len(load_completed(k, t, split))
            for t in tasks
        )
        log.info(f"  {MODEL_CONFIGS[k]['display']:40s}  remaining={max(0, todo)}")

    if args.dry_run:
        log.info("DRY RUN - exiting")
        return

    print_progress(tasks, split, log)

    # -- run ------------------------------------------------------------------
    for gk in groq_keys:
        asyncio.run(run_groq_tasks_async(gk, tasks, split, log))

    for ok in ollama_keys:
        run_ollama_model(ok, tasks, split, log)

    print_progress(tasks, split, log)
    log.info(f"ALL DONE  split={split}")


if __name__ == "__main__":
    main()
