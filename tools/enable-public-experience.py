from pathlib import Path

server = Path('Deployment/cloud/server.py')
text = server.read_text(encoding='utf-8')

# Keep the public surface intentionally small. Internal state APIs remain authenticated.
old = '''PUBLIC_METHODS = {
    "Health",
    "RuntimeInfo",
    "ListWorkers",
    "ListProjects",
    "ListMemories",
    "ListFiles",
    "ListCheckpoints",
    "ListGovernanceApprovals",
    "ListDigitalHumanSessions",
    "ListEvents",
    "QueryCognitiveGraph",
}
'''
new = '''PUBLIC_METHODS = {
    "Health",
    "RuntimeInfo",
}
'''
if old in text:
    text = text.replace(old, new, 1)

old_auth = '''def authenticate(request: dict[str, Any]) -> None:
    if not AUTH_TOKEN:
        return
    params = request.get("params")
    supplied = params.get("authToken") if isinstance(params, dict) else None
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, AUTH_TOKEN):
        raise PermissionError("authentication_required")
'''
new_auth = '''def authenticate(request: dict[str, Any], method: str | None = None) -> None:
    if method in PUBLIC_METHODS:
        return
    if not AUTH_TOKEN:
        return
    params = request.get("params")
    supplied = params.get("authToken") if isinstance(params, dict) else None
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, AUTH_TOKEN):
        raise PermissionError("authentication_required")
'''
if old_auth in text:
    text = text.replace(old_auth, new_auth, 1)

text = text.replace('''    authenticate(request)
    return method, params
''', '''    authenticate(request, method)
    return method, params
''', 1)
text = text.replace('''    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("SAREMBOK_AUTH_TOKEN") or api_key
''', '''    openai_key = os.getenv("OPENAI_API_KEY") or api_key
''', 1)

# Never inject the server authentication secret into browser HTML.
old_injection = '''        elif AUTH_TOKEN:
            token_injection = f'<script>window.__SAREMBOK_DEFAULT_TOKEN__ = "{AUTH_TOKEN}";</script>'
            if "<head>" in html_str:
                html_str = html_str.replace("<head>", f"<head>\n    {token_injection}", 1)
            else:
                html_str = token_injection + html_str
'''
if old_injection not in text:
    if 'window.__SAREMBOK_DEFAULT_TOKEN__' in text:
        raise SystemExit('refusing to leave browser auth-token injection in place')
else:
    text = text.replace(old_injection, '''        # AUTH_TOKEN is server-side only and must never be exposed to the browser.
''', 1)

# Sanitize RuntimeInfo because this method is intentionally public.
start = text.find('    if method == "RuntimeInfo":')
if start >= 0:
    end = text.find('    if method == "ListProjects":', start)
    if end < 0:
        raise SystemExit('RuntimeInfo end marker not found')
    runtime_info = '''    if method == "RuntimeInfo":
        worker_stats = get_worker_status_counts()
        active_agents = store.db.execute("SELECT COUNT(*) FROM agents WHERE status='ONLINE'").fetchone()[0]
        active_sessions = store.db.execute("SELECT COUNT(*) FROM digital_human_sessions WHERE status='ACTIVE'").fetchone()[0]
        return {
            "status": "ONLINE",
            "service": "sarembok-ve-cloud-runtime",
            "uptimeSeconds": int(time.time() - STARTED),
            "storage": "sqlite-wal",
            "registeredWorkers": worker_stats["registeredWorkers"],
            "onlineWorkers": worker_stats["onlineWorkers"],
            "activeAgents": active_agents,
            "activeDigitalHumanSessions": active_sessions,
        }

'''
    text = text[:start] + runtime_info + text[end:]
else:
    raise SystemExit('RuntimeInfo method not found')

server.write_text(text, encoding='utf-8')

