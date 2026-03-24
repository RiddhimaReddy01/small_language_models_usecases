param(
    [string]$PythonExe = "python",
    [switch]$SkipBuildToolsInstall
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-WingetPackage {
    param(
        [string]$PackageId,
        [string]$OverrideArgs = ""
    )

    $showOutput = winget show --id $PackageId --exact --source winget 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "winget package '$PackageId' was not found."
    }

    $arguments = @(
        "install",
        "--id", $PackageId,
        "--exact",
        "--source", "winget",
        "--accept-package-agreements",
        "--accept-source-agreements"
    )
    if ($OverrideArgs) {
        $arguments += @("--override", $OverrideArgs)
    }

    Write-Host "Installing $PackageId via winget..."
    & winget @arguments
}

function Get-VcVarsPath {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) {
        return $null
    }

    $installPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $installPath) {
        return $null
    }

    $vcvars = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
    if (Test-Path $vcvars) {
        return $vcvars
    }
    return $null
}

if (-not (Test-CommandExists "winget")) {
    throw "winget is required for this setup script."
}

if (-not (Test-CommandExists "cmake")) {
    Ensure-WingetPackage -PackageId "Kitware.CMake"
}

$vcvarsPath = Get-VcVarsPath
if (-not $vcvarsPath -and -not $SkipBuildToolsInstall) {
    $override = "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    Ensure-WingetPackage -PackageId "Microsoft.VisualStudio.2022.BuildTools" -OverrideArgs $override
    $vcvarsPath = Get-VcVarsPath
}

if (-not $vcvarsPath) {
    throw "Visual Studio Build Tools with C++ workload were not found. Re-run without -SkipBuildToolsInstall or install them manually."
}

Write-Host "Using vcvars64 at: $vcvarsPath"

$installCommand = @(
    "`"$vcvarsPath`"",
    "&&",
    "$PythonExe -m pip install --upgrade pip setuptools wheel",
    "&&",
    "$PythonExe -m pip install llama-cpp-python"
) -join " "

cmd.exe /c $installCommand

Write-Host "llama-cpp-python installation finished."
