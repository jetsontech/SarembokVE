"""Hardened SarembokVE production entrypoint.

The historical runtime dispatcher remains intact. This boundary adds:
- explicit browser/operator/admin/master roles;
- secure admin credential behavior with no source fallback;
- worker enrollment and database-backed worker tokens;
- WebSocket origin and rate limits;
- per-request execution IDs and audit events;
- cooperative cancellation ownership;
- idempotency for mutating operations;
- secret redaction;
- reported-vs-attested worker capability semantics.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from typing import Any

import knowledge_rpc_server as runtime
from production_guard_v2 import (
    CANCELLATION_METHODS,
    METHOD_REQUIREMENTS,
    ProductionGuard,
    scrub,
)
from provider_router import reset_stream_callback, set_stream_callback

cloud = runtime.cloud_server
GUARD = ProductionGuard()
ORIGINAL_VALIDATE = cloud.validate_request
ORIGINAL_DISPATCH = cloud.dispatch
ORIGINAL_HANDLER = cloud.handler
ORIGINAL_PROCESS_HTTP_REQUEST = cloud.process_http_request
ORIGINAL_SET_STREAM_CALLBACK = set_stream_callback

WORKER_TOKEN_TABLE = "worker_credentials"
EXECUTION_OWNERS: dict[str, str] = {}
CANCELLED: dict[str, float] = {}
ACTIVE_EXECUTIONS: dict[str, asyncio.Task[Any]] = {}

# Source-compatible runtime safety: no development credential is accepted.
_admin_passcode = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
cloud.ADMIN_PASSCODE = _admin_passcode
cloud.ADMIN_ALLOWED_PASSCODES = {_admin_passcode} if _admin_passcode else set()


def _ensure_worker_credentials() -> None:
    db = cloud.store.db
    db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {WORKER_TOKEN_TABLE} (
            worker_id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            revoked_at TEXT
        )
        """
    )
    db.commit()


def _token_hash(token: str) -> str:
    salt = os.getenv("SAREMBOK_WORKER_TOKEN_HASH_SALT", "").strip()
    return hashlib.sha256((salt + token).encode("utf-8")).hexdigest()


def _browser_session_valid(token: str) -> bool:
    if not token:
        return False
    expiry = getattr(cloud, "BROWSER_SESSIONS", {}).get(token)
    return bool(expiry and float(expiry) > time.time())


def _worker_token_valid(worker_id: str, token: str) -> bool:
    if not worker_id or not token:
        return False
    _ensure_worker_credentials()
    row = cloud.store.db.execute(
        f"SELECT token_hash, revoked_at FROM {WORKER_TOKEN_TABLE} WHERE worker_id=?",
        (worker_id,),
    ).fetchone()
    if not row or row[1]:
        return False
    valid = hmac.compare_digest(str(row[0]), _token_hash(token))
    if valid:
        cloud.store.db.execute(
            f"UPDATE {WORKER_TOKEN_TABLE} SET last_used_at=? WHERE worker_id=?",
            (cloud.now(), worker_id),
        )
        cloud.store.db.commit()
    return valid


