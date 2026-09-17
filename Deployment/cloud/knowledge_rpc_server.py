"""Production JSON-RPC entrypoint with streaming dialogue bridge."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import time
import sys

import websockets

from provider_router import reset_stream_callback, set_stream_callback
from runtime_authority import render_markdown as render_runtime_diagnostic
from runtime_authority import snapshot as runtime_authority_snapshot
from runtime_response_composer import (
    build_runtime_context,
    is_capability_query,
    is_identity_query,
    is_limitation_query,
    is_self_state_query,
    render_capabilities,
    render_identity,
    render_limitations,
    render_model_inventory,
)

CLOUD_SERVER_PATH = "/app/server.py"
spec = importlib.util.spec_from_file_location("sarembok_cloud_server", CLOUD_SERVER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cloud server: {CLOUD_SERVER_PATH}")
cloud_server = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cloud_server
spec.loader.exec_module(cloud_server)

sys.path.insert(0, "/app/Runtime")
from sarembok_knowledge_api import KnowledgeRuntimeAPI
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime

knowledge_runtime = PersistentKnowledgeRuntime(cloud_server.DB_PATH)
knowledge_api = KnowledgeRuntimeAPI(knowledge_runtime)
_original_dispatch = cloud_server.dispatch
_original_process_http_request = cloud_server.process_http_request


def _authoritative_snapshot() -> dict:
    if hasattr(cloud_server, "ensure_sovereign_worker"):
        cloud_server.ensure_sovereign_worker()
    cloud_server.evaluate_worker_liveness()
    return runtime_authority_snapshot(
        cloud_server.store,
        cloud_server.PROVIDER_ROUTER,
        cloud_server.STARTED,
    )


def _dispatch_chat_with_authority(params: dict) -> dict:
    snapshot = _authoritative_snapshot()

    prompt = str(
        params.get("prompt")
        or params.get("message")
        or params.get("text")
        or ""
    ).strip()

    # 1. Limitation / architectural boundary questions answered directly by Runtime Authority
    if is_limitation_query(prompt):
        response = render_limitations(snapshot)
        return {
            **snapshot,
            "response": response,
            "audioText": "Sarembok VE operates within defined architectural boundaries: containerized sandbox isolation, strict human-in-the-loop authorization for high-risk actions, and verified ground-truth telemetry.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": cloud_server.build_structured_response(
                response,
                provider="runtime_authority",
                model="runtime-authority",
            ),
            "agentId": "sarembok-prime",
            "timestamp": cloud_server.now(),
        }

    # 2. Capability questions answered directly by Runtime Authority
    if is_capability_query(prompt):
        response = render_capabilities(snapshot)
        return {
            **snapshot,
            "response": response,
            "audioText": "I am Sarembok VE. I can stream media and audio, conduct live two-way voice conversations, retrieve real-time news and intelligence, synthesize code, and orchestrate multi-agent pipelines.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": cloud_server.build_structured_response(
                response,
                provider="runtime_authority",
                model="runtime-authority",
            ),
            "agentId": "sarembok-prime",
            "timestamp": cloud_server.now(),
        }

    # 2. Identity / system architecture questions answered directly by Runtime Authority
    if is_identity_query(prompt):
        response = render_identity(snapshot)
        return {
            **snapshot,
            "response": response,
            "audioText": "I am Sarembok VE, the sovereign computing environment and AI multimodal runtime.",
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": cloud_server.build_structured_response(
                response,
                provider="runtime_authority",
                model="runtime-authority",
            ),
            "agentId": "sarembok-prime",
            "timestamp": cloud_server.now(),
        }

    # 3. Sarembok inventory/state questions that do not require an LLM
    # are answered directly from Runtime Authority.
    inventory_query_markers = (
        "what models are available",
        "what other models",
        "other models",
        "which models are available",
        "which models can i use",
        "what models can i use",
        "what llms are available",
        "what llms can i use",
        "what language models are available",
        "what language models can i use",
        "what models are configured",
        "which models are configured",
        "model availability",
        "available models",
        "configured models",
    )

    prompt_lower = prompt.lower()

    if is_self_state_query(prompt) and any(
        marker in prompt_lower for marker in inventory_query_markers
    ):
        response = render_model_inventory(snapshot)

        return {
            **snapshot,
            "response": response,
            "audioText": response.replace("*", "").replace("`", "").replace("#", "")[:1200],
            "source": "runtime_authority",
            "model": "runtime-authority",
            "action": None,
            "structuredResponse": cloud_server.build_structured_response(
                response,
                provider="runtime_authority",
                model="runtime-authority",
            ),
            "agentId": "sarembok-prime",
            "timestamp": cloud_server.now(),
        }

    # Ordinary dialogue goes directly through the existing cloud
    # dialogue engine and Provider Router. Runtime Authority facts
    # are supplied by the dialogue path itself; no monkey-patching
    # of ProviderRouter.generate() is required here.
    return _original_dispatch("SarembokChat", params)

def _is_runtime_diagnostic(prompt: str) -> bool:
    text = prompt.lower()
    markers = (
        "system diagnostic",
        "runtime diagnostic",
        "registered workers",
        "compute capabilities",
        "persistent memory status",
        "scheduler status",
        "provider currently serving",
    )
    return sum(1 for marker in markers if marker in text) >= 2


def dispatch(method: str, params: dict) -> dict:
    if method == "GetRuntimeInfo":
        return _authoritative_snapshot()
    if method in {"SarembokChat", "Chat", "SarembokDialogue"}:
        prompt = str(params.get("prompt") or params.get("message") or params.get("text") or "").strip()
        if _is_runtime_diagnostic(prompt):
            diagnostic = _authoritative_snapshot()
            response = render_runtime_diagnostic(diagnostic)
            return {
                **diagnostic,
                "response": response,
                "audioText": response.replace("*", "").replace("`", "").replace("#", "")[:1200],
                "source": "runtime_authority",
                "model": "runtime-authority",
                "action": None,
                "structuredResponse": cloud_server.build_structured_response(
                    response,
                    provider="runtime-authority",
                    model="runtime-authority",
                ),
                "agentId": "sarembok-prime",
                "timestamp": cloud_server.now(),
            }

        return _dispatch_chat_with_authority(params)

    if method in KnowledgeRuntimeAPI.METHODS:
        return knowledge_api.dispatch(method, params)
    return _original_dispatch(method, params)


cloud_server.dispatch = dispatch
CHAT_METHODS = {"SarembokChat", "Chat", "SarembokDialogue"}


async def handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    cloud_server.LOG.info("connection_open peer=%s", peer)
    try:
        async for raw in websocket:
            request = None
            token_ctx = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > cloud_server.MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")
                request = json.loads(raw)
                method, params = cloud_server.validate_request(request)
                prompt_for_stream_check = str(
                    params.get("prompt")
                    or params.get("message")
                    or params.get("text")
                    or ""
                ).strip()

                model_identity_query = _is_model_identity_query(prompt_for_stream_check)

                stream_requested = (
                    bool(params.get("stream"))
                    and method in CHAT_METHODS
                    and not model_identity_query
                )
                first_delta_at = [None]
                started_at = time.perf_counter()
                if stream_requested:
                    loop = asyncio.get_running_loop()
                    request_id = request.get("id")
                    def emit_delta(text: str) -> None:
                        if first_delta_at[0] is None:
                            first_delta_at[0] = time.perf_counter()
                        event = {"jsonrpc": "2.0", "method": "SarembokChat.delta", "params": {"id": request_id, "text": text}}
                        future = asyncio.run_coroutine_threadsafe(websocket.send(json.dumps(event, separators=(",", ":"))), loop)
                        future.result(timeout=10)
                    token_ctx = set_stream_callback(emit_delta)
                async with cloud_server.get_db_lock():
                    result = await asyncio.to_thread(cloud_server.dispatch, method, params)
                if token_ctx is not None:
                    reset_stream_callback(token_ctx)
                    token_ctx = None
                    if isinstance(result, dict):
                        metadata = result.get("metadata")
                        if isinstance(metadata, dict):
                            metadata["streamed"] = True
                            metadata["ttft_ms"] = round((first_delta_at[0] - started_at) * 1000, 1) if first_delta_at[0] is not None else None
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                cloud_server.LOG.info("rpc_success method=%s request_id=%s streamed=%s", method, request.get("id"), stream_requested)
            except PermissionError as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32001, "message": str(exc)}}
                cloud_server.LOG.warning("rpc_auth_failed peer=%s", peer)
            except Exception as exc:
                if token_ctx is not None:
                    try: reset_stream_callback(token_ctx)
                    except Exception: pass
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32000, "message": str(exc)}}
                cloud_server.LOG.warning("rpc_error peer=%s error=%s", peer, exc)
            await websocket.send(json.dumps(response, separators=(",", ":")))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        cloud_server.LOG.info("connection_close peer=%s", peer)


def _is_model_identity_query(prompt: str) -> bool:
    markers = (
        "what model is this",
        "what model are you",
        "what model do you use",
        "what model is running",
        "what model is active",
        "what model are you running",
    )
    prompt_lower = prompt.lower()
    return any(marker in prompt_lower for marker in markers)

cloud_server.handler = handler


THEME_UI = r'''
<style id="sarembok-theme-toggle-style">
html[data-sarembok-theme="light"] {
    color-scheme: light;
    --bg-void: #f4f7fb;
    --bg-surface: #ffffff;
    --bg-card: rgba(255,255,255,0.92);
    --border-glass: rgba(15,23,42,0.14);
    --border-subtle: rgba(15,23,42,0.10);
    --text-main: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
}
html[data-sarembok-theme="light"] body {
    background: #f4f7fb !important;
    color: #0f172a !important;
}
html[data-sarembok-theme="light"] #app {
    background: #f4f7fb !important;
}
html[data-sarembok-theme="light"] .cyber-header {
    background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,255,255,0.72)) !important;
    border-bottom-color: rgba(15,23,42,0.10) !important;
}
html[data-sarembok-theme="light"] .cyber-left-dock {
    background: rgba(255,255,255,0.92) !important;
    border-right-color: rgba(15,23,42,0.10) !important;
}
html[data-sarembok-theme="light"] [class*="panel"],
html[data-sarembok-theme="light"] [class*="card"],
html[data-sarembok-theme="light"] [class*="surface"],
html[data-sarembok-theme="light"] [class*="workspace"],
html[data-sarembok-theme="light"] [class*="view"] {
    color: #0f172a !important;
}
html[data-sarembok-theme="light"] [class*="panel"]:not([class*="gradient"]),
html[data-sarembok-theme="light"] [class*="card"]:not([class*="gradient"]),
html[data-sarembok-theme="light"] [class*="surface"]:not([class*="gradient"]),
html[data-sarembok-theme="light"] [class*="workspace"]:not([class*="gradient"]),
html[data-sarembok-theme="light"] [class*="view"]:not([class*="gradient"]) {
    background-color: rgba(255,255,255,0.88) !important;
    border-color: rgba(15,23,42,0.10) !important;
}
html[data-sarembok-theme="light"] .header-brand-title,
html[data-sarembok-theme="light"] .dock-version,
html[data-sarembok-theme="light"] #global-input-field,
html[data-sarembok-theme="light"] input,
html[data-sarembok-theme="light"] textarea,
html[data-sarembok-theme="light"] select {
    color: #0f172a !important;
}
html[data-sarembok-theme="light"] input::placeholder,
html[data-sarembok-theme="light"] textarea::placeholder,
html[data-sarembok-theme="light"] #global-input-field::placeholder {
    color: #64748b !important;
}
html[data-sarembok-theme="light"] #global-input-bar {
    background: linear-gradient(to top, rgba(244,247,251,1) 0%, rgba(244,247,251,0.94) 60%, rgba(244,247,251,0) 100%) !important;
}
html[data-sarembok-theme="light"] #global-input-bar-inner {
    background: rgba(255,255,255,0.96) !important;
    border-color: rgba(15,23,42,0.14) !important;
    box-shadow: 0 10px 32px rgba(15,23,42,0.12), 0 0 18px rgba(0,160,180,0.08) !important;
}
html[data-sarembok-theme="light"] .dock-btn {
    color: #475569 !important;
}
html[data-sarembok-theme="light"] .dock-btn:hover,
html[data-sarembok-theme="light"] .dock-btn.active {
    color: #008ea3 !important;
    background: rgba(0,160,180,0.10) !important;
    border-color: rgba(0,160,180,0.28) !important;
    box-shadow: none !important;
}
html[data-sarembok-theme="light"] .dock-btn.active::before {
    background: #008ea3 !important;
    box-shadow: none !important;
}
#sarembok-theme-toggle {
    position: fixed;
    top: 14px;
    right: 18px;
    z-index: 1000;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: 108px;
    height: 36px;
    padding: 0 12px;
    border: 1px solid rgba(0,240,255,0.28);
    border-radius: 999px;
    background: rgba(6,12,26,0.88);
    color: #ffffff;
    font: 600 10px/1 'JetBrains Mono', monospace;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 8px 22px rgba(0,0,0,0.22), 0 0 16px rgba(0,240,255,0.10);
    cursor: pointer;
    transition: transform .2s ease, border-color .2s ease, background .2s ease, color .2s ease;
}
#sarembok-theme-toggle:hover { transform: translateY(-1px); border-color: rgba(0,240,255,0.5); }
#sarembok-theme-toggle:focus-visible { outline: 2px solid var(--cyan, #00f0ff); outline-offset: 2px; }
#sarembok-theme-toggle .theme-icon { font-size: 15px; line-height: 1; }
html[data-sarembok-theme="light"] #sarembok-theme-toggle {
    background: rgba(255,255,255,0.94);
    border-color: rgba(15,23,42,0.14);
    color: #0f172a;
    box-shadow: 0 8px 22px rgba(15,23,42,0.12);
}
@media (max-width: 768px) {
    #sarembok-theme-toggle {
        top: 10px;
        right: 10px;
        min-width: 92px;
        height: 34px;
        padding: 0 10px;
    }
}
</style>
<button id="sarembok-theme-toggle" type="button" aria-label="Switch to light mode" aria-pressed="false" title="Switch to light mode">
    <span class="theme-icon" aria-hidden="true">☀</span>
    <span class="theme-label">LIGHT</span>
</button>
<script>
(function () {
    const KEY = 'sarembok-theme';
    const root = document.documentElement;
    const button = document.getElementById('sarembok-theme-toggle');
    if (!button) return;

    function applyTheme(theme) {
        const light = theme === 'light';
        root.dataset.sarembokTheme = light ? 'light' : 'dark';
        button.setAttribute('aria-pressed', light ? 'true' : 'false');
        button.setAttribute('aria-label', light ? 'Switch to dark mode' : 'Switch to light mode');
        button.title = light ? 'Switch to dark mode' : 'Switch to light mode';
        const icon = button.querySelector('.theme-icon');
        const label = button.querySelector('.theme-label');
        if (icon) icon.textContent = light ? '☾' : '☀';
        if (label) label.textContent = light ? 'DARK' : 'LIGHT';
    }

    let saved = null;
    try { saved = localStorage.getItem(KEY); } catch (_) {}
    applyTheme(saved === 'light' ? 'light' : 'dark');

    button.addEventListener('click', function () {
        const next = root.dataset.sarembokTheme === 'light' ? 'dark' : 'light';
        applyTheme(next);
        try { localStorage.setItem(KEY, next); } catch (_) {}
    });
})();
</script>
'''


async def process_http_request(connection, request):
    path = getattr(request, "path", None) or getattr(connection, "path", "/")
    if path not in ("/", "/index.html"):
        return await _original_process_http_request(connection, request)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "frontend", "index.html"),
        os.path.join(base_dir, "..", "frontend", "index.html"),
        os.path.join(base_dir, "..", "..", "frontend", "index.html"),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "index.html")),
        "/app/frontend/index.html",
        "frontend/index.html",
    ]
    html_str = None
    for cand in candidates:
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f: html_str = f.read()
                break
            except Exception as exc: cloud_server.LOG.error("Failed to read frontend index.html: %s", exc)
    if not html_str:
        html_str = "<!DOCTYPE html><html><body><h1>Sarembok VE Cloud Runtime</h1><p>Status: ONLINE</p></body></html>\n"

    # Inject the theme control at the HTTP presentation boundary so the
    # restored cockpit source remains untouched and the preference persists
    # entirely in the browser.
    if "id=\"sarembok-theme-toggle\"" not in html_str and "</body>" in html_str:
        html_str = html_str.replace("</body>", THEME_UI + "\n</body>", 1)

    # The authoritative browser UI lives in frontend/index.html.
    # Do not inject a second sendDirective implementation here.
    # The frontend's WebSocket dispatcher consumes SarembokChat.delta.
    if hasattr(connection, "respond"):
        resp = connection.respond(200, html_str)
        try: del resp.headers["Content-Type"]
        except Exception: pass
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    return (200, [("Content-Type", "text/html; charset=utf-8")], html_str.encode("utf-8"))


cloud_server.process_http_request = process_http_request

if __name__ == "__main__":
    asyncio.run(cloud_server.main())