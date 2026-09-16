#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml -f Deployment/cloud/compose.frontier.yaml)
ENV_FILE="Deployment/cloud/.env"

mkdir -p Deployment/cloud
chmod 700 Deployment/cloud
[ -f "$ENV_FILE" ] || touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
command -v openssl >/dev/null 2>&1 || { echo 'ERROR: openssl is required'; exit 1; }

secret(){ openssl rand -hex 32; }
passcode(){ openssl rand -hex 16; }
set_if_missing(){
  local key="$1" value="$2"
  grep -qE "^${key}=" "$ENV_FILE" || printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

set_if_missing SAREMBOK_AUTH_TOKEN "$(secret)"
set_if_missing SAREMBOK_ADMIN_TOKEN "$(secret)"
set_if_missing SAREMBOK_MASTER_TOKEN "$(secret)"
set_if_missing SAREMBOK_WORKER_ENROLLMENT_TOKEN "$(secret)"
set_if_missing SAREMBOK_ADMIN_PASSCODE "$(passcode)"
set_if_missing SAREMBOK_PUBLIC_HOST "sarembok.com"
set_if_missing SAREMBOK_REQUIRE_ORIGIN "true"
set_if_missing SAREMBOK_ALLOW_ORIGINLESS_LOCAL "true"
set_if_missing SAREMBOK_RATE_LIMIT_PER_IP "120"
set_if_missing SAREMBOK_RATE_LIMIT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_RATE_LIMIT_PER_SUBJECT "180"
set_if_missing SAREMBOK_RATE_LIMIT_SUBJECT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_IDEMPOTENCY_TTL_SECONDS "300"
chmod 600 "$ENV_FILE"

"${COMPOSE[@]} config >/dev/null
"${COMPOSE[@]} build sarembok-runtime sarembok-edge sarembok-browser
"${COMPOSE[@]} up -d --force-recreate
sleep 10

if command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 15 https://sarembok.com/health >/dev/null
fi

bash Deployment/cloud/verify_production.sh
python3 -m unittest Deployment/cloud/test_frontier_controls.py
bash Deployment/cloud/backup_database.sh

printf '\nFRONTIER DEPLOYMENT COMPLETE\n'
