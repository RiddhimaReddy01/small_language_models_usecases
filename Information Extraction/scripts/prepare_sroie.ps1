param(
    [string]$OcrDir,
    [string]$LabelsDir,
    [string]$Output = "data/processed/sroie_clean.jsonl"
)

& ie-benchmark ingest-sroie --ocr-dir $OcrDir --labels-dir $LabelsDir --output $Output
