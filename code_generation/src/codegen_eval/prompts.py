from __future__ import annotations

import ast

from markdown_it import MarkdownIt
from .types import Task

_MARKDOWN = MarkdownIt("commonmark")


PROMPT_VARIANTS: dict[str, str] = {
    "default": "Write a Python function that solves the following problem.",
    "solve": "Solve this problem in Python.",
    "function": "Write a Python function to solve the problem below.",
    "implement": "Implement the function below in Python.",
    "fast_cpu": "Return only the completed Python function.",
}


def build_prompt(task: Task, variant: str = "default") -> str:
    prefix = PROMPT_VARIANTS.get(variant, PROMPT_VARIANTS["default"])
    if variant == "fast_cpu":
        return (
            f"{prefix}\n\n"
            f"Problem:\n{task.problem_text}\n\n"
            f"Complete this function exactly:\n```python\n{task.starter_code.rstrip()}\n```\n\n"
            "Requirements:\n"
            f"- Use the exact function name `{task.entry_point}`\n"
            "- Preserve the required parameters\n"
            "- Return only Python code\n"
            "- Do not include explanations\n"
        )

    return (
        f"{prefix}\n\n"
        f"Problem:\n{task.problem_text}\n\n"
        f"Starter code:\n```python\n{task.starter_code.rstrip()}\n```\n\n"
        "Requirements:\n"
        "- Return only Python code\n"
        f"- Use the exact function name `{task.entry_point}`\n"
        "- Preserve the required parameters\n"
        "- Do not include explanations\n"
    )


def _parse_markdown(text: str):
    return _MARKDOWN.parse(text)


def _fenced_code_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for token in _parse_markdown(text):
        if token.type != "fence":
            continue
        info = (token.info or "").strip().lower().split()
        if not info or info[0] in {"python", "py"}:
            blocks.append(token.content.strip())
    return blocks


def _partial_fence_code_block(text: str) -> str | None:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return None

    lines = stripped.splitlines()
    if not lines:
        return None

    opening = lines[0].strip()
    language = opening[3:].strip().lower().split()
    if language and language[0] not in {"python", "py"}:
        return None

    body: list[str] = []
    for line in lines[1:]:
        if line.strip().startswith("```"):
            break
        body.append(line)
    return "\n".join(body).strip()


def _is_python_source(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def extract_code(text: str) -> str:
    fenced = _fenced_code_blocks(text)
    if fenced:
        return fenced[0]
    partial_fence = _partial_fence_code_block(text)
    if partial_fence is not None:
        return partial_fence
    return text.strip()


def is_code_only_output(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    fenced_count = 0
    for token in _parse_markdown(text):
        if token.type == "fence":
            fenced_count += 1
            continue
        if token.type == "inline" and token.content.strip():
            return False

    if fenced_count > 0:
        return fenced_count == 1

    if _partial_fence_code_block(text) is not None:
        return True

    return _is_python_source(stripped)
