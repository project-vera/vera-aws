# ========================================
# Vera GCP Installer for Windows
# ========================================
# Usage: .\install.ps1
# For Windows: uv, VERA_ENDPOINT / VERA_PROJECT, gcloud install, user config,
# isolated vera-gcloud-config, gcpcli wrapper (uv run gcpcli / Activate.ps1 then gcpcli).
# ========================================

$root = $PSScriptRoot
$Endpoint = if ($env:VERA_ENDPOINT) { $env:VERA_ENDPOINT } else { "http://localhost:9100" }
$Project = if ($env:VERA_PROJECT) { $env:VERA_PROJECT } else { "vera-project" }

function Refresh-PathEnv {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- uv (install.sh uses curl | sh on Darwin/Linux; Windows uses official install.ps1) ---
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> uv not found, installing..."
    $resp = Invoke-WebRequest -UseBasicParsing "https://astral.sh/uv/install.ps1"
    $installPs1 = $resp.Content
    if ($installPs1 -is [byte[]]) {
        $installPs1 = [System.Text.Encoding]::UTF8.GetString($installPs1)
    }
    Invoke-Expression $installPs1
    Refresh-PathEnv
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "!!! uv install failed or not on PATH."
        Write-Host "    See https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

Push-Location $root
try {
    uv sync
} finally {
    Pop-Location
}

$venvPath = Join-Path $root ".venv"
$binDir = Join-Path $venvPath "Scripts"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}
& (Join-Path $binDir "Activate.ps1")

Write-Host "==> Vera GCP installer  (endpoint: $Endpoint, project: $Project)"

# --- Google Cloud SDK (gcloud CLI) — winget / choco ~ brew / apt / yum ---
$gcloudBin = $null
if (Get-Command gcloud -ErrorAction SilentlyContinue) {
    $gcloudBin = (Get-Command gcloud -ErrorAction Stop).Source
    Write-Host "==> gcloud found: $(gcloud version 2>&1 | Select-Object -First 1)"
} else {
    Write-Host "==> gcloud not found, attempting install..."
    $installed = $false

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Google.CloudSDK --accept-package-agreements --accept-source-agreements --silent
        Refresh-PathEnv
        if (Get-Command gcloud -ErrorAction SilentlyContinue) { $installed = $true }
    }

    if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
        & choco install gcloudsdk -y
        Refresh-PathEnv
        if (Get-Command gcloud -ErrorAction SilentlyContinue) { $installed = $true }
    }

    if (-not $installed) {
        Write-Host "!!! Could not auto-install gcloud. Install manually:" -ForegroundColor Red
        Write-Host "    https://cloud.google.com/sdk/docs/install"
        exit 1
    }
    $gcloudBin = (Get-Command gcloud -ErrorAction Stop).Source
}

# --- Disable gcloud auth for local emulator use ---
$gcloudConfigDir = $env:CLOUDSDK_CONFIG
if (-not $gcloudConfigDir) {
    $gcloudConfigDir = Join-Path $env:USERPROFILE ".config\gcloud"
}
if (-not (Test-Path $gcloudConfigDir)) {
    New-Item -ItemType Directory -Path $gcloudConfigDir -Force | Out-Null
}

gcloud config set core/disable_usage_reporting true 2>$null
gcloud config set core/project $Project 2>$null

$propertiesFile = Join-Path $gcloudConfigDir "properties"
$hasCore = $false
if (Test-Path $propertiesFile) {
    $hasCore = [bool](Get-Content $propertiesFile -ErrorAction SilentlyContinue | Select-String '\[core\]')
}
if (-not $hasCore) {
    Add-Content -Path $propertiesFile -Value "`n[core]`ndisable_usage_reporting = true"
}

# --- gcpcli wrapper ---
$veraConfigDir = Join-Path $venvPath "vera-gcloud-config"
if (-not (Test-Path $veraConfigDir)) {
    New-Item -ItemType Directory -Path $veraConfigDir -Force | Out-Null
}

if (-not $gcloudBin) {
    Write-Host "!!! gcloud not found in PATH — wrapper will try 'gcloud' at runtime" -ForegroundColor Yellow
    $gcloudBin = "gcloud"
}

$tokenFile = Join-Path $veraConfigDir "access_token"
Set-Content -Path $tokenFile -Value "vera-local-token" -NoNewline

$gSaved = $env:CLOUDSDK_CONFIG
$env:CLOUDSDK_CONFIG = $veraConfigDir
& $gcloudBin config set core/project $Project 2>$null
& $gcloudBin config set core/disable_usage_reporting true 2>$null
& $gcloudBin config set core/disable_prompts true 2>$null
$env:CLOUDSDK_CONFIG = $gSaved

Remove-Item -Path (Join-Path $binDir "gcpcli.exe") -ErrorAction SilentlyContinue

$veraConfigDirEsc = $veraConfigDir.Replace("'", "''")
$tokenFileEsc = $tokenFile.Replace("'", "''")
$endpointEsc = "$Endpoint/".Replace("'", "''")
$projectEsc = $Project.Replace("'", "''")
$gcloudBinEsc = $gcloudBin.Replace("'", "''")

$gcpcliPs1 = Join-Path $binDir "gcpcli.ps1"
$gcpcliContent = @"
param([Parameter(ValueFromRemainingArguments=`$true)]`$args)
# Vera GCP — local emulator wrapper for gcloud compute
`$env:CLOUDSDK_CONFIG = '$veraConfigDirEsc'
`$env:CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE = '$endpointEsc'
`$env:CLOUDSDK_CORE_DISABLE_PROMPTS = '1'
`$env:CLOUDSDK_CORE_PROJECT = '$projectEsc'
& '$gcloudBinEsc' compute --access-token-file='$tokenFileEsc' `@args
"@
Set-Content -Path $gcpcliPs1 -Value $gcpcliContent -Force -Encoding UTF8

$gcpcliCmd = Join-Path $binDir "gcpcli.cmd"
$gcpcliCmdContent = @"
@echo off
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%gcpcli.ps1" %*
"@
Set-Content -Path $gcpcliCmd -Value $gcpcliCmdContent -Force -Encoding ASCII

Write-Host "==> Created gcpcli wrapper: $gcpcliCmd (and $gcpcliPs1)"

Write-Host ""
Write-Host "==> Done!"
Write-Host ""
Write-Host "    Start the emulator:"
Write-Host "      uv run main.py"
Write-Host ""
Write-Host "    Run compute commands (no real GCP account needed):"
Write-Host "      uv run gcpcli instances list"
Write-Host "      uv run gcpcli disks list"

& (Join-Path $binDir "Activate.ps1")
