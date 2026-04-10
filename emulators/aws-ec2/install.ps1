# ========================================
# Vera AWS Installer for Windows
# ========================================
# Usage: .\install.ps1
# For Windows: uv + uv sync, VERA_ENDPOINT, AWS CLI / Terraform install attempts,
# [vera] credentials, awscli + terlocal wrappers in .venv\Scripts, activate venv.
# README: `uv run awscli ...` and (after Activate.ps1) bare `awscli ...`.
# ========================================

$root = $PSScriptRoot
# Baked into wrappers at install time; re-run install.ps1 to change.
$Endpoint = if ($env:VERA_ENDPOINT) { $env:VERA_ENDPOINT } else { "http://localhost:5003" }

function Refresh-PathEnv {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- uv ---
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

Write-Host "==> Vera AWS - Installer (endpoint: $Endpoint)"

# --- AWS CLI (winget / choco ~ brew / apt / yum) ---
if (Get-Command aws -ErrorAction SilentlyContinue) {
    Write-Host "==> AWS CLI found: $((& aws --version 2>&1 | Select-Object -First 1))"
} else {
    Write-Host "==> AWS CLI not found, attempting install..."
    $installed = $false

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Amazon.AWSCLI --accept-package-agreements --accept-source-agreements --silent
        Refresh-PathEnv
        if (Get-Command aws -ErrorAction SilentlyContinue) { $installed = $true }
    }

    if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
        & choco install awscli -y
        Refresh-PathEnv
        if (Get-Command aws -ErrorAction SilentlyContinue) { $installed = $true }
    }

    if (-not $installed) {
        Write-Host "!!! Could not auto-install AWS CLI." -ForegroundColor Red
        Write-Host "    Install manually: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    }
}

$awsExe = (Get-Command aws -ErrorAction Stop).Source

# --- Terraform ---
if (Get-Command terraform -ErrorAction SilentlyContinue) {
    Write-Host "==> Terraform found: $((& terraform version -json 2>&1 | Select-Object -First 1))"
} else {
    Write-Host "==> Terraform not found, attempting install..."
    $tfOk = $false

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Hashicorp.Terraform --accept-package-agreements --accept-source-agreements --silent
        Refresh-PathEnv
        if (Get-Command terraform -ErrorAction SilentlyContinue) { $tfOk = $true }
    }

    if (-not $tfOk -and (Get-Command choco -ErrorAction SilentlyContinue)) {
        & choco install terraform -y
        Refresh-PathEnv
        if (Get-Command terraform -ErrorAction SilentlyContinue) { $tfOk = $true }
    }

    if (-not $tfOk) {
        Write-Host "!!! Could not auto-install Terraform (optional, needed for terlocal)." -ForegroundColor Yellow
        Write-Host "    Install manually: https://developer.hashicorp.com/terraform/install"
        Write-Host "    Continuing without Terraform support..."
    }
}

# --- AWS credentials ---
$awsDir = Join-Path $env:USERPROFILE ".aws"
if (-not (Test-Path $awsDir)) { New-Item -ItemType Directory -Path $awsDir | Out-Null }

$credFile = Join-Path $awsDir "credentials"
if (-not (Get-Content $credFile -ErrorAction SilentlyContinue | Select-String "\[vera\]")) {
    Add-Content $credFile "`n[vera]`naws_access_key_id = test`naws_secret_access_key = test`nregion = us-east-1`n"
    Write-Host "==> Adding [vera] profile to ~/.aws/credentials"
} else {
    Write-Host "==> AWS [vera] profile already exists"
}

# --- awscli in .venv\Scripts (uv run awscli; Activate.ps1 then awscli) ---
Remove-Item -Path (Join-Path $binDir "awscli.exe") -ErrorAction SilentlyContinue

$usePythonModule = ($awsExe -like "$($binDir.TrimEnd('\'))*")
$wrapperPs1 = Join-Path $binDir "awscli.ps1"
if ($usePythonModule) {
    $wrapperContent = @"
param([Parameter(ValueFromRemainingArguments=`$true)]`$args)
& '$binDir\python.exe' -m awscli --endpoint-url='$Endpoint' --profile vera `@args
"@
} else {
    $wrapperContent = @"
param([Parameter(ValueFromRemainingArguments=`$true)]`$args)
& '$awsExe' --endpoint-url='$Endpoint' --profile vera `@args
"@
}
Set-Content -Path $wrapperPs1 -Value $wrapperContent -Force -Encoding UTF8

$wrapperCmd = Join-Path $binDir "awscli.cmd"
$cmdContent = @"
@echo off
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%awscli.ps1" %*
"@
Set-Content -Path $wrapperCmd -Value $cmdContent -Force -Encoding ASCII

if ($usePythonModule) {
    Remove-Item -Path (Join-Path $binDir "aws.exe") -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $binDir "aws.cmd") -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $binDir "aws") -ErrorAction SilentlyContinue
    $awsCmdDirect = @"
@echo off
set "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%python.exe" -m awscli --endpoint-url=$Endpoint --profile vera %*
"@
    Set-Content -Path (Join-Path $binDir "aws.cmd") -Value $awsCmdDirect -Force -Encoding ASCII
    Set-Content -Path (Join-Path $binDir "aws.ps1") -Value $wrapperContent -Force -Encoding UTF8
    Write-Host "==> Replaced pip aws launchers with aws.cmd / aws.ps1 (aws ec2 ...)"
}

Write-Host "==> Created awscli wrapper: $wrapperCmd (and $wrapperPs1)"

$overrideTfBody = @"
provider "aws" {
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = "$Endpoint"
  }
}
"@
$overrideEscaped = $overrideTfBody -replace '"', '`"' -replace "`r`n", "`n" -replace "`n", "`n"
$terlocalPs1 = Join-Path $binDir "terlocal.ps1"
$terlocalContent = @"
param([Parameter(ValueFromRemainingArguments=`$true)]`$args)
`$env:AWS_ACCESS_KEY_ID = 'test'
`$env:AWS_SECRET_ACCESS_KEY = 'test'
if (-not `$env:AWS_DEFAULT_REGION) { `$env:AWS_DEFAULT_REGION = 'us-east-1' }
`$override = '_vera_override.tf'
if (-not (Test-Path `$override)) {
`$overrideContent = "$overrideEscaped"
Set-Content -Path `$override -Value `$overrideContent -Encoding UTF8
}
terraform `@args
"@
Set-Content -Path $terlocalPs1 -Value $terlocalContent -Force -Encoding UTF8

$terlocalCmd = Join-Path $binDir "terlocal.cmd"
$terlocalCmdContent = @"
@echo off
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%terlocal.ps1" %*
"@
Set-Content -Path $terlocalCmd -Value $terlocalCmdContent -Force -Encoding ASCII

Write-Host "==> Created terlocal wrapper: $terlocalCmd (and $terlocalPs1)"
Write-Host "==> After Activate.ps1: awscli ec2 ...   or: uv run awscli ec2 ..."

& (Join-Path $venvPath "Scripts\Activate.ps1")
