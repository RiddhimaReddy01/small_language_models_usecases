# Retrieval-Grounded Benchmark

Clean, reproducible structure for dataset ingestion, experiment runs, and report generation.

## Repository Layout

```
Retrieval_grounded/
├── README.md
├── requirements.txt
├── .gitignore
├── configs/
│   ├── config.yaml
│   ├── config.tiny.yaml
│   └── config.smoke.yaml
├── data/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   └── samples/
├── src/
│   ├── data_loaders.py
│   ├── metrics.py
│   ├── parsers.py
│   ├── prompts.py
│   ├── reporting.py
│   └── runners.py
├── cli/
│   ├── prepare_datasets.py
│   ├── run_experiment.py
│   └── generate_reports.py
├── outputs/
│   ├── predictions/
│   ├── metrics/
│   └── logs/
├── scripts/
└── tests/
```

## Setup

```bash
pip install -r requirements.txt
```

## Typical Workflow

1) Prepare small sample data:

```bash
python cli/prepare_datasets.py
```

2) Run experiment:

```bash
python cli/run_experiment.py --config configs/config.yaml
```

3) Generate report:

```bash
python cli/generate_reports.py
```

## Quick Commands

- Windows: `run.bat` / `run.bat quick`
- Unix/macOS: `./run.sh` / `./run.sh quick`

## Notes

- Keep large raw/processed datasets outside git.
- `outputs/` is ignored except folder placeholders.
- Use `configs/config.smoke.yaml` for fast CI sanity checks.
