param(
    [string]$ServerIP = "15.204.173.205",
    [string]$User = "ubuntu",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sarembok_vps"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SAREMBOK PRODUCTION VPS DEPLOYMENT (OVH: $ServerIP)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$remoteCmd = @'
set -e
echo "[1/4] Pulling latest commits from origin main..."
cd ~/Sarembok_VE
git fetch origin main
git checkout main
git pull origin main

echo "[2/4] Verifying auth token..."
export SAREMBOK_AUTH_TOKEN="$(sudo cat /etc/sarembok/auth_token)"
test -n "$SAREMBOK_AUTH_TOKEN" && echo "Auth token loaded successfully."

echo "[3/4] Rebuilding and recreating production runtime container..."
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  up -d --build --force-recreate sarembok-runtime

echo "[4/4] Verifying container health..."
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  ps

echo "=========================================================="
echo " DEPLOYMENT COMPLETE: Sarembok runtime active on OVH!"
echo "=========================================================="
'@

Write-Host "[INFO] Connecting to $User@$ServerIP using key: $KeyPath" -ForegroundColor Yellow
Write-Host "[NOTE] If prompted, please enter your private key passphrase." -ForegroundColor Gray
Write-Host ""

if (Test-Path $KeyPath) {
    ssh -t -i "$KeyPath" "$User@$ServerIP" "$remoteCmd"
} else {
    ssh -t "$User@$ServerIP" "$remoteCmd"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] OVH Production Server updated successfully." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Remote deployment returned exit code $LASTEXITCODE" -ForegroundColor Red
}
