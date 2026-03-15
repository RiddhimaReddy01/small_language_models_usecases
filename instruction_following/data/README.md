# Data

Place local benchmark datasets or dataset exports here.

Current default behavior:
- the pipeline loads `google/IFEval` from Hugging Face by name
- if that load fails, it falls back to a tiny synthetic in-code sample

Recommended conventions:
- store any checked-in sample data under `data/samples/`
- store larger local-only exports under `data/raw/` or `data/processed/`
- keep generated caches out of git
