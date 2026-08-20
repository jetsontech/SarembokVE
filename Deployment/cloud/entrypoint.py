"""Production entrypoint that extends the stable cloud RPC gateway.

The existing server remains authoritative for all established RPC methods.
This wrapper adds conversational RPCs without rewriting the proven gateway.
"""

from __future__ import annotations

import asyncio
import json
import logging

import server
from conversation_runtime import ConversationRuntime

LOG = logging.getLogger("sarembok.cloud.conversation")
conversation = ConversationRuntime(server.store)


async def conversation_handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    LOG.info("conversation_connection_open peer=%s", peer)
    try:
        async for raw in websocket:
            request = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > server.MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")

                request = json.loads(raw)
                method, params = server.validate_request(request)

                if method in {"Chat", "SendChatMessage"}:
                    agent_id = str(params.get("agentId", "")).strip()
                    server.require_agent(agent_id)
                    async with server.DB_LOCK:
                        result = await conversation.chat(
                            agent_id=agent_id,
                            content=str(params.get("content", "")),
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
