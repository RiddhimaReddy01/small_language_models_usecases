$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Expected repo venv interpreter at $python. Create the venv and install requirements first."
}

Push-Location $repoRoot
try {
    & $python "tools\rerun_missing_benchmark_samples.py" --task classification --model-folder tinyllama_1.1b
    & $python "tools\rerun_missing_benchmark_samples.py" --task code_generation --model-folder tinyllama_1.1b
    & $python "tools\rerun_missing_benchmark_samples.py" --task code_generation --model-folder phi3_mini
    & $python "tools\rerun_missing_benchmark_samples.py" --task maths --model-folder tinyllama_1.1b
    & $python "tools\rerun_missing_benchmark_samples.py" --task text_generation --model-folder tinyllama_1.1b
    & $python "tools\rerun_missing_benchmark_samples.py" --task text_generation --model-folder phi3_mini

    $env:PYTHONPATH = "."
    & $python "tools\generate_benchmark75_sddf.py"
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    & $python "tools\generate_business_dashboard.py"
}
finally {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    Pop-Location
}
