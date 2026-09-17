#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" || ! -d "$REPO_ROOT/Deployment/cloud" ]]; then
  echo "ERROR: run this from inside the SarembokVE Git checkout."
  exit 1
fi
cd "$REPO_ROOT"

echo "===== SAREMBOKVE UI RECOVERY DEPLOYMENT ====="
echo "Repo: $REPO_ROOT"

git fetch origin main
git checkout main
git pull --ff-only origin main

echo
echo "===== COMMIT ====="
git log -1 --oneline

echo
echo "===== COMPOSE VALIDATION ====="
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml config >/tmp/sarembok-compose.rendered.yaml
echo "compose config: OK"

echo
echo "===== EDGE BUILD / RECREATE ====="
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml build --pull sarembok-edge
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml up -d sarembok-edge

echo
echo "===== CONTAINER STATE ====="
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml ps

echo
echo "===== CADDY CONFIG ====="
docker exec sarembok-edge caddy validate --config /etc/caddy/Caddyfile

echo
echo "===== RUNTIME INTERNAL HEALTH ====="
docker exec sarembok-runtime python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=5).read().decode().strip())"
echo
echo "===== BROWSER WORKER HEALTH ====="
docker exec sarembok-browser python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9100/health', timeout=5).read().decode().strip())"
echo
echo "===== PUBLIC HEALTH ====="
curl -fsS https://sarembok.com/health
echo
echo "===== PUBLIC SESSION ====="
curl -fsS https://sarembok.com/session

echo
echo "===== END-TO-END UI SMOKE ====="
python3 Deployment/cloud/production_ui_smoke.py

echo
echo "===== UI RECOVERY DEPLOYMENT COMPLETE ====="
