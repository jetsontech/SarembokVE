from pathlib import Path

p = Path("Deployment/cloud/server.py")
s = p.read_text()
s = s.replace(
    'LLM_PROVIDER_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "10")))',
    'LLM_PROVIDER_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "20")))',
)
s = s.replace(
    'LLM_TOTAL_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS", "15")))',
    'LLM_TOTAL_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS", "30")))',
)
s = s.replace('import urllib.request\n', 'import urllib.request\nimport urllib.error\n')
old = '''            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)\n            timeout = min(LLM_PROVIDER_TIMEOUT_SECONDS, max(1, remaining))\n            with urllib.request.urlopen(req, timeout=timeout) as r:\n                payload = json.loads(r.read().decode("utf-8"))\n            reply = (payload["candidates"][0]["content"]["parts"][0]["text"] if name == "Gemini" else payload["choices"][0]["message"]["content"]).strip()\n'''
new = '''            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)\n            timeout = min(LLM_PROVIDER_TIMEOUT_SECONDS, max(1, remaining))\n            attempts = 2 if name == "Gemini" else 1\n            payload = None\n            for attempt in range(attempts):\n                try:\n                    with urllib.request.urlopen(req, timeout=timeout) as r:\n                        payload = json.loads(r.read().decode("utf-8"))\n                    break\n                except urllib.error.HTTPError as http_exc:\n                    if name != "Gemini" or http_exc.code not in (429, 500, 502, 503, 504) or attempt + 1 >= attempts:\n                        raise\n                    retry_delay = min(2.0, 0.75 * (2 ** attempt))\n                    remaining = provider_deadline - time.monotonic()\n                    if remaining <= retry_delay + 1:\n                        raise\n                    LOG.warning("Gemini returned HTTP %s; retrying once after %.2fs", http_exc.code, retry_delay)\n                    time.sleep(retry_delay)\n                    remaining = provider_deadline - time.monotonic()\n                    timeout = min(LLM_PROVIDER_TIMEOUT_SECONDS, max(1, remaining))\n            if payload is None:\n                raise RuntimeError(f"{name} returned no payload")\n            reply = (payload["candidates"][0]["content"]["parts"][0]["text"] if name == "Gemini" else payload["choices"][0]["message"]["content"]).strip()\n'''
if old not in s:
    raise SystemExit("expected Gemini provider block not found")
s = s.replace(old, new)
p.write_text(s)
