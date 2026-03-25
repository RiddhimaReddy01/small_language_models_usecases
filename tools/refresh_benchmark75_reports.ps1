$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Expected repo venv interpreter at $python. Create the venv and install requirements first."
}

Push-Location $repoRoot
try {
    & $python -m pytest tests

    $env:PYTHONPATH = "."
    & $python "tools\generate_benchmark75_sddf.py"
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    & $python "tools\generate_business_dashboard.py"
}
finally {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    Pop-Location
}
