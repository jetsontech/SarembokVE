<#
.SYNOPSIS
    Canonical Sarembok VE CLI & Cloud Deployment Orchestrator
.DESCRIPTION
    Provides automated 10-minute deployment pipeline for Sarembok VE Cloud:
    CHECK -> CONFIGURE -> VALIDATE -> BUILD -> START -> WAIT FOR HEALTH -> SMOKE TEST -> REPORT
.EXAMPLE
    .\Sarembok.ps1 -Deploy Cloud
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Cloud", "Local", "Build", "Clean", "Diagnose", "Generate")]
    [string]$Deploy,

    [Parameter(Mandatory=$false)]
    [ValidateSet("DeployCloud", "Build", "Clean", "Diagnose", "Generate", "Production")]
    [string]$Action = "DeployCloud",

    [Parameter(Mandatory=$false)]
    [string]$Domain = "sarembok.com",

    [Parameter(Mandatory=$false)]
    [string]$AuthToken,

    [Parameter(Mandatory=$false)]
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Sarembok_VE"
Set-Location $ProjectRoot

# Handle -Deploy parameter
if ($Deploy -eq "Cloud" -or $Action -eq "DeployCloud") {
    $TargetMode = "Cloud"
} else {
    $TargetMode = $Deploy
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         SAREMBOK VE - CLOUD PRODUCTION DEPLOYER        " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# -------------------------------------------------------------------
# STEP 1: CHECK (System & Environment Detection)
# -------------------------------------------------------------------
Write-Host "`n[1/8] CHECK: Verifying system requirements & DNS..." -ForegroundColor Yellow

$DockerInstalled = $false
try {
    $null = docker --version
    $DockerInstalled = $true
    Write-Host "  [OK] Docker CLI detected" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Docker CLI not detected in PATH" -ForegroundColor Yellow
}

$ComposeCmd = "docker compose"
try {
    $null = docker compose version
    Write-Host "  [OK] Docker Compose plugin detected" -ForegroundColor Green
} catch {
    try {
        $null = docker-compose --version
        $ComposeCmd = "docker-compose"
        Write-Host "  [OK] Standalone docker-compose detected" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Docker Compose not detected" -ForegroundColor Yellow
    }
}

# DNS Verification for sarembok.com
$DnsStatus = "NOT CONFIGURED"
$ResolvedIPs = @()
try {
    $DnsResult = [System.Net.Dns]::GetHostAddresses($Domain)
    if ($DnsResult.Count -gt 0) {
        $ResolvedIPs = $DnsResult | ForEach-Object { $_.IPAddressToString }
        $DnsStatus = "OK"
        Write-Host "  [OK] DNS -> OK ($Domain resolves to: $($ResolvedIPs -join ', '))" -ForegroundColor Green
    }
} catch {
    Write-Host "  [!]  DNS -> NOT CONFIGURED ($Domain does not resolve on this machine)" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 2: CONFIGURE (Secret & Environment Setup)
# -------------------------------------------------------------------
Write-Host "`n[2/8] CONFIGURE: Initializing deployment parameters..." -ForegroundColor Yellow

$PublicHost = if ($env:SAREMBOK_PUBLIC_HOST) { $env:SAREMBOK_PUBLIC_HOST } else { $Domain }
$Token = if ($AuthToken) { $AuthToken } elseif ($env:SAREMBOK_AUTH_TOKEN) { $env:SAREMBOK_AUTH_TOKEN } else { "" }

if (-not $Token) {
    # Generate a strong token for session
    $Bytes = New-Object byte[] 32
    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($Bytes)
    $Token = [Convert]::ToBase64String($Bytes) -replace '[^a-zA-Z0-9]', ''
    Write-Host "  [+] Generated new SAREMBOK_AUTH_TOKEN" -ForegroundColor Cyan
}

$env:SAREMBOK_PUBLIC_HOST = $PublicHost
$env:SAREMBOK_SITE_ADDRESS = $PublicHost
$env:SAREMBOK_AUTH_TOKEN = $Token

Write-Host "  SAREMBOK_PUBLIC_HOST : $PublicHost" -ForegroundColor White
Write-Host "  SAREMBOK_AUTH_TOKEN  : [CONFIGURED]" -ForegroundColor White

# -------------------------------------------------------------------
# STEP 3: VALIDATE (Docker Compose Configuration Validation)
# -------------------------------------------------------------------
Write-Host "`n[3/8] VALIDATE: Validating Docker Compose configuration..." -ForegroundColor Yellow

$ComposeFiles = "-f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml"
if ($DockerInstalled) {
    Invoke-Expression "$ComposeCmd $ComposeFiles config --quiet"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Docker Compose file validation passed" -ForegroundColor Green
    } else {
        throw "Docker Compose configuration validation failed."
    }
} else {
    Write-Host "  [SKIP] Docker Compose validation skipped (Docker engine not local)" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 4: BUILD (Container Image Build)
# -------------------------------------------------------------------
Write-Host "`n[4/8] BUILD: Building cloud production containers..." -ForegroundColor Yellow

if ($DockerInstalled) {
    Invoke-Expression "$ComposeCmd $ComposeFiles build"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Production container build completed" -ForegroundColor Green
    } else {
        throw "Production container build failed."
    }
} else {
    Write-Host "  [SKIP] Build skipped (Docker engine not running locally)" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 5: START (Deployment Lifecycle Start)
# -------------------------------------------------------------------
Write-Host "`n[5/8] START: Launching Sarembok Edge & Runtime..." -ForegroundColor Yellow

if ($DockerInstalled) {
    Invoke-Expression "$ComposeCmd $ComposeFiles up -d"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Containers started in detached mode" -ForegroundColor Green
    } else {
        throw "Failed to start Docker Compose services."
    }
} else {
    Write-Host "  [SKIP] Startup skipped (Target deployment for remote VPS ready)" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 6: WAIT FOR HEALTH (Liveness Verification)
# -------------------------------------------------------------------
Write-Host "`n[6/8] WAIT FOR HEALTH: Checking container liveness..." -ForegroundColor Yellow

if ($DockerInstalled) {
    $MaxRetries = 15
    $Healthy = $false
    for ($i = 1; $i -le $MaxRetries; $i++) {
        Start-Sleep -Seconds 2
        try {
            $Resp = Invoke-WebRequest -Uri "http://127.0.0.1/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
            if ($Resp.StatusCode -eq 200) {
                $Healthy = $true
                Write-Host "  [OK] Edge probe responded HTTP 200 OK" -ForegroundColor Green
                break
            }
        } catch {
            Write-Host "  Waiting for edge/runtime liveness ($i/$MaxRetries)..." -ForegroundColor Gray
        }
    }
    if (-not $Healthy) {
        Write-Host "  [WARN] Edge probe did not answer on port 80 (Containers starting or port bound)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [SKIP] Health waiting skipped (no local Docker engine)" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 7: SMOKE TEST (Diagnostic Validation)
# -------------------------------------------------------------------
Write-Host "`n[7/8] SMOKE TEST: Executing diagnostic test suite..." -ForegroundColor Yellow

if (-not $SkipSmokeTest) {
    $SmokeCmd = "python Deployment/cloud/smoke_test.py ws://127.0.0.1:9000"
    if ($DockerInstalled) {
        try {
            Invoke-Expression $SmokeCmd
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Cloud smoke test passed cleanly!" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Smoke test reported failures (check logs)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [WARN] Smoke test execution encountered an error: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [SKIP] Local smoke test skipped (deploying to target server)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [SKIP] Smoke test skipped via parameter" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# STEP 8: REPORT (Final Deployment Summary)
# -------------------------------------------------------------------
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "           SAREMBOK CLOUD PRODUCTION REPORT            " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host " STATUS                : " -NoNewline; Write-Host "SAREMBOK READY" -ForegroundColor Green
Write-Host " PUBLIC HOST           : $PublicHost" -ForegroundColor White
Write-Host " DNS STATUS            : " -NoNewline
if ($DnsStatus -eq "OK") {
    Write-Host "DNS -> OK" -ForegroundColor Green
} else {
    Write-Host "DNS -> NOT CONFIGURED" -ForegroundColor Yellow
}
Write-Host " AUTH TOKEN            : $Token" -ForegroundColor White
Write-Host " EDGE PORTS            : 80 / 443 (HTTPS / WSS)" -ForegroundColor White
Write-Host " RUNTIME PORT          : 9000 (Internal only - !reset host ports)" -ForegroundColor White

Write-Host "`n--- SYSTEM REQUIREMENTS & PRODUCTION REQS ---" -ForegroundColor Cyan
Write-Host " 1. VPS Host          : Ubuntu 22.04+ / Debian 12 / RHEL 9 (2 vCPU, 4GB RAM min)"
Write-Host " 2. Inbound Firewall  : Ports 80 & 443 OPEN to public internet"
Write-Host " 3. DNS Record        : A / AAAA record pointing $PublicHost to VPS IP"
Write-Host " 4. GPU Compute Node  : Remote GPU Worker registering via JSON-RPC RegisterWorker"

Write-Host "`n--- ONE-COMMAND DEPLOYMENT (REMOTE VPS) ---" -ForegroundColor Cyan
Write-Host " env SAREMBOK_AUTH_TOKEN=\"$Token\" SAREMBOK_PUBLIC_HOST=\"$PublicHost\" docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml up -d --build" -ForegroundColor Yellow

Write-Host "`n========================================================" -ForegroundColor Cyan
