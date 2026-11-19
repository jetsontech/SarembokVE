# ============================================================================
# Copyright (c) 2026 Timothy Hall Jr. / Jetsontech. All rights reserved.
#
# This source code is licensed under the Business Source License 1.1 (BSL).
# Commercial use, deployment in production environments, or redistribution 
# for profit is strictly prohibited without a valid commercial license.
#
# For commercial inquiries, licensing, or partnerships, contact the Licensor.
# ============================================================================

param(
    [string]$ServerIP = "15.204.173.205",
    [string]$User = "ubuntu",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\sarembok_agent",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SAREMBOK FRONTEND DEPLOYMENT (OVH: $ServerIP)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$dryRunValue = if ($DryRun) { "true" } else { "false" }
$remoteCmd = @"
set -eu
cd "`$HOME/SarembokVE"

branch=`$(git branch --show-current)
if [ "`$branch" != "main" ]; then
    echo "REFUSED: expected branch main, found `$branch"
    exit 2
fi

tracked_changes=`$(git status --porcelain --untracked-files=no)
if [ -n "`$tracked_changes" ]; then
    echo "REFUSED: tracked VPS changes must be committed or reconciled first."
    git status --short --branch
    exit 3
fi

git fetch origin main
old_head=`$(git rev-parse HEAD)
changed_paths=`$(git diff --name-only "`$old_head" origin/main)
unsupported=`$(printf '%s\n' "`$changed_paths" | sed '/^$/d' | grep -Ev '^(frontend/|Docs/|README\.md`$|CHANGELOG\.md`$|package\.json`$|package-lock\.json`$|\.npmignore`$|([^/]+/)*\.npmignore`$|Tools/Deploy-To-OVH\.ps1`$|public/generated/)' || true)
if [ -n "`$unsupported" ]; then
    echo "REFUSED: this script deploys the static frontend only. These changes require a separate runtime deployment plan:"
    printf '%s\n' "`$unsupported"
    exit 4
fi

if [ "$dryRunValue" = "true" ]; then
    echo "DRY RUN: eligible frontend changes from `$old_head to `$(git rev-parse origin/main):"
    printf '%s\n' "`$changed_paths"
    exit 0
fi

git merge --ff-only origin/main

if ! docker inspect --format '{{.State.Running}}' sarembok-edge 2>/dev/null | grep -qx true; then
    echo "ERROR: sarembok-edge is not running."
    exit 5
fi

check_route() {
    route=`$1
    expected=`$2
    result=`$(curl --resolve sarembok.com:443:127.0.0.1 -k -sS -o /dev/null -w '%{http_code}|%{content_type}' --max-time 10 "https://sarembok.com`$route")
    status=`$(printf '%s' "`$result" | cut -d'|' -f1)
    content_type=`$(printf '%s' "`$result" | cut -d'|' -f2-)
    if [ "`$status" != "200" ]; then
        echo "ERROR: `$route returned HTTP `$status."
        return 1
    fi
    case "`$expected: `$content_type" in
        html: text/html*|png: image/png*|svg: image/svg+xml*|text: text/plain*|xml: text/xml*|xml: application/xml*)
            echo "OK: `$route -> HTTP `$status (`$content_type)"
            ;;
        *)
            echo "ERROR: `$route has unexpected Content-Type `$content_type."
            return 1
            ;;
    esac
}

test -s frontend/index.html
check_route / html
check_route /docs html
check_route /logo.png png
check_route /og-banner.png png
check_route /logo.svg svg
check_route /og-banner.svg svg
check_route /robots.txt text
check_route /sitemap.xml xml

echo "FRONTEND DEPLOYED at `$(git rev-parse --short HEAD). Runtime containers were not rebuilt."
"@

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
