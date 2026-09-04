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
from runtime_response_composer import build_runtime_context, is_self_state_query, render_identity

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
    cloud_server.evaluate_worker_liveness()
    return runtime_authority_snapshot(
        cloud_server.store,
        cloud_server.PROVIDER_ROUTER,
        cloud_server.STARTED,
    )


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


def _dispatch_chat_with_authority(params: dict) -> dict:
    """Run the normal dialogue path with a live, authoritative system context."""
    prompt = str(params.get("prompt") or params.get("message") or params.get("text") or "").strip()
    diagnostic = _authoritative_snapshot()

    if is_self_state_query(prompt):
        response = render_identity(diagnostic)
        return {
            **diagnostic,
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

    # The existing cloud dialogue implementation owns provider selection and
    # conversation persistence. Inject authority at that boundary instead of
    # duplicating provider logic here.
    runtime_context = build_runtime_context(diagnostic)
    original_generate = cloud_server.PROVIDER_ROUTER.generate

    def generate_with_authority(system_prompt, user_prompt, messages):
        authoritative_prompt = (
            runtime_context
            + "\n\nDIALOGUE RULE: When describing Sarembok, prefer these observed facts over model assumptions. "
              "You may explain or contextualize them, but never contradict them.\n\n"
            + str(system_prompt or "")
        )
        return original_generate(authoritative_prompt, user_prompt, messages)

    cloud_server.PROVIDER_ROUTER.generate = generate_with_authority
    try:
        return _original_dispatch(params.get("_method", "SarembokChat"), params)
    finally:
        cloud_server.PROVIDER_ROUTER.generate = original_generate


def dispatch(method: str, params: dict) -> dict:
    if method == "GetRuntimeInfo":
        return _authoritative_snapshot()
    if method in {"SarembokChat", "Chat", "SarembokDialogue"}:
        chat_params = dict(params)
        chat_params["_method"] = method
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
                    provider="runtime_authority",
                    model="runtime-authority",
                ),
                "agentId": "sarembok-prime",
                "timestamp": cloud_server.now(),
            }
        return _dispatch_chat_with_authority(chat_params)
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
                stream_requested = bool(params.get("stream")) and method in CHAT_METHODS
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
                    result = await asyncio.to_thread(dispatch, method, params)
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
            except cloud_server.PermissionError as exc:
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


cloud_server.handler = handler


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
