"""Production entrypoint that extends the stable cloud RPC gateway.

The existing server remains authoritative for established RPC methods.
This wrapper adds conversational RPCs and a secure browser session boundary.
The runtime master token never enters browser JavaScript.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import server
from conversation_runtime import ConversationRuntime
from engineering_runtime import EngineeringRuntime
import public_session

LOG = logging.getLogger("sarembok.cloud.conversation")
conversation = ConversationRuntime(server.store)
engineering = EngineeringRuntime(
    root=os.getenv("SAREMBOK_ENGINEERING_ROOT", "/app"),
    data_root=os.getenv("SAREMBOK_ENGINEERING_DATA", "/data"),
)
PUBLIC_ORIGINS = {
    item.strip().rstrip("/")
    for item in os.getenv(
        "SAREMBOK_PUBLIC_ORIGINS",
        "https://sarembok.com,https://www.sarembok.com",
    ).split(",")
    if item.strip()
}

# Anonymous browser sessions may use product-facing operations, but never
# infrastructure control operations such as worker registration/completion or
# arbitrary task administration.
PUBLIC_METHODS = {
    "Health", "RuntimeInfo", "ListWorkers", "ListAgents", "GetAgent",
    "CreateAgent", "ListTasks", "GetTask", "ListDigitalHumanSessions",
    "GetDigitalHumanSession", "GetEvents", "ListEvents", "GetCognitiveScorecard",
    "CreateDigitalHumanSession", "Chat", "SendChatMessage", "RememberMemory",
    "RecallMemories", "ListConversation", "ModelProviderInfo",
}


def _request_headers(websocket):
    request = getattr(websocket, "request", None)
    headers = getattr(request, "headers", None)
    if headers is not None:
        return headers
    return getattr(websocket, "request_headers", {})


def _session_from_websocket(websocket) -> str:
    headers = _request_headers(websocket)
    cookie = headers.get("Cookie", "") if hasattr(headers, "get") else ""
    return public_session.extract_cookie(cookie)


def _origin_allowed(websocket) -> bool:
    headers = _request_headers(websocket)
    origin = headers.get("Origin", "") if hasattr(headers, "get") else ""
    return origin.rstrip("/") in PUBLIC_ORIGINS


def _install_public_session_cookie(connection, response):
    """Attach a new browser session cookie to the normal HTML response."""
    if not server.AUTH_TOKEN:
        return response
    headers = getattr(getattr(connection, "request", None), "headers", {})
    cookie = headers.get("Cookie", "") if hasattr(headers, "get") else ""
    if public_session.extract_cookie(cookie):
        return response
    token = public_session.issue(server.AUTH_TOKEN)
    value = public_session.cookie_header(token)
    if hasattr(response, "headers"):
        response.headers["Set-Cookie"] = value
        response.headers["Cache-Control"] = "no-store"
    elif isinstance(response, tuple) and len(response) == 3:
        status, response_headers, body = response
        response_headers = list(response_headers)
        response_headers.append(("Set-Cookie", value))
        response_headers.append(("Cache-Control", "no-store"))
        return (status, response_headers, body)
    return response


_original_process_http_request = server.process_http_request


async def process_http_request(connection, request):
    response = await _original_process_http_request(connection, request)
    path = getattr(request, "path", None) or getattr(connection, "path", "/")
    if path in ("/", "/index.html") and response is not None:
        return _install_public_session_cookie(connection, response)
    return response


server.process_http_request = process_http_request


async def conversation_handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    session_token = _session_from_websocket(websocket)
    public_authenticated = (
        public_session.validate(session_token, server.AUTH_TOKEN)
        and _origin_allowed(websocket)
    )
    LOG.info(
        "conversation_connection_open peer=%s public_session=%s",
        peer,
        public_authenticated,
    )
    try:
        async for raw in websocket:
            request = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > server.MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")

                request = json.loads(raw)
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")

                # Browser sessions are authenticated server-side by the signed
                # cookie. Direct integrations continue to use the existing
                # master runtime token through server.validate_request().
                params = request.get("params") or {}
                if not isinstance(params, dict):
                    raise ValueError("params must be an object")
                method = request.get("method")
                if not isinstance(method, str) or not method or len(method) > server.MAX_METHOD_LENGTH:
                    raise ValueError("invalid method")

                if public_authenticated and "authToken" not in params:
                    if method not in PUBLIC_METHODS:
                        raise PermissionError("method_not_available_to_public_session")
                    params = dict(params)
                    params["authToken"] = server.AUTH_TOKEN
                    request["params"] = params

                method, params = server.validate_request(request)

                if method in {"Chat", "SendChatMessage"}:
                    agent_id = str(params.get("agentId", "")).strip()
                    server.require_agent(agent_id)
                    result = await conversation.chat(
                        agent_id=agent_id,
                        content=str(params.get("content", "")),
                        db_lock=server.DB_LOCK,
                        session_id=(str(params.get("sessionId")) if params.get("sessionId") else None),
                        history_limit=int(params.get("historyLimit", 20)),
                        memory_limit=int(params.get("memoryLimit", 10)),
                    )
                elif method == "RememberMemory":
                    agent_id = str(params.get("agentId", "")).strip()
                    server.require_agent(agent_id)
                    async with server.DB_LOCK:
                        result = conversation.remember(
                            agent_id,
                            str(params.get("content", "")),
                            str(params.get("memoryType", "fact")),
                            float(params.get("importance", 0.5)),
                        )
                elif method == "RecallMemories":
                    agent_id = str(params.get("agentId", "")).strip()
                    server.require_agent(agent_id)
                    async with server.DB_LOCK:
                        result = conversation.recall(agent_id, int(params.get("limit", 20)))
                elif method == "ListConversation":
                    agent_id = str(params.get("agentId", "")).strip()
                    server.require_agent(agent_id)
                    async with server.DB_LOCK:
                        result = conversation.history(agent_id, int(params.get("limit", 50)))
                elif method == "ModelProviderInfo":
                    result = conversation.provider_info()
                elif method == "EngineeringAgentInfo":
                    result = engineering.info()
                elif method == "EngineeringExecutePlan":
                    result = await asyncio.to_thread(engineering.execute, params)
                elif method == "EngineeringGetExecution":
                    execution_id = str(params.get("executionId", "")).strip()
                    if not execution_id:
                        raise ValueError("executionId is required")
                    result = engineering.get(execution_id)
                else:
                    async with server.DB_LOCK:
                        result = server.dispatch(method, params)

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result,
                }
                LOG.info("rpc_success method=%s request_id=%s", method, request.get("id"))

            except PermissionError as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32001, "message": str(exc)},
                }
                LOG.warning("rpc_auth_failed peer=%s", peer)
            except Exception as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32000, "message": str(exc)},
                }
                LOG.warning("rpc_error peer=%s error=%s", peer, exc)

            await websocket.send(json.dumps(response, separators=(",", ":")))
    except server.websockets.exceptions.ConnectionClosed:
        pass
    finally:
        LOG.info("conversation_connection_close peer=%s", peer)


async def conversation_guard(websocket) -> None:
    try:
        await asyncio.wait_for(server.CONNECTIONS.acquire(), timeout=5)
    except TimeoutError:
        await websocket.close(code=1013, reason="server_busy")
        return
    try:
        await conversation_handler(websocket)
    finally:
        server.CONNECTIONS.release()


server.CONNECTIONS_guard = conversation_guard


if __name__ == "__main__":
    asyncio.run(server.main())

