#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "===== SAREMBOK PRODUCTION DEPLOY ====="
echo "Commit: $(git rev-parse --short HEAD)"

echo

echo "===== WORKTREE ====="
git status --short

echo

echo "===== COMPOSE VALIDATION ====="
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  config --quiet

echo "Compose: OK"

echo

echo "===== BUILD ====="
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  build --pull sarembok-runtime

echo "Build: OK"

echo

echo "===== RUNTIME RESTART ====="
docker compose \
  -f Deployment/cloud/compose.yaml \
  -f Deployment/cloud/compose.production.yaml \
  up -d --no-deps --force-recreate sarembok-runtime

echo

echo "===== HEALTH ====="
for i in {1..30}; do
  if curl -fsS https://sarembok.com/health >/tmp/sarembok-health.txt; then
    cat /tmp/sarembok-health.txt
    break
  fi
  sleep 2
done
curl -fsS https://sarembok.com/health

echo

echo "===== HOMEPAGE ====="
curl -fsS https://sarembok.com/ -o /tmp/sarembok-live.html
wc -c /tmp/sarembok-live.html

echo

echo "===== CAPABILITY FABRIC ASSETS ====="
grep -q 'sarembok-capability-fabric.css' /tmp/sarembok-live.html
grep -q 'sarembok-capability-fabric.js' /tmp/sarembok-live.html
echo "Capability UI assets: PRESENT"

echo

echo "===== TEXT SELECTION GUARD ====="
grep -q 'user-select: text' /tmp/sarembok-live.html
echo "Selection policy: PRESENT"

echo

echo "===== RUNTIME CAPABILITY RPC ====="
python3 - <<'PY'
import json, os, ssl, urllib.request
print("Capability RPC smoke check is performed by the authenticated browser/session path.")
print("Do not print or expose SAREMBOK_AUTH_TOKEN.")
PY

echo

echo "===== DONE ====="
echo "Production deploy and HTTP verification completed."
