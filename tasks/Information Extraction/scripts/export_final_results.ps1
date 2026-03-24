param(
    [string]$OutputDir = "results"
)

ie-benchmark export-results `
  --summary outputs/20260314_063054/summary.json `
  --summary outputs/20260314_061420/summary.json `
  --summary outputs/20260314_054734/summary.json `
  --model SmolLM2-1.7B-Instruct `
  --model Qwen2.5-0.5B-Instruct `
  --model Qwen2.5-1.5B-Instruct `
  --output-dir $OutputDir
