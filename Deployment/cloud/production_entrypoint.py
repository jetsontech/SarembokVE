"""SarembokVE production entrypoint.

Loads the existing compatibility RPC server, then adds production controls at
the WebSocket boundary. The historical cockpit and legacy dispatcher remain
unchanged underneath this boundary.
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import hmac
import os
import time
from typing import Any

import knowledge_rpc_server as runtime
from production_guard_v2 import (
    ADMIN_METHODS,
    CANCELLATION_METHODS,
    METHOD_REQUIREMENTS,
    ProductionGuard,
    scrub,
)
from provider_router import reset_stream_callback, set_stream_callback

cloud = runtime.cloud_server
GUARD = ProductionGuard()
CURRENT_EXECUTION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_execution_id", default="")
CURRENT_SUBJECT: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_subject", default="anonymous")
CANCELLED: dict[str, float] = {}
EXECUTION_OWNERS: dict[str, str] = {}

ORIGINAL_VALIDATE = cloud.validate_request
ORIGINAL_DISPATCH = cloud.dispatch
ORIGINAL_HANDLER = cloud.handler
ORIGINAL_PROCESS_HTTP_REQUEST = cloud.process_http_request
ORIGINAL_SET_STREAM_CALLBACK = set_stream_callback

# Remove the historical development credentials before the runtime can service
# any request. Empty administrator configuration means admin passcode auth is
# disabled rather than falling back to a source-controlled secret.
_admin_passcode = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
cloud.ADMIN_PASSCODE = _admin_passcode
cloud.ADMIN_ALLOWED_PASSCODES = {_admin_passcode} if _admin_passcode else set()


def _browser_session_valid(token: str) -> bool:
    if not token:
        return False
    expiry = getattr(cloud, "BROWSER_SESSIONS", {}).get(token)
    return bool(expiry and float(expiry) > time.time())


def _identity(params: dict[str, Any]) -> tuple[str, str]:
    token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
    if _browser_session_valid(token):
        return "USER", "browser-session"
    master = os.getenv("SAREMBOK_MASTER_TOKEN", "").strip()
    admin = os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()
    operator = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
    if master and token and hmac.compare_digest(token, master):
        return "MASTER", "master"
    if admin and token and hmac.compare_digest(token, admin):
        return "ADMIN", "admin"
    if operator and token and hmac.compare_digest(token, operator):
        return "OPERATOR", "operator"
    worker_id = str(params.get("workerId") or "").strip()
    worker_token = str(params.get("workerToken") or "").strip()
    if worker_id and worker_token:
        return "WORKER", worker_id
    return "PUBLIC", "anonymous"


def _required_role(method: str) -> str | None:
    if method == "ping" or method in {"AuthenticateMaster", "AuthenticateSocialUser"}:
        return None
    if method == "VerifyAdminPasscode":
        return "ADMIN"
    return METHOD_REQUIREMENTS.get(method, "ADMIN")


def _level(role: str) -> int:
    return {"PUBLIC": 0, "USER": 1, "WORKER": 2, "OPERATOR": 3, "ADMIN": 4, "MASTER": 5, "SYSTEM": 6}.get(role, 0)


def _validate(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    method, params = ORIGINAL_VALIDATE(request)
    params = dict(params or {})
    role, subject = _identity(params)
    required = _required_role(method)

    if method == "VerifyAdminPasscode":
        configured = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
        supplied = str(params.get("passcode") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(supplied, configured):
            raise PermissionError("invalid_admin_credentials")
        role, subject = "ADMIN", "admin-passcode"
    elif required is not None and _level(role) < _level(required):
        raise PermissionError("authenticated_session_required" if role == "PUBLIC" else "insufficient_privilege")

    execution_id = str(request.get("id") or f"rpc-{time.time_ns()}" )
    if len(execution_id) > 128:
        raise ValueError("execution_id_too_long")
    idem = str(params.get("idempotencyKey") or "").strip()
    if len(idem) > 128:
        raise ValueError("idempotency_key_too_long")

    params["executionId"] = execution_id
    params["_sarembokRole"] = role
    params["_sarembokSubject"] = subject
    CURRENT_EXECUTION_ID.set(execution_id)
    CURRENT_SUBJECT.set(subject)
    EXECUTION_OWNERS[execution_id] = subject
    GUARD.allow_subject(GUARD.identify(params, browser_session_valid=(role == "USER")))
    return method, params


def _mark_cancelled(execution_id: str) -> None:
    if execution_id:
        CANCELLED[execution_id] = time.monotonic()


def _is_cancelled(execution_id: str) -> bool:
    stamp = CANCELLED.get(execution_id)
    if stamp is None:
        return False
    if time.monotonic() - stamp > 900:
        CANCELLED.pop(execution_id, None)
        return False
    return True


def _dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(params.get("executionId") or CURRENT_EXECUTION_ID.get())
    subject = str(params.get("_sarembokSubject") or CURRENT_SUBJECT.get() or "anonymous")
    role = str(params.get("_sarembokRole") or "PUBLIC")

    if method in CANCELLATION_METHODS:
        target = str(params.get("requestId") or params.get("executionId") or "").strip()
        owner = EXECUTION_OWNERS.get(target)
        if not target or owner is None:
            raise PermissionError("unknown_execution")
        if owner != subject and role not in {"ADMIN", "MASTER", "SYSTEM"}:
            raise PermissionError("cannot_cancel_other_principal")
        _mark_cancelled(target)
        try:
            result = ORIGINAL_DISPATCH("CancelActiveStream", {"requestId": target})
        except Exception:
            result = {"cancelled": True}
        return {"cancelled": True, "executionId": target, "legacy": scrub(result), "status": "CANCEL_REQUESTED"}

    if execution_id and _is_cancelled(execution_id):
        return {"executionId": execution_id, "status": "CANCELLED", "cancelled": True}

    idem = str(params.get("idempotencyKey") or "").strip()
    if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
        cached = GUARD.idempotency.get(subject, method, idem)
        if cached is not None:
            return {**cached, "metadata": {**cached.get("metadata", {}), "idempotentReplay": True}}

    safe_params = {k: v for k, v in params.items() if not k.startswith("_sarembok")}
    started = time.perf_counter()
    try:
        result = ORIGINAL_DISPATCH(method, safe_params)
        if isinstance(result, dict):
            result = scrub(dict(result))
        else:
            result = {"value": scrub(result)}
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        metadata.update({
            "executionId": execution_id,
            "role": role,
            "durationMs": round((time.perf_counter() - started) * 1000, 1),
        })
        result["metadata"] = metadata

        # Ground worker capability semantics without changing the legacy schema:
        # a GPU/device string is reported metadata unless independently attested.
        if method == "ListWorkers":
            def annotate(value: Any) -> Any:
                if isinstance(value, list): return [annotate(x) for x in value]
                if isinstance(value, dict):
                    out = {k: annotate(v) for k, v in value.items()}
                    if any(k in out for k in ("gpu_model", "gpuModel", "gpu", "cuda_version", "cudaVersion")):
                        out.setdefault("capabilityTrust", "REPORTED")
                        out.setdefault("hardwareAttestation", "NOT_ATTESTED")
                    return out
                return value
            result = annotate(result)

        if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
            GUARD.idempotency.put(subject, method, idem, result)
        try:
            cloud.store.event(None, "RPC_EXECUTION", scrub({
                "executionId": execution_id, "method": method, "subject": subject,
                "role": role, "status": "SUCCEEDED",
                "durationMs": round((time.perf_counter() - started) * 1000, 1),
            }))
        except Exception:
            pass
        return result
    except Exception as exc:
        try:
            cloud.store.event(None, "RPC_EXECUTION", scrub({
                "executionId": execution_id, "method": method, "subject": subject,
                "role": role, "status": "FAILED", "error": str(exc),
            }))
        except Exception:
            pass
        raise


def _stream_callback(callback):
    execution_id = CURRENT_EXECUTION_ID.get()
    def guarded(text: str):
        if execution_id and _is_cancelled(execution_id):
            return
        callback(text)
    return ORIGINAL_SET_STREAM_CALLBACK(guarded)


async def _handler(websocket):
    if not GUARD.origin_allowed(websocket):
        await websocket.close(code=1008, reason="origin_not_allowed")
        return
    GUARD.allow_ip(websocket)
    return await ORIGINAL_HANDLER(websocket)


cloud.validate_request = _validate
cloud.dispatch = _dispatch
runtime.set_stream_callback = _stream_callback
runtime.reset_stream_callback = reset_stream_callback
runtime.cloud_server.handler = _handler
cloud.handler = _handler

# Preserve the existing HTTP frontend/session behavior exactly.
cloud.process_http_request = ORIGINAL_PROCESS_HTTP_REQUEST

if __name__ == "__main__":
    asyncio.run(cloud.main())
