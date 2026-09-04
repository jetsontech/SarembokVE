from pathlib import Path

p = Path("Deployment/cloud/server.py")
s = p.read_text()

s = s.replace(
    'LLM_PROVIDER_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "10")))',
    'LLM_PROVIDER_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_PROVIDER_TIMEOUT_SECONDS", "10")))\nLLM_TOTAL_TIMEOUT_SECONDS = max(5, int(os.getenv("SAREMBOK_LLM_TOTAL_TIMEOUT_SECONDS", "15")))',
    1,
)

s = s.replace(
    'gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")',
    'gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")',
    1,
)
s = s.replace(
    'providers.append(("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}", gemini_key, gemini_model))',
    'providers.append(("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent", gemini_key, gemini_model))',
    1,
)

old = '''    reply = None
    source = None
    model = None
    for name, url, key, mdl in providers:
        try:
            if name == "Gemini":
                data = {"contents": [{"parts": [{"text": system_prompt + "\\n\\nUser: " + prompt_clean}]}]}
                headers = {"Content-Type": "application/json"}
            else:
                data = {"model": mdl, "messages": messages, "max_tokens": 800, "temperature": 0.7}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
                if name == "OpenRouter":
                    headers.update({"HTTP-Referer": "https://sarembok.com", "X-Title": "Sarembok VE"})
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=LLM_PROVIDER_TIMEOUT_SECONDS) as r:
                payload = json.loads(r.read().decode("utf-8"))
            reply = (payload["candidates"][0]["content"]["parts"][0]["text"] if name == "Gemini" else payload["choices"][0]["message"]["content"]).strip()
            source = name
            model = mdl
            break
        except Exception as exc:
            LOG.warning("LLM provider %s failed; trying next: %s", name, exc)'''
new = '''    reply = None
    source = None
    model = None
    provider_deadline = time.monotonic() + LLM_TOTAL_TIMEOUT_SECONDS
    for name, url, key, mdl in providers:
        remaining = provider_deadline - time.monotonic()
        if remaining <= 0:
            LOG.warning("LLM total timeout reached before provider %s", name)
            break
        try:
            if name == "Gemini":
                data = {"contents": [{"role": "user", "parts": [{"text": system_prompt + "\\n\\nUser: " + prompt_clean}]}]}
                headers = {"Content-Type": "application/json", "x-goog-api-key": key}
            else:
                data = {"model": mdl, "messages": messages, "max_tokens": 800, "temperature": 0.7}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
                if name == "OpenRouter":
                    headers.update({"HTTP-Referer": "https://sarembok.com", "X-Title": "Sarembok VE"})
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            timeout = min(LLM_PROVIDER_TIMEOUT_SECONDS, max(1, remaining))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
            reply = (payload["candidates"][0]["content"]["parts"][0]["text"] if name == "Gemini" else payload["choices"][0]["message"]["content"]).strip()
            source = name
            model = mdl
            break
        except Exception as exc:
            LOG.warning("LLM provider %s failed; trying next: %s", name, exc)'''
if old not in s:
    raise SystemExit("provider block not found")
s = s.replace(old, new, 1)

old = '            "llmConfigured": bool(os.getenv("OPENAI_API_KEY") or os.getenv("SAREMBOK_AUTH_TOKEN", "").startswith("sk-")),'
new = '''            "llmConfigured": bool(
                os.getenv("OPENAI_API_KEY")
                or os.getenv("OPENROUTER_API_KEY")
                or os.getenv("GROQ_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("LLM_ENDPOINT_URL")
            ),'''
if old not in s:
    raise SystemExit("llmConfigured block not found")
s = s.replace(old, new, 1)

old = '                    result = dispatch(method, params)'
new = '''                    # Keep synchronous SQLite/provider I/O off the asyncio event loop.
                    result = await asyncio.to_thread(dispatch, method, params)'''
if old not in s:
    raise SystemExit("dispatch call not found")
s = s.replace(old, new, 1)

p.write_text(s)

compose = Path("Deployment/cloud/compose.production.yaml")
if compose.exists():
    c = compose.read_text()
    needle = '      GEMINI_API_KEY: ${GEMINI_API_KEY:-}\\n'
    if needle in c and '      GEMINI_MODEL:' not in c:
        c = c.replace(needle, needle + '      GEMINI_MODEL: ${GEMINI_MODEL:-gemini-3.8-flash}\\n', 1)
        compose.write_text(c)
