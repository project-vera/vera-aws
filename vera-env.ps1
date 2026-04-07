<#
.SYNOPSIS
Point host AWS/GCP CLIs at Vera endpoints.
Run with dot-source:
    . .\vera-env.ps1
NOTE:
    If you get a "script execution is disabled" error, run:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    This temporarily allows the current PowerShell session to run scripts without changing system policy.
#>

# AWS
if (-not $env:AWS_ENDPOINT_URL) { $env:AWS_ENDPOINT_URL = "http://localhost:5003" }
if (-not $env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION = "us-east-1" }
$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"

# GCP
if (-not $env:CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE) { $env:CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE = "http://localhost:9100/" }
if (-not $env:CLOUDSDK_CORE_PROJECT) { $env:CLOUDSDK_CORE_PROJECT = "vera-project" }
$env:CLOUDSDK_AUTH_DISABLE_CREDENTIALS = "true"

# Info
Write-Host "Vera environment active" -ForegroundColor Green
Write-Host "  AWS CLI  -> $env:AWS_ENDPOINT_URL"
Write-Host "  GCP SDK  -> $env:CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE"