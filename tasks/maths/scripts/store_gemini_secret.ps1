<#
Stores the GEMINI API key securely in the PowerShell SecretStore (SecretManagement).

Usage:
  Run in PowerShell:
    ./store_gemini_secret.ps1
  The script will install required modules (per-user) if missing, register a local vault,
  and prompt you to paste the API key securely.

To read the secret in a session later:
  $key = Get-Secret -Name GEMINI_API_KEY
  $env:GEMINI_API_KEY = $key

#>

Write-Host "Ensuring SecretManagement and SecretStore modules are installed (current user)..."
if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.SecretManagement)) {
    Install-Module Microsoft.PowerShell.SecretManagement -Scope CurrentUser -Force
}
if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.SecretStore)) {
    Install-Module Microsoft.PowerShell.SecretStore -Scope CurrentUser -Force
}

Import-Module Microsoft.PowerShell.SecretManagement -ErrorAction Stop
Import-Module Microsoft.PowerShell.SecretStore -ErrorAction Stop

$vaults = Get-SecretVault -ErrorAction SilentlyContinue
if (-not ($vaults | Where-Object { $_.Name -eq 'LocalSecretStore' })) {
    Write-Host "Registering a new SecretStore vault named 'LocalSecretStore'..."
    Register-SecretVault -Name LocalSecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
}

Write-Host "Enter the GEMINI API key (input hidden):"
$secure = Read-Host -AsSecureString

Set-Secret -Name GEMINI_API_KEY -Secret $secure -Vault LocalSecretStore
Write-Host "GEMINI API key stored in SecretStore as 'GEMINI_API_KEY'. Use Get-Secret to retrieve it." -ForegroundColor Green