html = Path('frontend/index.html')
h = html.read_text(encoding='utf-8')
h = h.replace('''<div class="card-label" style="color:var(--emerald);">● RUNTIME CONNECTED</div>''', '''<div class="card-label" id="runtime-status" style="color:var(--text-muted);">● CONNECTING TO RUNTIME</div>''', 1)
h = h.replace('''<div class="card-val text-cyan" id="metric-mem">SQLite-WAL</div>''', '''<div class="card-val text-cyan" id="metric-mem">—</div>''', 1)
h = h.replace('''<div class="card-val" id="metric-agents">ARIA + 4 Workers</div>''', '''<div class="card-val" id="metric-agents">—</div>''', 1)
h = h.replace('''<div class="card-val text-emerald">sarembok.com</div>''', '''<div class="card-val text-emerald" id="metric-workers">—</div>''', 1)

old_js = '''        function connect() {
            const loc = window.location;
            const proto = loc.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = (loc.hostname === "localhost" || loc.hostname === "127.0.0.1")
                ? "ws://127.0.0.1:9120"
                : `${proto}//${loc.host}/ws`;

            ws = new WebSocket(wsUrl);
            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.id && pending.has(data.id)) {
                        const { res, rej } = pending.get(data.id);
                        pending.delete(data.id);
                        if (data.error) rej(data.error);
                        else res(data.result);
                    }
                } catch(err) {}
            };
            ws.onclose = () => setTimeout(connect, 3000);
        }
'''
new_js = '''        function setRuntimeStatus(online, detail = "") {
            const el = document.getElementById('runtime-status');
            if (!el) return;
            el.textContent = online ? '● RUNTIME ONLINE' : '● RUNTIME OFFLINE';
            el.style.color = online ? 'var(--emerald)' : 'var(--text-muted)';
            if (detail) el.title = detail;
        }

        function applyRuntimeInfo(info) {
            if (!info) return;
            const mem = document.getElementById('metric-mem');
            const agents = document.getElementById('metric-agents');
            const workers = document.getElementById('metric-workers');
            if (mem) mem.textContent = info.storage || '—';
            if (agents) agents.textContent = String(info.activeAgents ?? 0);
            if (workers) workers.textContent = `${info.onlineWorkers ?? 0} / ${info.registeredWorkers ?? 0} workers online`;
        }

        function connect() {
            const loc = window.location;
            const proto = loc.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = (loc.hostname === "localhost" || loc.hostname === "127.0.0.1")
                ? "ws://127.0.0.1:9120"
                : `${proto}//${loc.host}/ws`;

            ws = new WebSocket(wsUrl);
            ws.onopen = async () => {
                setRuntimeStatus(true);
                try {
                    const info = await sendRPC("RuntimeInfo");
                    applyRuntimeInfo(info);
                } catch (err) {
                    setRuntimeStatus(false, 'Runtime RPC unavailable');
                }
            };
            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.id && pending.has(data.id)) {
                        const { res, rej } = pending.get(data.id);
                        pending.delete(data.id);
                        if (data.error) rej(data.error);
                        else res(data.result);
                    }
                } catch(err) {}
            };
            ws.onerror = () => setRuntimeStatus(false, 'WebSocket error');
            ws.onclose = () => {
                setRuntimeStatus(false, 'Connection closed');
                setTimeout(connect, 3000);
            };
        }
'''
if old_js in h:
    h = h.replace(old_js, new_js, 1)

old_catch = '''            } catch(e) {
                aiMsg.innerHTML = `<strong style="color:var(--cyan);">ARIA:</strong> Directive received: "${escapeHtml(txt)}". Memory context reconciled.`;
            }
'''
new_catch = '''            } catch(e) {
                aiMsg.innerHTML = `<strong style="color:#f59e0b;">RUNTIME:</strong> ${escapeHtml(e.message || 'The Sarembok runtime is unavailable. No action was executed.')}`;
            }
'''
if old_catch in h:
    h = h.replace(old_catch, new_catch, 1)

h = h.replace('''<strong style="color:var(--cyan);">ARIA:</strong> System initialized. Ready to execute code synthesis, multi-agent pipelines, memory recall, or research directives.''', '''<strong style="color:var(--cyan);">ARIA:</strong> Runtime connection established when the cloud gateway is available. Commands execute only when the backend confirms execution.''', 1)
html.write_text(h, encoding='utf-8')