def _identity(method: str, params: dict[str, Any]) -> tuple[str, str]:
    token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
    if method == "RegisterWorker":
        enrollment = str(params.get("enrollmentToken") or "").strip()
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        if configured and enrollment and hmac.compare_digest(enrollment, configured):
            return "WORKER", str(params.get("workerId") or "registration")
        return "PUBLIC", "anonymous"
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
    if worker_id and _worker_token_valid(worker_id, worker_token):
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
    method, raw_params = ORIGINAL_VALIDATE(request)
    params = dict(raw_params or {})
    role, subject = _identity(method, params)

    if method == "VerifyAdminPasscode":
        configured = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
        supplied = str(params.get("passcode") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(supplied, configured):
            raise PermissionError("invalid_admin_credentials")
        role, subject = "ADMIN", "admin-passcode"
    else:
        required = _required_role(method)
        if required is not None and _level(role) < _level(required):
            raise PermissionError("authenticated_session_required" if role == "PUBLIC" else "insufficient_privilege")

    # Registration is the only operation where an enrollment secret establishes
    # a new worker identity. The secret itself is never returned or persisted.
    if method == "RegisterWorker":
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        enrollment = str(params.get("enrollmentToken") or "").strip()
        if not configured or not enrollment or not hmac.compare_digest(enrollment, configured):
            raise PermissionError("worker_enrollment_required")

    execution_id = str(request.get("id") or f"rpc-{time.time_ns()}")
    if len(execution_id) > 128:
        raise ValueError("execution_id_too_long")
    idem = str(params.get("idempotencyKey") or "").strip()
    if len(idem) > 128:
        raise ValueError("idempotency_key_too_long")

    params["executionId"] = execution_id
    params["_sarembokRole"] = role
    params["_sarembokSubject"] = subject
    EXECUTION_OWNERS[execution_id] = subject
    return method, params


def _is_cancelled(execution_id: str) -> bool:
    stamp = CANCELLED.get(execution_id)
    if stamp is None:
        return False
    if time.monotonic() - stamp > 900:
        CANCELLED.pop(execution_id, None)
        return False
    return True


def _register_worker_token(worker_id: str) -> str:
    _ensure_worker_credentials()
    token = secrets.token_urlsafe(32)
    cloud.store.db.execute(
        f"INSERT OR REPLACE INTO {WORKER_TOKEN_TABLE}(worker_id,token_hash,created_at,last_used_at,revoked_at) VALUES(?,?,?,?,NULL)",
        (worker_id, _token_hash(token), cloud.now(), cloud.now()),
    )
    cloud.store.db.commit()
    return token


def _dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(params.get("executionId") or "")
    subject = str(params.get("_sarembokSubject") or "anonymous")
    role = str(params.get("_sarembokRole") or "PUBLIC")

    if method in CANCELLATION_METHODS:
        target = str(params.get("requestId") or params.get("executionId") or "").strip()
        owner = EXECUTION_OWNERS.get(target)
        if not target or owner is None:
            raise PermissionError("unknown_execution")
        if owner != subject and role not in {"ADMIN", "MASTER", "SYSTEM"}:
            raise PermissionError("cannot_cancel_other_principal")
        CANCELLED[target] = time.monotonic()
        task = ACTIVE_EXECUTIONS.get(target)
        if task and not task.done():
            task.cancel()
        try:
            legacy = ORIGINAL_DISPATCH("CancelActiveStream", {"requestId": target})
        except Exception:
            legacy = {"cancelled": True}
        return {"cancelled": True, "executionId": target, "status": "CANCEL_REQUESTED", "legacy": scrub(legacy)}

    if execution_id and _is_cancelled(execution_id):
        return {"executionId": execution_id, "status": "CANCELLED", "cancelled": True}

    idem = str(params.get("idempotencyKey") or "").strip()
    if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
        cached = GUARD.idempotency.get(subject, method, idem)
        if cached is not None:
            return {**cached, "metadata": {**cached.get("metadata", {}), "idempotentReplay": True}}

    safe_params = {k: v for k, v in params.items() if not k.startswith("_sarembok")}
    started = time.perf_counter()
    result = ORIGINAL_DISPATCH(method, safe_params)

    if method == "RegisterWorker" and isinstance(result, dict):
        worker_id = str(result.get("workerId") or safe_params.get("workerId") or "").strip()
        if worker_id:
            result = dict(result)
            result["workerToken"] = _register_worker_token(worker_id)
            result["workerTokenType"] = "enrollment_issued"
            result["hardwareAttestation"] = "NOT_ATTESTED"
            result["capabilityTrust"] = "REPORTED"

    if method == "ListWorkers" and isinstance(result, dict):
        def annotate(value: Any) -> Any:
            if isinstance(value, list): return [annotate(x) for x in value]
            if isinstance(value, dict):
                out = {k: annotate(v) for k, v in value.items()}
                workerish = any(k in out for k in ("gpu_model", "gpuModel", "gpu", "cuda_version", "cudaVersion"))
                if workerish:
                    out.setdefault("capabilityTrust", "REPORTED")
                    out.setdefault("hardwareAttestation", "NOT_ATTESTED")
                return out
            return value
        result = annotate(result)

    if not isinstance(result, dict):
        result = {"value": result}
    result = scrub(dict(result))
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    metadata.update({"executionId": execution_id, "role": role, "durationMs": round((time.perf_counter() - started) * 1000, 1)})
    result["metadata"] = metadata

    if idem and method not in {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}:
        GUARD.idempotency.put(subject, method, idem, result)

    try:
        cloud.store.event(None, "RPC_EXECUTION", scrub({
            "executionId": execution_id, "method": method, "subject": subject,
            "role": role, "status": "SUCCEEDED", "durationMs": metadata["durationMs"],
        }))
    except Exception:
        pass
    return result


def _stream_callback(callback):
    execution_id = EXECUTION_OWNERS.copy()
    current = next(reversed(execution_id), "") if execution_id else ""
    def guarded(text: str):
        if current and _is_cancelled(current):
            return
        callback(text)
    return ORIGINAL_SET_STREAM_CALLBACK(guarded)


async def _handler(websocket):
    if not GUARD.origin_allowed(websocket):
        await websocket.close(code=1008, reason="origin_not_allowed")
        return
    GUARD.allow_ip(websocket)
    return await ORIGINAL_HANDLER(websocket)


# Install boundary before the legacy server enters its main loop.
_ensure_worker_credentials()
cloud.validate_request = _validate
cloud.dispatch = _dispatch
cloud.handler = _handler
cloud.process_http_request = ORIGINAL_PROCESS_HTTP_REQUEST
runtime.set_stream_callback = _stream_callback
runtime.reset_stream_callback = reset_stream_callback
runtime.cloud_server.handler = _handler

if __name__ == "__main__":
    asyncio.run(cloud.main())
