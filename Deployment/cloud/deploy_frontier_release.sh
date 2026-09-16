#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
ENV_FILE="Deployment/cloud/.env"
C=(docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml -f Deployment/cloud/compose.frontier_final.yaml)

printf '\n===== SAREMBOKVE FRONTIER RELEASE DEPLOY =====\n'
git fetch origin
git checkout main
git reset --hard origin/main
mkdir -p Deployment/cloud
[ -f "$ENV_FILE" ] || touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
command -v openssl >/dev/null 2>&1 || { echo 'ERROR: openssl required'; exit 1; }
secret(){ openssl rand -hex 32; }
passcode(){ openssl rand -hex 16; }
set_if_missing(){ grep -qE "^$1=" "$ENV_FILE" || printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"; }
set_if_missing SAREMBOK_AUTH_TOKEN "$(secret)"
set_if_missing SAREMBOK_ADMIN_TOKEN "$(secret)"
set_if_missing SAREMBOK_MASTER_TOKEN "$(secret)"
set_if_missing SAREMBOK_WORKER_ENROLLMENT_TOKEN "$(secret)"
set_if_missing SAREMBOK_WORKER_TOKEN_HASH_SALT "$(secret)"
set_if_missing SAREMBOK_ADMIN_PASSCODE "$(passcode)"
set_if_missing SAREMBOK_PUBLIC_HOST "sarembok.com"
set_if_missing SAREMBOK_REQUIRE_ORIGIN "true"
set_if_missing SAREMBOK_ALLOW_ORIGINLESS_LOCAL "false"
set_if_missing SAREMBOK_RATE_LIMIT_PER_IP "120"
set_if_missing SAREMBOK_RATE_LIMIT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_RATE_LIMIT_PER_SUBJECT "180"
set_if_missing SAREMBOK_RATE_LIMIT_SUBJECT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_IDEMPOTENCY_TTL_SECONDS "300"
chmod 600 "$ENV_FILE"

# Export only for this process tree so the live acceptance scripts can verify
# the same generated credentials that Compose injects into the runtime.
set -a
. "$ENV_FILE"
set +a

"${C[@]}" config >/dev/null
"${C[@]}" build --pull sarembok-runtime sarembok-browser sarembok-edge
"${C[@]}" up -d --force-recreate
sleep 12

bash Deployment/cloud/verify_frontier_v2.sh
bash Deployment/cloud/verify_frontier_e2e.sh
bash Deployment/cloud/backup_database.sh

printf '\n===== RELEASE RESULT =====\n'
printf 'SAREMBOKVE FRONTIER RELEASE: PASS\n'
printf 'COMMIT: %s\n' "$(git rev-parse HEAD)"
printf 'PUBLIC: https://%s\n' "${SAREMBOK_PUBLIC_HOST:-sarembok.com}"
printf 'Cockpit UI: preserved\n'
printf 'Admin fallback: disabled at production boundary\n'
printf 'Worker enrollment: authenticated and token-backed\n'
printf 'Execution ledger: durable\n'
printf 'Idempotency ledger: durable\n'
printf 'Origin/rate controls: enabled\n'
printf 'SQLite backup: verified\n'
