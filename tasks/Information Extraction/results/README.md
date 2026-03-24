# Final Results

This directory stores stable benchmark artifacts that are ready to share, commit, and compare.

The current saved final tables were exported from the best working runs we completed in this workspace. Those source runs are traceable in `final_sources.json`.

For future comparisons, prefer rerunning the shared config `configs/sroie_cpu_working_models.json` so all working models are evaluated on the same sampled subset.

Recommended workflow:

1. Ingest or download the dataset into `data/processed/`
2. Run one or more benchmark configs into `outputs/<timestamp>/`
3. Export the selected summaries into stable final tables in `results/`

Example:

```powershell
ie-benchmark export-results `
  --summary outputs/20260314_063054/summary.json `
  --summary outputs/20260314_061420/summary.json `
  --summary outputs/20260314_054734/summary.json `
  --model SmolLM2-1.7B-Instruct `
  --model Qwen2.5-0.5B-Instruct `
  --model Qwen2.5-1.5B-Instruct `
  --output-dir results
```

Generated files:

- `final_capability_metrics.csv`
- `final_capability_metrics.md`
- `final_operational_metrics.csv`
- `final_operational_metrics.md`
- `final_sources.json`
