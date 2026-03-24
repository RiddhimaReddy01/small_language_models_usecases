from __future__ import annotations

import ast
import random
from typing import Iterable

from datasets import load_dataset

from .types import Task


def _extract_signature_from_code(code: str) -> tuple[str, str]:
    module = ast.parse(code)
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            args = ", ".join(arg.arg for arg in node.args.args)
            signature = f"def {node.name}({args}):\n    pass"
            return node.name, signature
    raise ValueError("Could not infer function signature from reference code.")


def _try_load_dataset(candidates: Iterable[tuple[str, str | None, str | None]]):
    last_error: Exception | None = None
    for path, name, split in candidates:
        try:
            kwargs = {}
            if name is not None:
                kwargs["name"] = name
            dataset = load_dataset(path, **kwargs)
            if split:
                return dataset[split]
            if hasattr(dataset, "keys"):
                first_split = next(iter(dataset.keys()))
                return dataset[first_split]
            return dataset
        except Exception as exc:  # pragma: no cover - depends on environment
            last_error = exc
    raise RuntimeError(f"Failed to load dataset using known identifiers: {last_error}")


def load_humaneval_tasks(limit: int, seed: int) -> list[Task]:
    dataset = _try_load_dataset(
        [
            ("openai_humaneval", None, "test"),
            ("openai/openai_humaneval", None, "test"),
        ]
    )

    rows = list(dataset)
    random.Random(seed).shuffle(rows)
    selected = rows[:limit]

    tasks: list[Task] = []
    for row in selected:
        prompt = row["prompt"].rstrip()
        tasks.append(
            Task(
                task_id=str(row["task_id"]),
                dataset="HumanEval",
                problem_text="Complete the Python function defined in the starter code.",
                entry_point=row["entry_point"],
                starter_code=prompt,
                test_code=row["test"],
                metadata={"canonical_solution": row.get("canonical_solution", "")},
            )
        )
    return tasks


def load_mbpp_tasks(limit: int, seed: int) -> list[Task]:
    dataset = _try_load_dataset(
        [
            ("mbpp", None, "test"),
            ("google-research-datasets/mbpp", None, "test"),
        ]
    )

    rows = list(dataset)
    random.Random(seed).shuffle(rows)
    selected = rows[:limit]

    tasks: list[Task] = []
    for row in selected:
        entry_point, starter_code = _extract_signature_from_code(row["code"])
        setup = row.get("test_setup_code", "")
        tests = "\n".join(row.get("test_list", []))
        test_code = "\n".join(part for part in [setup, tests] if part.strip())
        tasks.append(
            Task(
                task_id=str(row["task_id"]),
                dataset="MBPP",
                problem_text=row["text"],
                entry_point=entry_point,
                starter_code=starter_code,
                test_code=test_code,
                metadata={"reference_code": row["code"]},
            )
        )
    return tasks


def load_task_pool(human_eval_limit: int, mbpp_limit: int, seed: int) -> list[Task]:
    tasks = load_humaneval_tasks(human_eval_limit, seed)
    tasks.extend(load_mbpp_tasks(mbpp_limit, seed + 1))
    return tasks
