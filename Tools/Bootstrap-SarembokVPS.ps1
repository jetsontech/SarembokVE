param(
    [string]$ServerIP = "15.204.173.205",
    [string]$User = "ubuntu"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SAREMBOK VPS BOOTSTRAP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Testing SSH..." -ForegroundColor Yellow

ssh "$User@$ServerIP" "echo SAREMBOK_SSH_OK"

if ($LASTEXITCODE -ne 0) {
    throw "SSH connection failed."
}

Write-Host "[2/4] Building remote bootstrap..." -ForegroundColor Yellow

$bashLines = @(
    '#!/usr/bin/env bash'
    'set -euo pipefail'
    ''
    'echo "========================================"'
    'echo " SAREMBOK CONTROL PLANE BOOTSTRAP"'
    'echo "========================================"'
    ''
    'echo "[1/8] Updating Ubuntu..."'
    'sudo apt-get update'
    'sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y'
    ''
    'echo "[2/8] Installing base packages..."'
    'sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl git gnupg jq unzip ufw fail2ban openssh-server'
    ''
    'echo "[3/8] Configuring 4 GB swap..."'
    'if ! swapon --show | grep -q .; then'
    '    if [ ! -f /swapfile ]; then'
    '        sudo fallocate -l 4G /swapfile'
    '        sudo chmod 600 /swapfile'
    '        sudo mkswap /swapfile'
    '    fi'
    '    sudo swapon /swapfile'
    '    if ! grep -q "^/swapfile " /etc/fstab; then'
    '        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null'
    '    fi'
    'fi'
    ''
    'echo "[4/8] Installing Docker..."'
    'if ! command -v docker >/dev/null 2>&1; then'
    '    sudo install -m 0755 -d /etc/apt/keyrings'
    '    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg'
    '    sudo chmod a+r /etc/apt/keyrings/docker.gpg'
    '    . /etc/os-release'
    '    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null'
    '    sudo apt-get update'
    '    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin'
    'fi'
    'sudo systemctl enable --now docker'
    ''
    'echo "[5/8] Configuring Docker access..."'
    'sudo usermod -aG docker "$USER" || true'
    ''
    'echo "[6/8] Configuring firewall..."'
    'sudo ufw --force reset'
    'sudo ufw default deny incoming'
    'sudo ufw default allow outgoing'
    'sudo ufw allow 22/tcp'
    'sudo ufw allow 80/tcp'
    'sudo ufw allow 443/tcp'
    'sudo ufw --force enable'
    ''
    'echo "[7/8] Enabling security services..."'
    'sudo systemctl enable --now ssh'
    'sudo systemctl enable --now fail2ban'
    ''
    'echo "[8/8] Verification..."'
    'echo "=== OS ==="'
    'grep PRETTY_NAME /etc/os-release'
    'echo "=== CPU ==="'
    'nproc'
    'echo "=== MEMORY ==="'
    'free -h'
    'echo "=== SWAP ==="'
    'swapon --show'
    'echo "=== DOCKER ==="'
    'docker --version'
    'docker compose version'
    'echo "=== FIREWALL ==="'
    'sudo ufw status verbose'
    'echo "=== LISTENING PORTS ==="'
    'sudo ss -lntp'
    'echo "=== BOOTSTRAP COMPLETE ==="'
)

$bashScript = $bashLines -join "`n"

Write-Host "[3/4] Streaming bootstrap to VPS..." -ForegroundColor Yellow

$bashScript | ssh "$User@$ServerIP" "cat > /tmp/sarembok-vps-bootstrap.sh && chmod +x /tmp/sarembok-vps-bootstrap.sh && /tmp/sarembok-vps-bootstrap.sh"

if ($LASTEXITCODE -ne 0) {
    throw "Remote bootstrap failed."
}

Write-Host "[4/4] Complete." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " SAREMBOK VPS READY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
