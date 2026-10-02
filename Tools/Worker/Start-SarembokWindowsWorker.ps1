# Sarembok VE Windows 11 Worker Launcher
# Requires Python 3.12+ and a reachable https://sarembok.com deployment.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.12+ and rerun this script."
}

$venv = Join-Path $RepoRoot ".sarembok-worker-venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    python -m venv $venv
}
$py = Join-Path $venv "Scripts\python.exe"

& $py -m pip install --upgrade pip
& $py -m pip install "websockets>=15,<19"

# Install the concrete browser executor once. Chromium is installed separately so
# web_automation is a real capability, not an advertised stub.
# Install the concrete browser executor unconditionally. pip is idempotent, so
# this avoids fragile native Python import probes under PowerShell's stderr
# handling when ErrorActionPreference is set to Stop.
& $py -m pip install "playwright>=1.55,<2"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Playwright."
}

& $py -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install or verify Chromium for Playwright."
}

& $py -c "import playwright; print('Playwright import: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Playwright is not importable after installation."
}

if (-not $env:SAREMBOK_WORKER_ENROLLMENT_TOKEN) {
    $secure = Read-Host "Enter the current Sarembok worker enrollment token" -AsSecureString
    $env:SAREMBOK_WORKER_ENROLLMENT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringUni(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

if (-not $env:SAREMBOK_WORKER_ID) {
    $env:SAREMBOK_WORKER_ID = "win-" + $env:COMPUTERNAME.ToLower()
}

$env:SAREMBOK_WS_URL = "wss://sarembok.com/ws"
$env:SAREMBOK_WORKER_ORIGIN = "https://sarembok.com"
$env:SAREMBOK_WORKER_HEARTBEAT_INTERVAL = "15"
$env:SAREMBOK_WORKER_POLL_INTERVAL = "2"
$env:SAREMBOK_WORKER_WORKSPACE = (Join-Path $RepoRoot "Deployment")

Write-Host ""
Write-Host "===== SAREMBOK WINDOWS WORKER =====" -ForegroundColor Cyan
Write-Host "WORKER ID : $env:SAREMBOK_WORKER_ID"
Write-Host "ENDPOINT  : $env:SAREMBOK_WS_URL"
Write-Host "ORIGIN    : $env:SAREMBOK_WORKER_ORIGIN"
Write-Host "CAPS      : auto-detected concrete local executors"
Write-Host ""

& $py "Deployment/cloud/worker_client.py"
