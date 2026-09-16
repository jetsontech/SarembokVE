#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
HOST="${SAREMBOK_PUBLIC_HOST:-sarembok.com}"
BASE="https://${HOST}"

python3 - <<'PY'
import json, os, ssl, sys, urllib.request
try:
    import websockets
except Exception as exc:
    raise SystemExit(f'websockets package unavailable: {exc}')

base='https://' + os.getenv('SAREMBOK_PUBLIC_HOST','sarembok.com')
with urllib.request.urlopen(base + '/session', timeout=15) as response:
    data=json.loads(response.read().decode())
token=data.get('sessionToken')
if not token:
    raise SystemExit('FAIL: /session returned no sessionToken')
print('PASS  browser session issued')

async def main():
    uri='wss://' + os.getenv('SAREMBOK_PUBLIC_HOST','sarembok.com') + '/ws'
    async with websockets.connect(uri, origin=base, max_size=2*1024*1024, open_timeout=10) as ws:
        async def rpc(rid, method, params=None):
            payload={'jsonrpc':'2.0','id':rid,'method':method,'params':dict(params or {}, sessionToken=token)}
            await ws.send(json.dumps(payload))
            while True:
                msg=json.loads(await ws.recv())
                if msg.get('id') == rid:
                    return msg

        runtime=await rpc('e2e-runtime','GetRuntimeInfo')
        if 'result' not in runtime: raise SystemExit(f'FAIL: GetRuntimeInfo: {runtime}')
        print('PASS  authenticated GetRuntimeInfo')

        workers=await rpc('e2e-workers','ListWorkers')
        if 'result' not in workers: raise SystemExit(f'FAIL: ListWorkers: {workers}')
        print('PASS  authenticated ListWorkers')

        admin=await rpc('e2e-admin','AdminExecuteDirective', {'directive':'noop'})
        if admin.get('result',{}).get('metadata',{}).get('role') == 'USER':
            raise SystemExit('FAIL: USER session gained ADMIN role')
        if 'error' not in admin:
            raise SystemExit(f'FAIL: USER admin directive was not denied: {admin}')
        print('PASS  USER denied admin directive')

        fallback=await rpc('e2e-fallback','VerifyAdminPasscode', {'passcode':'joc'})
        if 'result' in fallback:
            raise SystemExit('FAIL: historical hard-coded admin passcode remains accepted')
        print('PASS  historical admin fallback rejected')

        chat=await rpc('e2e-chat','SarembokChat', {'prompt':'Return exactly the word READY.', 'stream':False})
        if 'result' not in chat:
            raise SystemExit(f'FAIL: SarembokChat: {chat}')
        print('PASS  authenticated SarembokChat')

import asyncio
asyncio.run(main())
PY

printf 'PASS  public session/WebSocket/chat acceptance\n'
printf '\n===== FRONTIER E2E RESULT =====\n'
printf 'FRONTIER E2E: PASS\n'
