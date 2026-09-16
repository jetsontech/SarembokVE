#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/Deployment/cloud/.env"
mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

rand_secret(){ openssl rand -hex 32; }
rand_passcode(){ openssl rand -base64 27 | tr -dc 'A-Za-z0-9' | head -c 24; }
set_if_missing(){ local key="$1" value="$2"; grep -qE "^${key}=" "$ENV_FILE" || printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"; }

command -v openssl >/dev/null 2>&1 || { echo 'ERROR: openssl is required'; exit 1; }

set_if_missing SAREMBOK_AUTH_TOKEN "$(rand_secret)"
set_if_missing SAREMBOK_ADMIN_TOKEN "$(rand_secret)"
set_if_missing SAREMBOK_MASTER_TOKEN "$(rand_secret)"
set_if_missing SAREMBOK_WORKER_ENROLLMENT_TOKEN "$(rand_secret)"
set_if_missing SAREMBOK_ADMIN_PASSCODE "$(rand_passcode)"
set_if_missing SAREMBOK_PUBLIC_HOST "sarembok.com"
set_if_missing SAREMBOK_REQUIRE_ORIGIN "true"
set_if_missing SAREMBOK_ALLOW_ORIGINLESS_LOCAL "true"
set_if_missing SAREMBOK_RATE_LIMIT_PER_IP "120"
set_if_missing SAREMBOK_RATE_LIMIT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_RATE_LIMIT_PER_SUBJECT "180"
set_if_missing SAREMBOK_RATE_LIMIT_SUBJECT_WINDOW_SECONDS "60"
set_if_missing SAREMBOK_IDEMPOTENCY_TTL_SECONDS "300"

# Keep provider configuration already present; never print secrets.
chmod 600 "$ENV_FILE"
printf 'Frontier production credentials verified/initialized in %s\n' "$ENV_FILE"
printf 'Credentials are intentionally not printed. Protect this file.\n'
