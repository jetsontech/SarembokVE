#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export COMPOSE="docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml"

: "${SAREMBOK_AUTH_TOKEN:?Set SAREMBOK_AUTH_TOKEN before production deployment}"

echo "============================================================"
echo "SAREMBOK CLOUD SCHEDULER V3 DEPLOYMENT"
echo "============================================================"
echo "This procedure does NOT remove persistent volumes."

echo
git fetch origin cloud-scheduler-v3-production
git checkout cloud-scheduler-v3-production
git pull --ff-only origin cloud-scheduler-v3-production

echo
git rev-parse --short HEAD

git tag --points-at HEAD

echo

echo "===== CONFIG VALIDATION ====="
$COMPOSE config >/dev/null

echo "[OK] Compose configuration"

echo

echo "===== BUILD RUNTIME ====="
$COMPOSE build sarembok-runtime

echo

echo "===== RECREATE RUNTIME ONLY ====="
$COMPOSE up -d --no-deps --force-recreate sarembok-runtime

echo

echo "===== EDGE STATUS ====="
$COMPOSE up -d sarembok-edge

echo

echo "===== HEALTH ====="
sleep 3
curl -fsS https://sarembok.com/health
printf '\n'
$COMPOSE ps

echo

echo "===== PUBLIC SCHEDULER V3 SMOKE ====="
python Deployment/cloud/public_scheduler_v3_smoke.py

echo

echo "[OK] SCHEDULER V3 DEPLOYMENT COMPLETE"
