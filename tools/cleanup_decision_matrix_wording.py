from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> tuple[str, str]:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Could not decode {path}")


def _write_text(path: Path, text: str, encoding: str) -> None:
    path.write_text(text, encoding=encoding)


def _cleanup_docs(text: str) -> str:
    replacements = {
        "The goal is to show how the learned difficulty signals, capability/risk curves, and t thresholds flow into the decision matrix and Pareto analysis that power routing.": (
            "The goal is to show how the learned difficulty signals, capability/risk curves, "
            "and t thresholds flow into the primary routing matrix: model size vs risk first, "
            "then model size vs capability."
        ),
        "The learned taus (stored in each `AnalysisResult`) identify the **zone of capability** (highest difficulty where capability remains trustworthy) and the **zone of risk** (first difficulty where risk spikes), matching the physical intuition of the two-tier decision matrix.": (
            "The learned taus (stored in each `AnalysisResult`) define the two routing boundaries: "
            "the highest difficulty that remains risk-eligible (`tau_risk`) and the highest "
            "difficulty that remains capability-eligible (`tau_cap`)."
        ),
        "## 4. Decision matrix (parameter count vs risk / capability)": (
            "## 4. Decision matrix (parameter count vs risk, then parameter count vs capability)"
        ),
        "  2. **Capability tier**: from the risk-eligible set, pick the smallest model with \\(E[\\text{cap}] \\ge \\tau_\\cap\\). Even if risk is acceptable, failing the capability tier forces a fallback to the next model or the LLM, producing the Q1–Q4 quadrant assignments in `ProductionRouter.route`.": (
            "  2. **Capability tier**: from the risk-eligible set, pick the smallest model with "
            "\\(E[\\text{cap}] \\ge \\tau_\\cap\\). Even if risk is acceptable, failing the "
            "capability tier forces a fallback to the next model or the LLM."
        ),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _cleanup_report_text(text: str) -> str:
    replacements = {
        "Deployment Zones": "Size-First Decision Matrix",
        "Inferred deployment stance": "Inferred size-first decision matrix",
        "Suggested routing policy": "Two-Stage Routing Policy",
        "## Routing Policy": "## Two-Stage Routing Policy",
        "### Routing Policy": "### Two-Stage Routing Policy",
        "Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.": (
            "Caveat: this decision matrix is benchmark-level and should be revalidated after reruns."
        ),
        "Likely SDDF stance:": "Likely matrix outcome:",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"- Bin `([^`]+)` at difficulty `([^`]+)` -> Zone `([^`]+)`",
        r"- Bin `\1` at difficulty `\2` contributes to the tau-based threshold evidence.",
        text,
    )
    text = re.sub(
        r"<li>Bin <code>([^<]+)</code> at difficulty <code>([^<]+)</code> -&gt; Zone <code>([^<]+)</code></li>",
        r"<li>Bin <code>\1</code> at difficulty <code>\2</code> contributes to the tau-based threshold evidence.</li>",
        text,
    )
    text = text.replace(
        "Suggested `SLM_WITH_GATE` threshold",
        "Legacy gated threshold retained for traceability",
    )
    text = text.replace(
        "Suggested `SLM` threshold",
        "Route to `SLM` while both `tau_risk` and `tau_cap` are satisfied",
    )
    text = text.replace(
        "Suggested `LLM` threshold",
        "Escalate to `LLM` once either `tau_risk` or `tau_cap` fails",
    )
    return text


def main() -> int:
    updated = 0

    docs_path = REPO_ROOT / "docs" / "SDDF_PIPELINE.md"
    if docs_path.exists():
        text, encoding = _read_text(docs_path)
        cleaned = _cleanup_docs(text)
        if cleaned != text:
            _write_text(docs_path, cleaned, encoding)
            updated += 1

    report_patterns = [
        "tasks/**/reports/*.md",
        "tasks/**/reports/*.html",
    ]
    for pattern in report_patterns:
        for path in REPO_ROOT.glob(pattern):
            text, encoding = _read_text(path)
            cleaned = _cleanup_report_text(text)
            if cleaned != text:
                _write_text(path, cleaned, encoding)
                updated += 1

    print(f"Updated {updated} docs/report files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
