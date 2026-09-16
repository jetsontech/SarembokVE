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
printf 'ROOT: %s\nHOST: %s\n\n' "$ROOT" "$HOST"

printf '%s\n' '===== SOURCE ====='
if git diff --quiet && git diff --cached --quiet; then pass 'working tree clean'; else fail 'working tree has uncommitted changes'; fi
BRANCH="$(git branch --show-current)"
[ "$BRANCH" = "main" ] && pass 'branch main' || fail "unexpected branch: $BRANCH"

printf '\n%s\n' '===== COMPOSE ====='
docker compose -f compose.yaml -f compose.production.yaml config >/dev/null && pass 'compose configuration valid' || fail 'compose configuration invalid'
SERVICES="$(docker compose -f compose.yaml -f compose.production.yaml config --services)"
for svc in sarembok-runtime sarembok-browser sarembok-edge; do
  printf '%s\n' "$SERVICES" | grep -Fxq "$svc" && pass "declared service: $svc" || fail "missing declared service: $svc"
done
if printf '%s\n' "$SERVICES" | grep -Eq '^sarembok-worker(-|$)'; then
  pass 'worker service declarations present'
else
  warn 'no worker container service is declared by the current production compose; external/registered workers are runtime inventory, not compose services'
fi

printf '\n%s\n' '===== CONTAINERS ====='
for svc in sarembok-runtime sarembok-browser sarembok-edge; do
  cid="$(docker compose -f compose.yaml -f compose.production.yaml ps -q "$svc" || true)"
  [ -n "$cid" ] && pass "$svc container exists" || fail "$svc container missing"
done
RUNTIME_STATUS="$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' sarembok-runtime 2>/dev/null || true)"
printf '%s\n' "$RUNTIME_STATUS" | grep -q 'running healthy' && pass 'runtime running and healthy' || fail "runtime health: ${RUNTIME_STATUS:-missing}"

printf '\n%s\n' '===== RUNTIME WORKER INVENTORY ====='
WORKER_JSON="$(docker exec sarembok-runtime python - <<'PY'
import json, sqlite3
p='/data/sarembok_cloud.db'
con=sqlite3.connect(p)
con.row_factory=sqlite3.Row
rows=con.execute('SELECT worker_id,status,last_heartbeat,gpu_vendor,gpu_model FROM workers ORDER BY worker_id').fetchall()
print(json.dumps([dict(r) for r in rows]))
PY
)"
python3 - "$WORKER_JSON" <<'PY'
import json, sys
rows=json.loads(sys.argv[1])
online=[r for r in rows if str(r.get('status','')).upper() in {'ONLINE','READY','ACTIVE','AVAILABLE'}]
print(f'workers recorded: {len(rows)}')
print(f'workers online/ready/active/available: {len(online)}')
for r in rows:
    print(f"  {r.get('worker_id')} status={r.get('status')} gpu={r.get('gpu_vendor') or '-'} {r.get('gpu_model') or '-'} heartbeat={r.get('last_heartbeat')}")
if not online:
    print('WARNING: no active worker is currently registered in the runtime database.')
PY

printf '\n%s\n' '===== PUBLIC HTTP ====='
HEALTH="$(curl -fsS --max-time 15 "$BASE/health" || true)"
[ "$HEALTH" = 'OK' ] && pass 'public /health = OK' || fail "public /health = ${HEALTH:-unreachable}"
HTML="$(curl -fsS --max-time 15 "$BASE/" || true)"
[ -n "$HTML" ] && pass 'public homepage reachable' || fail 'public homepage unreachable'

printf '\n%s\n' '===== FRONTEND ASSET INTEGRITY ====='
HTML="$HTML" python3 - <<'PY'
import os, re, sys
from html.parser import HTMLParser

html=os.environ.get('HTML','')
class P(HTMLParser):
    def __init__(self): super().__init__(); self.in_code=0; self.text=[]; self.assets=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in {'script','style'}: self.in_code += 1
        if tag == 'link' and a.get('rel') == 'stylesheet': self.assets.append(('css',a.get('href','')))
        if tag == 'script' and a.get('src'): self.assets.append(('js',a.get('src','')))
    def handle_endtag(self, tag):
        if tag in {'script','style'}: self.in_code=max(0,self.in_code-1)
    def handle_data(self, data):
        if not self.in_code: self.text.append(data)
p=P(); p.feed(html)
css=[u for k,u in p.assets if k=='css' and 'sarembok-simplified.css' in u]
js=[u for k,u in p.assets if k=='js' and 'sarembok-simplified.js' in u]
print('simplified CSS references:', css)
print('simplified JS references:', js)
if len(css) != 1: sys.exit('ERROR: expected exactly one simplified CSS reference')
if len(js) != 1: sys.exit('ERROR: expected exactly one simplified JS reference')
visible=' '.join(p.text)
if re.search(r'\baria\b', visible, re.I): sys.exit('ERROR: prohibited product word found in visible UI text')
print('visible UI text check: PASS')
PY
[ "$?" -eq 0 ] && pass 'frontend asset and visible-text integrity' || FAIL=1

for path in /css/sarembok-simplified.css /js/sarembok-simplified.js /session; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$path" || true)"
  [ "$code" = '200' ] && pass "$path HTTP 200" || fail "$path HTTP $code"
done

printf '\n===== RESULT =====\n'
if [ "$FAIL" -eq 0 ]; then
  printf 'PRODUCTION VERIFICATION: PASS\n'
else
  printf 'PRODUCTION VERIFICATION: FAIL\n'
  exit 1
fi
