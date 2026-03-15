import re
from typing import Optional
try:
    from sympy import sympify, simplify, N
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+?)(?:\n|$)", re.IGNORECASE | re.DOTALL)
NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:\s*/\s*[-+]?\d[\d,]*)?(?:[eE][-+]?\d+)?%?")
LETTER_RE = re.compile(r"\b([A-E])\b", re.IGNORECASE)
LATEX_FRACTION_RE = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")


def _clean_candidate(value: str) -> str:
    cleaned = value.strip()
    cleaned = LATEX_FRACTION_RE.sub(r"\1/\2", cleaned)
    cleaned = cleaned.replace("\\%", "%")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^[=:,\-\s]+", "", cleaned)
    return cleaned.strip()


def extract_final_answer(text: str) -> Optional[str]:
    if not text:
        return None

    boxed = BOXED_RE.findall(text)
    if boxed:
        return _clean_candidate(boxed[-1])

    match = FINAL_ANSWER_RE.search(text)
    if match:
        candidate = _clean_candidate(match.group(1))
        if candidate:
            first_line = candidate.splitlines()[0].strip()

            latex_fraction = LATEX_FRACTION_RE.search(first_line)
            if latex_fraction:
                return f"{latex_fraction.group(1).strip()}/{latex_fraction.group(2).strip()}"

            num_match = NUMBER_RE.search(first_line)
            if num_match:
                return _clean_candidate(num_match.group(0))

            # Fall back to a concise answer fragment when the final line includes prose.
            compact = re.split(r"[.;]|(?:\b(?:because|since|therefore|thus)\b)", first_line, maxsplit=1, flags=re.IGNORECASE)[0]
            compact = _clean_candidate(compact)
            if compact:
                return compact

    numbers = NUMBER_RE.findall(text)
    if numbers:
        return _clean_candidate(numbers[-1])

    letter = LETTER_RE.findall(text)
    if letter:
        return letter[-1].upper()

    stripped = text.strip()
    return stripped or None


def normalize_and_compare(predicted: str, gold: str) -> bool:
    """
    Compare answers using symbolic evaluation (SymPy).
    Handles fractions, decimals, expressions, etc.
    Falls back to string matching if SymPy unavailable.
    """
    if not HAS_SYMPY:
        return predicted.strip() == gold.strip()

    try:
        # Try symbolic evaluation
        pred_sym = sympify(predicted, rational=True)
        gold_sym = sympify(gold, rational=True)

        # Check if symbolically equal
        diff = simplify(pred_sym - gold_sym)
        return diff == 0
    except:
        # Fallback to string matching
        return predicted.strip() == gold.strip()
