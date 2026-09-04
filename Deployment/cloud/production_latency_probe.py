#!/usr/bin/env python3
"""Black-box production probe for the public scoped browser session path."""
from __future__ import annotations
import asyncio
import json
import statistics
import time
import urllib.request
import urllib.parse

import websockets

HOST = __import__('os').environ.get('SAREMBOK_PROBE_HOST', 'https://sarembok.com').rstrip('/')
WS = HOST.replace('https://', 'wss://').replace('http://', 'ws://')
PROMPT = __import__('os').environ.get('SAREMBOK_PROBE_PROMPT', 'Respond with exactly: SAREMBOK LATENCY PROBE OK')
SAMPLES = max(1, int(__import__('os').environ.get('SAREMBOK_PROBE_SAMPLES', '3')))

def session():
    started=time.perf_counter()
    with urllib.request.urlopen(HOST + '/session', timeout=15) as r:
        body=json.loads(r.read().decode())
    return body, (time.perf_counter()-started)*1000

async def one(token, i):
    started=time.perf_counter()
    async with websockets.connect(WS, open_timeout=15, close_timeout=5, ping_interval=20, ping_timeout=20, compression=None) as ws:
        connected=(time.perf_counter()-started)*1000
        payload={'jsonrpc':'2.0','id':f'probe-{i}','method':'SarembokChat','params':{'sessionToken':token,'prompt':PROMPT,'sessionId':f'latency-probe-{i}'}}
        sent=time.perf_counter()
        await ws.send(json.dumps(payload,separators=(',',':')))
        raw=await asyncio.wait_for(ws.recv(), timeout=45)
        total=(time.perf_counter()-started)*1000
    result=json.loads(raw).get('result',{})
    meta=result.get('metadata') or {}
    return {'total_ms':round(total,1),'ws_connect_ms':round(connected,1),'provider_ms':meta.get('latency_ms'),'provider':meta.get('provider'),'model':meta.get('model'),'api':meta.get('provider_api'),'response':result.get('response','')[:100]}

async def main():
    s, session_ms=session()
    token=s['sessionToken']
    print(json.dumps({'session_ms':round(session_ms,1),'scope':s.get('scope'),'expiresIn':s.get('expiresIn')},indent=2))
    rows=[]
    for i in range(SAMPLES):
        row=await one(token,i)
        rows.append(row)
        print(json.dumps(row))
    totals=[r['total_ms'] for r in rows]
    providers=[r['provider_ms'] for r in rows if isinstance(r['provider_ms'],(int,float))]
    print(json.dumps({'samples':len(rows),'total_p50_ms':round(statistics.median(totals),1),'total_max_ms':round(max(totals),1),'provider_p50_ms':round(statistics.median(providers),1) if providers else None,'provider_max_ms':round(max(providers),1) if providers else None},indent=2))
    if any('SAREMBOK LATENCY PROBE OK' not in r['response'] for r in rows):
        raise SystemExit('probe response mismatch')

if __name__ == '__main__':
    asyncio.run(main())
