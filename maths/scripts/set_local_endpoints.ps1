<#
Sets persistent user environment variables for local SLM endpoints.

Usage:
  - Run in PowerShell:
      ./set_local_endpoints.ps1
  - You will be prompted for each endpoint; press Enter to accept the default.

After running, restart your terminal or log out/in for changes to take effect.
#>

Function Prompt-Default($prompt, $default) {
    $val = Read-Host "$prompt [$default]"
    if ([string]::IsNullOrWhiteSpace($val)) { return $default }
    return $val
}

$defaultEndpoint = "http://localhost:11434/api/generate"
$phi3 = Prompt-Default "LOCAL_SLM_ENDPOINT_PHI3" $defaultEndpoint
$gemma = Prompt-Default "LOCAL_SLM_ENDPOINT_GEMMA2B" $defaultEndpoint
$mistral = Prompt-Default "LOCAL_SLM_ENDPOINT_MISTRAL7B" $defaultEndpoint

# Persist to user environment
[System.Environment]::SetEnvironmentVariable("LOCAL_SLM_ENDPOINT_PHI3", $phi3, "User")
[System.Environment]::SetEnvironmentVariable("LOCAL_SLM_ENDPOINT_GEMMA2B", $gemma, "User")
[System.Environment]::SetEnvironmentVariable("LOCAL_SLM_ENDPOINT_MISTRAL7B", $mistral, "User")

Write-Host "Wrote endpoints to user environment. Restart your terminal to pick them up." -ForegroundColor Green
