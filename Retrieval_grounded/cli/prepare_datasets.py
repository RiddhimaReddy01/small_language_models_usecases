"""Prepares local sample datasets for quick ingestion tests."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loaders import sample_dataset


def main() -> None:
    examples = sample_dataset(n_questions=5, max_context_tokens=150, max_answer_tokens=12)
    out_path = Path("data/samples/squad_sample.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([ex.__dict__ for ex in examples], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote sample dataset to {out_path}")


if __name__ == "__main__":
    main()
