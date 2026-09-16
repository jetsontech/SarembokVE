#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
FAIL=0
pass(){ printf 'PASS  %s\n' "$1"; }
fail(){ printf 'FAIL  %s\n' "$1"; FAIL=1; }
warn(){ printf 'WARN  %s\n' "$1"; }
C=(docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml -f Deployment/cloud/compose.frontier.yaml)

printf '\n===== SAREMBOK FRONTIER PRODUCTION VERIFICATION =====\n'
"${C[@]}" config >/dev/null && pass 'frontier compose configuration valid' || fail 'frontier compose configuration invalid'

[ "$(git branch --show-current)" = "main" ] && pass 'branch main' || fail 'not on main'
git diff --quiet && git diff --cached --quiet && pass 'working tree clean' || fail 'working tree has changes'

python3 -m compileall -q Deployment/cloud && pass 'python compileall' || fail 'python compileall'
python3 -m unittest Deployment/cloud/test_frontier_controls.py && pass 'frontier control tests' || fail 'frontier control tests'

if docker ps --format '{{.Names}}' | grep -Fxq sarembok-runtime; then
  cmd="$(docker inspect -f '{{join .Config.Cmd " "}}' sarembok-runtime 2>/dev/null || true)"
  printf '%s\n' "$cmd" | grep -Fq '/app/production_entrypoint.py' && pass 'runtime uses production entrypoint' || fail "runtime command is not frontier entrypoint: $cmd"

  for key in SAREMBOK_AUTH_TOKEN SAREMBOK_ADMIN_TOKEN SAREMBOK_MASTER_TOKEN SAREMBOK_WORKER_ENROLLMENT_TOKEN SAREMBOK_ADMIN_PASSCODE; do
    value="$(docker exec sarembok-runtime /bin/sh -c "[ -n \"\${$key:-}\" ] && printf yes || printf no" 2>/dev/null || true)"
    [ "$value" = yes ] && pass "runtime secret configured: $key" || fail "runtime secret missing: $key"
  done

  integrity="$(docker exec sarembok-runtime python - <<'PY'
import sqlite3
with sqlite3.connect('/data/sarembok_cloud.db') as db: print(db.execute('PRAGMA integrity_check').fetchone()[0])
PY
)"
  [ "$integrity" = ok ] && pass 'SQLite integrity' || fail "SQLite integrity: $integrity"
else
  fail 'sarembok-runtime container missing'
fi

bash Deployment/cloud/verify_production.sh || fail 'base production verification'

printf '\n===== RESULT =====\n'
[ "$FAIL" -eq 0 ] && printf 'FRONTIER PRODUCTION GATE: PASS\n' || { printf 'FRONTIER PRODUCTION GATE: FAIL\n'; exit 1; }
