#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/Deployment/cloud"
HOST="${SAREMBOK_PUBLIC_HOST:-sarembok.com}"
BASE="https://${HOST}"
FAIL=0

pass(){ printf 'PASS  %s\n' "$1"; }
warn(){ printf 'WARN  %s\n' "$1"; }
fail(){ printf 'FAIL  %s\n' "$1"; FAIL=1; }

printf '\n===== SAREMBOK PRODUCTION VERIFICATION =====\n'
printf 'ROOT: %s\nHOST: %s\n' "$ROOT" "$HOST"

printf '\n===== SOURCE =====\n'
SOURCE_CONTENT_DIRTY=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  ABS_PATH="$ROOT/$path"
  if [ ! -f "$ABS_PATH" ]; then
    SOURCE_CONTENT_DIRTY=1
    fail "tracked source file missing: $path"
    continue
  fi
  WORKTREE_BLOB="$(git hash-object -- "$ABS_PATH")"
  HEAD_BLOB="$(git rev-parse "HEAD:$path" 2>/dev/null || true)"
  if [ -z "$HEAD_BLOB" ] || [ "$WORKTREE_BLOB" != "$HEAD_BLOB" ]; then
    SOURCE_CONTENT_DIRTY=1
    fail "tracked source content changed: $path"
  fi
done < <(git diff --name-only; git diff --cached --name-only | sort -u)
[ "$SOURCE_CONTENT_DIRTY" -eq 0 ] && pass 'tracked source content clean'
BRANCH="$(git branch --show-current)"
[ "$BRANCH" = main ] && pass 'branch main' || fail "unexpected branch: $BRANCH"

printf '\n===== COMPOSE =====\n'
docker compose -f compose.yaml -f compose.production.yaml config >/dev/null && pass 'compose configuration valid' || fail 'compose configuration invalid'
SERVICES="$(docker compose -f compose.yaml -f compose.production.yaml config --services)"
for svc in sarembok-runtime sarembok-browser sarembok-edge; do
  printf '%s\n' "$SERVICES" | grep -Fxq "$svc" && pass "declared service: $svc" || fail "missing declared service: $svc"
done
printf '%s\n' "$SERVICES" | grep -Eq '^sarembok-worker(-|$)' || warn 'no worker container service is declared by the current production compose; external/registered workers are runtime inventory, not compose services'

printf '\n===== CONTAINERS =====\n'
for svc in sarembok-runtime sarembok-browser sarembok-edge; do
  cid="$(docker compose -f compose.yaml -f compose.production.yaml ps -q "$svc" || true)"
  [ -n "$cid" ] && pass "$svc container exists" || fail "$svc container missing"
done
RUNTIME_STATUS="$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' sarembok-runtime 2>/dev/null || true)"
printf '%s\n' "$RUNTIME_STATUS" | grep -q 'running healthy' && pass 'runtime running and healthy' || fail "runtime health: ${RUNTIME_STATUS:-missing}"

printf '\n===== RUNTIME WORKER INVENTORY =====\n'
WORKER_JSON="$(docker exec sarembok-runtime python -c 'import json,sqlite3; con=sqlite3.connect("/data/sarembok_cloud.db"); con.row_factory=sqlite3.Row; print(json.dumps([dict(r) for r in con.execute("SELECT worker_id,status,last_heartbeat,gpu_vendor,gpu_model FROM workers ORDER BY worker_id").fetchall()]))' 2>&1 || true)"
if python3 - "$WORKER_JSON" <<'PY'
import json,sys
try: data=json.loads(sys.argv[1])
except Exception as exc:
 print(f"FAIL: worker inventory response was not valid JSON: {exc}"); raise SystemExit(1)
if isinstance(data,dict) and "error" in data:
 print(f"FAIL: worker inventory unavailable: {data['error']}"); raise SystemExit(1)
rows=data if isinstance(data,list) else []
online=[r for r in rows if str(r.get('status','')).upper() in {'ONLINE','READY','ACTIVE','AVAILABLE'}]
print(f"workers recorded: {len(rows)}")
print(f"workers online/ready/active/available: {len(online)}")
for r in rows: print(f"  {r.get('worker_id')} status={r.get('status')} gpu={r.get('gpu_vendor') or '-'} {r.get('gpu_model') or '-'} heartbeat={r.get('last_heartbeat')}")
if not online: print('WARNING: no active worker is currently registered in the runtime database.')
PY
then
  pass 'runtime worker inventory query'
else
  fail 'runtime worker inventory query failed'
fi

printf '\n===== PUBLIC HTTP =====\n'
HEALTH="$(curl -fsS --max-time 15 "$BASE/health" || true)"
[ "$HEALTH" = OK ] && pass 'public /health = OK' || fail "public /health = ${HEALTH:-unreachable}"
HTML="$(curl -fsS --max-time 15 "$BASE/" || true)"
[ -n "$HTML" ] && pass 'public homepage reachable' || fail 'public homepage unreachable'

printf '\n===== FRONTEND COCKPIT INTEGRITY =====\n'
HTML_FILE="$(mktemp)"
trap 'rm -f "$HTML_FILE"' EXIT
printf '%s' "$HTML" > "$HTML_FILE"
python3 - "$HTML_FILE" <<'PY'
import re,sys
from html.parser import HTMLParser
html=open(sys.argv[1],encoding='utf-8').read()
class P(HTMLParser):
    def __init__(self): super().__init__(); self.in_code=0; self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}: self.in_code += 1
    def handle_endtag(self,tag):
        if tag in {'script','style'}: self.in_code=max(0,self.in_code-1)
    def handle_data(self,data):
        if not self.in_code: self.text.append(data)
p=P(); p.feed(html)
checks={
 'full cockpit dock':'cyber-left-dock' in html,
 'global cockpit input':'global-input-bar' in html,
 'cockpit HUD':'header-hud-group' in html,
 'cockpit view system':'SAREMBOK VE' in html and 'COMPUTE COCKPIT' in html,
}
for name,ok in checks.items():
    if not ok: raise SystemExit(f'ERROR: missing {name}')
visible=' '.join(p.text)
if re.search(r'\baria\b',visible,re.I): raise SystemExit('ERROR: prohibited product word found in visible UI text')
if 'sarembok-simplified.css' in html or 'sarembok-simplified.js' in html:
    raise SystemExit('ERROR: stripped-down simplified frontend still active')
print('full cockpit marker: PASS')
print('global cockpit input marker: PASS')
print('cockpit HUD marker: PASS')
print('visible UI text check: PASS')
PY
if [ $? -eq 0 ]; then pass 'frontend cockpit and visible-text integrity'; else fail 'frontend cockpit and visible-text integrity'; fi

for path in /session; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$path" || true)"
  [ "$code" = 200 ] && pass "$path HTTP 200" || fail "$path HTTP $code"
done

printf '\n===== RESULT =====\n'
if [ "$FAIL" -eq 0 ]; then
  printf 'PRODUCTION VERIFICATION: PASS\n'
else
  printf 'PRODUCTION VERIFICATION: FAIL\n'
  exit 1
fi
