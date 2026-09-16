"""Production bootstrap for SarembokVE.

Loads the existing production JSON-RPC entrypoint and applies security,
correlation, idempotency, origin and cancellation controls before the server is
started. The historical cockpit and runtime dispatcher remain intact.
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import hmac
import os
import re
import time
from typing import Any

import knowledge_rpc_server as runtime
from production_guard import (
    USER_METHODS,
    WORKER_METHODS,
    OPERATOR_METHODS,
    ADMIN_METHODS,
    LOGIN_METHODS,
    ProductionGuard,
    scrub,
)

cloud = runtime.cloud_server
GUARD = ProductionGuard()
CURRENT_EXECUTION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_execution_id", default="")
CANCELLED: dict[str, float] = {}

# Remove historical insecure administrative fallbacks before the dispatcher can
# be reached. An empty environment variable intentionally disables passcode auth.
_explicit_admin = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
cloud.ADMIN_PASSCODE = _explicit_admin
cloud.ADMIN_ALLOWED_PASSCODES = {_explicit_admin} if _explicit_admin else set()

_ORIGINAL_VALIDATE = cloud.validate_request
_ORIGINAL_DISPATCH = cloud.dispatch
_ORIGINAL_HANDLER = cloud.handler
_ORIGINAL_SET_STREAM_CALLBACK = runtime.set_stream_callback


def _browser_session_valid(token: str) -> bool:
    if not token:
        return False
    expiry = getattr(cloud, "BROWSER_SESSIONS", {}).get(token)
    return bool(expiry and float(expiry) > time.time())


def _role_for(method: str, params: dict[str, Any]) -> tuple[str, str]:
    token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
    if _browser_session_valid(token):
        return "USER", "browser-session"
    if token and os.getenv("SAREMBOK_MASTER_TOKEN", "").strip() and hmac.compare_digest(token, os.getenv("SAREMBOK_MASTER_TOKEN", "").strip()):
        return "MASTER", "master"
    if token and os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip() and hmac.compare_digest(token, os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()):
        return "ADMIN", "admin"
    if token and os.getenv("SAREMBOK_AUTH_TOKEN", "").strip() and hmac.compare_digest(token, os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()):
        return "OPERATOR", "operator"
    if method in WORKER_METHODS and str(params.get("workerToken") or "").strip():
        return "WORKER", str(params.get("workerId") or "worker")
    return "PUBLIC", "anonymous"


def _required_role(method: str) -> str | None:
    if method in {"GetRuntimeInfo", "GetProviderMetrics", "GetVisualEngineStatus", "ListWorkers", "ListTasks", "ListProjects", "GetCurrentUser", "GetFeedbackSummary", "ListMemories", "SearchMemories", "ListDigitalHumanSessions", "GetDigitalHumanSession", "ListMcpServers", "GetGpuMarketplace", "ListGpuRentals", "GetVisionStatus", "GetAdminStatus", "GetConversationHistory"}:
        return "USER"
    if method in {"SarembokChat", "Chat", "SarembokDialogue", "BrowserNavigate", "BrowserScreenshot", "BrowserRender", "SubmitFeedback", "StoreMemory", "DeleteMemory", "CreateDigitalHumanSession", "CloseDigitalHumanSession", "SearchYouTube", "ResolveMediaStream", "ProcessVisionFrame", "SpatialVisualRecall", "GenerateImage", "SaveUserChatSession", "ListUserChatSessions", "DeleteUserChatSession"}:
        return "USER"
    if method in {"RegisterWorker", "Heartbeat", "ClaimTask", "CompleteTask", "FailTask", "ExecuteComputeTask"}:
        return "WORKER"
    if method in OPERATOR_METHODS:
        return "OPERATOR"
    if method in ADMIN_METHODS:
        return "ADMIN"
    if method in LOGIN_METHODS or method == "ping":
        return None
    return "ADMIN"


def _level(role: str) -> int:
    return {"PUBLIC": 0, "USER": 1, "WORKER": 2, "OPERATOR": 3, "ADMIN": 4, "MASTER": 5, "SYSTEM": 6}.get(role, 0)


def _guard_validate(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    method, params = _ORIGINAL_VALIDATE(request)
    params = dict(params or {})
    role, subject = _role_for(method, params)
    required = _required_role(method)
    if required is not None and _level(role) < _level(required):
        raise PermissionError("insufficient_privilege" if role != "PUBLIC" else "authenticated_session_required")

    # Worker mutating operations require an explicit worker enrollment credential
    # in production. Existing internal/administrative callers use the higher roles.
    if method == "RegisterWorker":
        enrollment = str(params.get("enrollmentToken") or "").strip()
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        if not configured or not enrollment or not hmac.compare_digest(enrollment, configured):
            raise PermissionError("worker_enrollment_required")

    execution_id = str(request.get("id") or f"rpc-{int(time.time()*1000)}-{os.getpid()}")
    params["executionId"] = execution_id
    params["_guardSubject"] = subject
    params["_guardRole"] = role
    CURRENT_EXECUTION_ID.set(execution_id)
    return method, params


def _cancelled(execution_id: str) -> bool:
    stamp = CANCELLED.get(execution_id)
    if stamp is None:
        return False
    if time.monotonic() - stamp > 900:
        CANCELLED.pop(execution_id, None)
        return False
    return True


def _dispatch_guarded(method: str, params: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(params.get("executionId") or CURRENT_EXECUTION_ID.get() or "")
    if method == "CancelActiveStream":
        target = str(params.get("requestId") or params.get("executionId") or "").strip()
        if not target:
            return {"cancelled": False, "error": "requestId_required"}
        CANCELLED[target] = time.monotonic()
        return {"cancelled": True, "executionId": target, "timestamp": cloud.now()}
    if execution_id and _cancelled(execution_id):
        return {"cancelled": True, "executionId": execution_id, "status": "CANCELLED", "timestamp": cloud.now()}

    role = str(params.get("_guardRole") or "PUBLIC")
    subject = str(params.get("_guardSubject") or "anonymous")
    idem = str(params.get("idempotencyKey") or "").strip()
    if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
        cached = GUARD.idempotency.get(subject, method, idem)
        if cached is not None:
            return dict(cached)

    started = time.perf_counter()
    try:
        result = _ORIGINAL_DISPATCH(method, params)
        if not isinstance(result, dict):
            result = {"value": result}
        result = scrub(dict(result))
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        metadata.update({"executionId": execution_id, "role": role, "durationMs": round((time.perf_counter() - started) * 1000, 1)})
        result["metadata"] = metadata
        if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
            GUARD.idempotency.put(subject, method, idem, result)
        try:
            cloud.store.event(None, "RPC_EXECUTION", scrub({"executionId": execution_id, "method": method, "subject": subject, "role": role, "status": "SUCCEEDED"}))
        except Exception:
            pass
        return result
    except Exception as exc:
        try:
            cloud.store.event(None, "RPC_EXECUTION", scrub({"executionId": execution_id, "method": method, "subject": subject, "role": role, "status": "FAILED", "error": str(exc)}))
        except Exception:
            pass
        raise


def _set_stream_callback_guarded(callback):
    execution_id = CURRENT_EXECUTION_ID.get()
    def guarded(text: str):
        if execution_id and _cancelled(execution_id):
            return
        callback(text)
    return _ORIGINAL_SET_STREAM_CALLBACK(guarded)


cloud.validate_request = _guard_validate
cloud.dispatch = _dispatch_guarded
runtime.set_stream_callback = _set_stream_callback_guarded


async def _handler(websocket):
    if not GUARD.origin_allowed(websocket):
        await websocket.close(code=1008, reason="origin_not_allowed")
        return
    peer = getattr(websocket, "remote_address", None)
    GUARD.allow_ip(websocket)
    return await _ORIGINAL_HANDLER(websocket)


cloud.handler = _handler
runtime.cloud_server.handler = _handler

if __name__ == "__main__":
    asyncio.run(cloud.main())
