#!/usr/bin/env bash
set -Eeuo pipefail
HOST="${SAREMBOK_PUBLIC_HOST:-sarembok.com}"
BASE="https://${HOST}"

python3 - <<'PY'
import asyncio, json, os, urllib.error, urllib.request
try:
    import websockets
except Exception as exc:
    raise SystemExit(f'websockets package unavailable: {exc}')

base='https://' + os.getenv('SAREMBOK_PUBLIC_HOST','sarembok.com')
with urllib.request.urlopen(base + '/session', timeout=15) as response:
    data=json.loads(response.read().decode())
token=data.get('sessionToken')
if not token: raise SystemExit('FAIL: /session returned no sessionToken')
print('PASS  browser session issued')

try:
    urllib.request.urlopen(base + '/api/chat-sessions', timeout=10)
    raise SystemExit('FAIL: legacy unauthenticated /api endpoint is reachable')
except urllib.error.HTTPError as exc:
    if exc.code != 404: raise SystemExit(f'FAIL: /api/chat-sessions returned HTTP {exc.code}')
print('PASS  legacy /api surface blocked at edge')

async def main():
    uri='wss://' + os.getenv('SAREMBOK_PUBLIC_HOST','sarembok.com') + '/ws'
    async with websockets.connect(uri, origin=base, max_size=2*1024*1024, open_timeout=10) as ws:
        async def rpc(rid, method, params=None, auth=token):
            payload={'jsonrpc':'2.0','id':rid,'method':method,'params':dict(params or {}, sessionToken=auth) if auth is not None else dict(params or {})}
            await ws.send(json.dumps(payload))
            while True:
                msg=json.loads(await ws.recv())
                if msg.get('id') == rid: return msg

        runtime=await rpc('e2e-runtime','GetRuntimeInfo')
        if 'result' not in runtime: raise SystemExit(f'FAIL: GetRuntimeInfo: {runtime}')
        print('PASS  authenticated GetRuntimeInfo')

        workers=await rpc('e2e-workers','ListWorkers')
        if 'result' not in workers: raise SystemExit(f'FAIL: ListWorkers: {workers}')
        print('PASS  authenticated ListWorkers')

        admin=await rpc('e2e-user-admin','AdminExecuteDirective', {'directive':'noop'})
        if 'error' not in admin: raise SystemExit(f'FAIL: USER admin directive was not denied: {admin}')
        print('PASS  USER denied admin directive')

        fallback=await rpc('e2e-fallback','VerifyAdminPasscode', {'passcode':'joc'})
        if 'result' in fallback: raise SystemExit('FAIL: historical hard-coded admin passcode remains accepted')
        print('PASS  historical admin fallback rejected')

        admin_token=os.getenv('SAREMBOK_ADMIN_TOKEN','')
        if not admin_token: raise SystemExit('FAIL: admin token is absent from release environment')
        admin_ok=await rpc('e2e-admin-ok','AdminExecuteDirective', {'directive':'noop'}, auth=admin_token)
        if 'error' in admin_ok: raise SystemExit(f'FAIL: generated admin token cannot authorize admin directive: {admin_ok}')
        print('PASS  generated admin token authorizes typed admin directive')

        key='e2e-idempotency-fixed-key'
        first=await rpc('e2e-idem-1','CreateProject', {'name':'frontier-e2e','idempotencyKey':key}, auth=admin_token)
        second=await rpc('e2e-idem-2','CreateProject', {'name':'frontier-e2e','idempotencyKey':key}, auth=admin_token)
        if 'error' in first or 'result' not in first: raise SystemExit(f'FAIL: idempotency first request: {first}')
        if second.get('result',{}).get('metadata',{}).get('idempotentReplay') is not True: raise SystemExit(f'FAIL: durable idempotency replay marker missing: {second}')
        print('PASS  idempotency replay protected')

        chat=await rpc('e2e-chat','SarembokChat', {'prompt':'Return exactly the word READY.', 'stream':False})
        if 'result' not in chat: raise SystemExit(f'FAIL: SarembokChat: {chat}')
        print('PASS  authenticated SarembokChat')

asyncio.run(main())
PY

printf 'PASS  public session/WebSocket/auth/API lockdown acceptance\n'
printf '\n===== FRONTIER E2E RESULT =====\n'
printf 'FRONTIER E2E: PASS\n'
