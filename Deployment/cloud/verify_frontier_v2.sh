#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
FAIL=0
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
pass(){ printf 'PASS  %s\n' "$1"; }
fail(){ printf 'FAIL  %s\n' "$1"; FAIL=1; }
C=(docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml -f Deployment/cloud/compose.frontier_final.yaml)

printf '\n===== SAREMBOKVE FRONTIER PRODUCTION VERIFICATION =====\n'
printf 'VERIFIER: frontier_v2_diagnostic_20260916\n'
printf 'VERIFIER_COMMIT: %s\n' "$(git rev-parse HEAD)"
printf 'VERIFIER_FILE_SHA256: %s\n' "$(sha256sum "$ROOT/Deployment/cloud/verify_frontier_v2.sh" | awk '{print $1}')"

if python3 Deployment/cloud/frontier_release_gate.py >"$TMP" 2>&1; then
    cat "$TMP"
    pass 'frontier static gate'
else
    cat "$TMP"
    fail 'frontier static gate'
fi
"${C[@]}" config >/dev/null && pass 'frontier compose configuration valid' || fail 'frontier compose configuration invalid'

[ "$(git branch --show-current)" = "main" ] && pass 'branch main' || fail 'not on main'
if git diff --quiet && git diff --cached --quiet; then
    pass 'working tree clean'
else
    fail 'working tree has changes'
    git status --short || true
fi

python3 -m compileall -q Deployment/cloud && pass 'python compileall' || fail 'python compileall'
PYTHONPATH="$ROOT/Deployment/cloud:${PYTHONPATH:-}" python3 -m unittest Deployment/cloud/test_frontier_controls.py && pass 'frontier control tests' || fail 'frontier control tests'

if docker ps --format '{{.Names}}' | grep -Fxq sarembok-runtime; then
  cmd="$(docker inspect -f '{{join .Config.Cmd " "}}' sarembok-runtime 2>/dev/null || true)"
  printf '%s\n' "$cmd" | grep -Fq '/app/production_entrypoint_frontier.py' && pass 'runtime uses frontier production boundary v5' || fail "runtime command is not frontier v5: $cmd"

  for key in SAREMBOK_AUTH_TOKEN SAREMBOK_ADMIN_TOKEN SAREMBOK_MASTER_TOKEN SAREMBOK_WORKER_ENROLLMENT_TOKEN SAREMBOK_WORKER_TOKEN_HASH_SALT SAREMBOK_ADMIN_PASSCODE; do
    value="$(docker exec sarembok-runtime /bin/sh -c "[ -n \"\${$key:-}\" ] && printf yes || printf no" 2>/dev/null || true)"
    [ "$value" = yes ] && pass "runtime secret configured: $key" || fail "runtime secret missing: $key"
  done

  integrity=""
  integrity_error=""
  for attempt in 1 2 3 4 5; do
    result="$(docker exec sarembok-runtime python -c 'import sqlite3; db=sqlite3.connect("file:/data/sarembok_cloud.db?mode=ro", uri=True, timeout=30); db.execute("PRAGMA busy_timeout=30000"); print(db.execute("PRAGMA integrity_check").fetchone()[0]); db.close()' 2>&1 || true)"
    if [ "$result" = ok ]; then
      integrity=ok
      break
    fi
    integrity_error="$result"
    sleep 1
  done
  [ "$integrity" = ok ] && pass 'SQLite integrity' || fail "SQLite integrity: ${integrity_error:-unavailable}"

  worker_rows="$(docker exec sarembok-runtime python - <<'PY'
import sqlite3
with sqlite3.connect('/data/sarembok_cloud.db') as db:
    ids=[r[0] for r in db.execute('SELECT worker_id FROM workers').fetchall()]
print('\n'.join(ids))
PY
)"
  if printf '%s\n' "$worker_rows" | grep -Eq '(^|/)(sarembok-edge-frontier-01|worker-gpu-|worker-edge-|worker-scale-)'; then
    fail 'synthetic worker identity remains in live registry'
  else
    pass 'no known synthetic worker identity in live registry'
  fi
else
  fail 'sarembok-runtime container missing'
fi

if bash Deployment/cloud/verify_production.sh; then
    :
else
    fail 'base production verification'
fi

printf '\n===== RESULT =====\n'
if [ "$FAIL" -eq 0 ]; then
    printf 'FRONTIER PRODUCTION GATE: PASS\n'
else
    printf 'FRONTIER PRODUCTION GATE: FAIL\n'
    exit 1
fi
