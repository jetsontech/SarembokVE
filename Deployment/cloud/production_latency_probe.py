#!/usr/bin/env python3
"""Black-box production probe for the public scoped streaming dialogue path."""
from __future__ import annotations
import asyncio
import json
import statistics
import time
import urllib.request
import websockets

HOST = __import__('os').environ.get('SAREMBOK_PROBE_HOST', 'https://sarembok.com').rstrip('/')
WS = HOST.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws'
PROMPT = __import__('os').environ.get('SAREMBOK_PROBE_PROMPT', 'Respond with exactly: SAREMBOK LATENCY PROBE OK')
SAMPLES = max(1, int(__import__('os').environ.get('SAREMBOK_PROBE_SAMPLES', '3')))
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36'

def session():
    started = time.perf_counter()
    req = urllib.request.Request(HOST + '/session', headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode())
    return body, (time.perf_counter() - started) * 1000

async def one(token, i):
    started = time.perf_counter()
    async with websockets.connect(WS, open_timeout=15, close_timeout=5, ping_interval=20, ping_timeout=20, compression=None) as ws:
        connected = (time.perf_counter() - started) * 1000
        request_id = f'probe-{i}'
        payload = {'jsonrpc': '2.0', 'id': request_id, 'method': 'SarembokChat', 'params': {'sessionToken': token, 'message': PROMPT, 'sessionId': f'latency-probe-{i}', 'stream': True}}
        await ws.send(json.dumps(payload, separators=(',', ':')))
        first_delta_ms = None
        text_parts = []
        final = None
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=45)
            data = json.loads(raw)
            if data.get('method') == 'SarembokChat.delta' and (data.get('params') or {}).get('id') == request_id:
                if first_delta_ms is None:
                    first_delta_ms = (time.perf_counter() - started) * 1000
                text_parts.append(str((data.get('params') or {}).get('text') or ''))
                continue
            if data.get('id') == request_id:
                final = data
                break
        total = (time.perf_counter() - started) * 1000
    result = (final or {}).get('result', {})
    meta = result.get('metadata') or {}
    return {'total_ms': round(total, 1), 'ws_connect_ms': round(connected, 1), 'ttft_client_ms': round(first_delta_ms, 1) if first_delta_ms is not None else None, 'ttft_server_ms': meta.get('ttft_ms'), 'provider_ms': meta.get('latency_ms'), 'provider': meta.get('provider'), 'model': meta.get('model'), 'api': meta.get('provider_api'), 'streamed': meta.get('streamed'), 'response': result.get('response', '')[:100], 'delta_chars': len(''.join(text_parts))}

async def main():
    s, session_ms = session()
    token = s['sessionToken']
    print(json.dumps({'session_ms': round(session_ms, 1), 'scope': s.get('scope'), 'expiresIn': s.get('expiresIn')}, indent=2))
    rows = []
    for i in range(SAMPLES):
        row = await one(token, i)
        rows.append(row)
        print(json.dumps(row))
    totals = [r['total_ms'] for r in rows]
    ttfts = [r['ttft_client_ms'] for r in rows if isinstance(r['ttft_client_ms'], (int, float))]
    providers = [r['provider_ms'] for r in rows if isinstance(r['provider_ms'], (int, float))]
    print(json.dumps({'samples': len(rows), 'total_p50_ms': round(statistics.median(totals), 1), 'total_max_ms': round(max(totals), 1), 'ttft_client_p50_ms': round(statistics.median(ttfts), 1) if ttfts else None, 'ttft_client_max_ms': round(max(ttfts), 1) if ttfts else None, 'provider_p50_ms': round(statistics.median(providers), 1) if providers else None, 'provider_max_ms': round(max(providers), 1) if providers else None}, indent=2))
    if any('SAREMBOK LATENCY PROBE OK' not in r['response'] for r in rows): raise SystemExit('probe response mismatch')

if __name__ == '__main__':
    asyncio.run(main())
