from __future__ import annotations

import ast

from .types import SafetyReport


def _attribute_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _attribute_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def scan_code_safety(code: str, blocked_imports: list[str], blocked_calls: list[str]) -> SafetyReport:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return SafetyReport(is_safe=True, reasons=[])

    reasons: list[str] = []
    blocked_import_roots = {item.split(".")[0] for item in blocked_imports}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in blocked_import_roots:
                    reasons.append(f"blocked import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in blocked_import_roots:
                reasons.append(f"blocked import: {node.module}")
        elif isinstance(node, ast.Call):
            name = _attribute_name(node.func)
            if name in blocked_calls:
                reasons.append(f"blocked call: {name}")

    return SafetyReport(is_safe=not reasons, reasons=sorted(set(reasons)))
