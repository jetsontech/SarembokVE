#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
FAIL=0
pass(){ printf 'PASS  %s\n' "$1"; }
fail(){ printf 'FAIL  %s\n' "$1"; FAIL=1; }
warn(){ printf 'WARN  %s\n' "$1"; }

printf '\n===== SAREMBOK FRONTIER PRODUCTION GATE =====\n'

grep -RniE 'ADMIN_PASSCODE.*or.*"(joc|sarembok2026)"|"joc"|"sarembok2026"' Deployment/cloud/server.py >/dev/null 2>&1 && fail 'hard-coded administrative fallback still present' || pass 'no hard-coded administrative fallback in server.py'
[ -f Deployment/cloud/production_guard_v2.py ] && pass 'production guard present' || fail 'production guard missing'
[ -f Deployment/cloud/production_entrypoint.py ] && pass 'production entrypoint present' || fail 'production entrypoint missing'
[ -f Deployment/cloud/bootstrap_frontier_secrets.sh ] && pass 'secret bootstrap present' || fail 'secret bootstrap missing'
[ -f Deployment/cloud/backup_database.sh ] && pass 'database backup procedure present' || fail 'database backup procedure missing'
[ -f Deployment/cloud/orchestration_contract.py ] && pass 'orchestration contract present' || fail 'orchestration contract missing'

python3 -m compileall -q Deployment/cloud || fail 'python compileall'
[ "$FAIL" -eq 0 ] && pass 'python compileall'

python3 Deployment/cloud/test_frontier_controls.py || fail 'frontier unit tests'
[ "$FAIL" -eq 0 ] && pass 'frontier unit tests'

bash Deployment/cloud/verify_production.sh || fail 'base production verification'

if docker ps --format '{{.Names}}' | grep -Fxq sarembok-runtime; then
  integrity="$(docker exec sarembok-runtime python - <<'PY'
import sqlite3
p='/data/sarembok_cloud.db'
with sqlite3.connect(p) as db:
    print(db.execute('PRAGMA integrity_check').fetchone()[0])
PY
)"
  [ "$integrity" = "ok" ] && pass 'runtime SQLite integrity' || fail "runtime SQLite integrity: $integrity"

  docker exec sarembok-runtime python - <<'PY' || exit 1
import os
required = [
 'SAREMBOK_AUTH_TOKEN','SAREMBOK_ADMIN_TOKEN','SAREMBOK_MASTER_TOKEN',
 'SAREMBOK_WORKER_ENROLLMENT_TOKEN','SAREMBOK_ADMIN_PASSCODE'
]
missing=[k for k in required if not os.getenv(k,'').strip()]
if missing:
    raise SystemExit('missing production secret(s): '+','.join(missing))
print('production secret configuration: present')
PY
  pass 'production secrets loaded'
else
  warn 'runtime container not active; container-local checks skipped'
fi

printf '\n===== RESULT =====\n'
if [ "$FAIL" -eq 0 ]; then
  printf 'FRONTIER PRODUCTION GATE: PASS\n'
else
  printf 'FRONTIER PRODUCTION GATE: FAIL\n'
  exit 1
fi
