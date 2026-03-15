Place normalized benchmark datasets in `data/processed/` as JSONL files:

- `gsm8k.jsonl`
- `svamp.jsonl`
- `math_subset.jsonl`

Required schema per line:

```json
{"question": "Problem text", "answer": "42", "difficulty": "easy"}
```

Rules:

- `difficulty` must be one of `easy`, `medium`, `hard`
- files must contain enough examples in each difficulty bucket for stratified sampling
- current sample sizes are defined in `configs/config.yaml`

If you are starting from raw datasets, place them under:

- `data/raw/gsm8k`
- `data/raw/svamp`
- `data/raw/math`

Then run:

```bash
python cli/prepare_datasets.py
```
