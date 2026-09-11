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
echo "[3/4] Updating production edge and runtime containers..."
# Determine repository directory (SarembokVE or Sarembok_VE)
if [ -d "$HOME/SarembokVE" ]; then
  cd "$HOME/SarembokVE"
elif [ -d "$HOME/Sarembok_VE" ]; then
  cd "$HOME/Sarembok_VE"
fi
git fetch origin main
git checkout main
git reset --hard origin/main

docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml up -d --build --force-recreate sarembok-runtime sarembok-edge

echo "[4/4] Verifying container health..."
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  ps

echo "=========================================================="
echo " DEPLOYMENT COMPLETE: Sarembok runtime active on OVH!"
echo "=========================================================="
'@

$cleanBash = ($remoteCmd -replace "`r`n", "`n") -replace "`r", "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($cleanBash))
$execCmd = "echo '$b64' | base64 -d | bash"

Write-Host "[INFO] Connecting to $User@$ServerIP using key: $KeyPath" -ForegroundColor Yellow
Write-Host "[NOTE] If prompted, please enter your private key passphrase." -ForegroundColor Gray
Write-Host ""

if (Test-Path $KeyPath) {
    ssh -t -i "$KeyPath" "$User@$ServerIP" "$execCmd"
} else {
    ssh -t "$User@$ServerIP" "$execCmd"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] OVH Production Server updated successfully." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Remote deployment returned exit code $LASTEXITCODE" -ForegroundColor Red
}
