"""Hardened production boundary with request-scoped streaming cancellation."""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from typing import Any

import knowledge_rpc_server as runtime
from production_guard_v2 import CANCELLATION_METHODS, METHOD_REQUIREMENTS, ProductionGuard, scrub
from provider_router import reset_stream_callback, set_stream_callback

cloud = runtime.cloud_server
GUARD = ProductionGuard()
ORIGINAL_VALIDATE = cloud.validate_request
ORIGINAL_DISPATCH = cloud.dispatch
ORIGINAL_HANDLER = cloud.handler
ORIGINAL_PROCESS_HTTP_REQUEST = cloud.process_http_request
ORIGINAL_SET_STREAM_CALLBACK = set_stream_callback

EXECUTION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_execution_id", default="")
EXECUTION_SUBJECT: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_execution_subject", default="anonymous")
EXECUTION_OWNERS: dict[str, str] = {}
CANCELLED: dict[str, float] = {}
ACTIVE_TASKS: dict[str, asyncio.Task[Any]] = {}
WORKER_TOKEN_TABLE = "worker_credentials"

_admin = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
cloud.ADMIN_PASSCODE = _admin
cloud.ADMIN_ALLOWED_PASSCODES = {_admin} if _admin else set()


def ensure_worker_credentials() -> None:
    db = cloud.store.db
    db.execute(f"CREATE TABLE IF NOT EXISTS {WORKER_TOKEN_TABLE}(worker_id TEXT PRIMARY KEY,token_hash TEXT NOT NULL,created_at TEXT NOT NULL,last_used_at TEXT,revoked_at TEXT)")
    db.commit()


def worker_hash(token: str) -> str:
    salt = os.getenv("SAREMBOK_WORKER_TOKEN_HASH_SALT", "").strip()
    return hashlib.sha256((salt + token).encode()).hexdigest()


def browser_session_valid(token: str) -> bool:
    expiry = getattr(cloud, "BROWSER_SESSIONS", {}).get(token)
    return bool(token and expiry and float(expiry) > time.time())


def worker_token_valid(worker_id: str, token: str) -> bool:
    if not worker_id or not token:
        return False
    ensure_worker_credentials()
    row = cloud.store.db.execute(f"SELECT token_hash,revoked_at FROM {WORKER_TOKEN_TABLE} WHERE worker_id=?", (worker_id,)).fetchone()
    if not row or row[1]:
        return False
    valid = hmac.compare_digest(str(row[0]), worker_hash(token))
    if valid:
        cloud.store.db.execute(f"UPDATE {WORKER_TOKEN_TABLE} SET last_used_at=? WHERE worker_id=?", (cloud.now(), worker_id))
        cloud.store.db.commit()
    return valid


def identify(method: str, params: dict[str, Any]) -> tuple[str, str]:
    token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
    if method == "RegisterWorker":
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        supplied = str(params.get("enrollmentToken") or "").strip()
        return ("WORKER", str(params.get("workerId") or "registration")) if configured and supplied and hmac.compare_digest(configured, supplied) else ("PUBLIC", "anonymous")
    if browser_session_valid(token):
        return "USER", "browser-session"
    master = os.getenv("SAREMBOK_MASTER_TOKEN", "").strip()
    admin = os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()
    operator = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
    if master and token and hmac.compare_digest(master, token): return "MASTER", "master"
    if admin and token and hmac.compare_digest(admin, token): return "ADMIN", "admin"
    if operator and token and hmac.compare_digest(operator, token): return "OPERATOR", "operator"
    wid = str(params.get("workerId") or "").strip(); wt = str(params.get("workerToken") or "").strip()
    if worker_token_valid(wid, wt): return "WORKER", wid
    return "PUBLIC", "anonymous"


def required_role(method: str) -> str | None:
    if method == "ping" or method in {"AuthenticateMaster", "AuthenticateSocialUser"}: return None
    if method == "VerifyAdminPasscode": return "ADMIN"
    return METHOD_REQUIREMENTS.get(method, "ADMIN")


def level(role: str) -> int:
    return {"PUBLIC":0,"USER":1,"WORKER":2,"OPERATOR":3,"ADMIN":4,"MASTER":5,"SYSTEM":6}.get(role,0)


def validate(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    method, raw = ORIGINAL_VALIDATE(request)
    params = dict(raw or {})
    role, subject = identify(method, params)
    if method == "VerifyAdminPasscode":
        configured = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
        supplied = str(params.get("passcode") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(configured, supplied): raise PermissionError("invalid_admin_credentials")
        role, subject = "ADMIN", "admin-passcode"
    else:
        req = required_role(method)
        if req is not None and level(role) < level(req): raise PermissionError("authenticated_session_required" if role == "PUBLIC" else "insufficient_privilege")
    if method == "RegisterWorker":
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip(); supplied = str(params.get("enrollmentToken") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(configured, supplied): raise PermissionError("worker_enrollment_required")
    execution = str(request.get("id") or f"rpc-{time.time_ns()}")
    if len(execution) > 128: raise ValueError("execution_id_too_long")
    idem = str(params.get("idempotencyKey") or "").strip()
    if len(idem) > 128: raise ValueError("idempotency_key_too_long")
    params["executionId"] = execution
    params["_srbk_role"] = role
    params["_srbk_subject"] = subject
    EXECUTION_OWNERS[execution] = subject
    EXECUTION_ID.set(execution); EXECUTION_SUBJECT.set(subject)
    GUARD.allow_subject(GUARD.identify(params, browser_session_valid=(role == "USER")))
    return method, params


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    execution = str(params.get("executionId") or EXECUTION_ID.get())
    subject = str(params.get("_srbk_subject") or EXECUTION_SUBJECT.get() or "anonymous")
    role = str(params.get("_srbk_role") or "PUBLIC")
    if method in CANCELLATION_METHODS:
        target = str(params.get("requestId") or params.get("executionId") or "").strip()
        owner = EXECUTION_OWNERS.get(target)
        if not target or not owner: raise PermissionError("unknown_execution")
        if owner != subject and role not in {"ADMIN","MASTER","SYSTEM"}: raise PermissionError("cannot_cancel_other_principal")
        CANCELLED[target] = time.monotonic()
        task = ACTIVE_TASKS.get(target)
        if task and not task.done(): task.cancel()
        try: legacy = ORIGINAL_DISPATCH("CancelActiveStream", {"requestId": target})
        except Exception: legacy = {"cancelled": True}
        return {"cancelled": True, "executionId": target, "status": "CANCEL_REQUESTED", "legacy": scrub(legacy)}
    if execution and execution in CANCELLED and time.monotonic() - CANCELLED[execution] < 900:
        return {"cancelled": True, "executionId": execution, "status": "CANCELLED"}
    idem = str(params.get("idempotencyKey") or "").strip()
    if idem and method not in {"SarembokChat","Chat","SarembokDialogue","GetRuntimeInfo"}:
        cached = GUARD.idempotency.get(subject, method, idem)
        if cached is not None: return {**cached, "metadata": {**cached.get("metadata",{}), "idempotentReplay": True}}
    clean = {k:v for k,v in params.items() if not k.startswith("_srbk_")}
    started = time.perf_counter()
    result = ORIGINAL_DISPATCH(method, clean)
    if method == "RegisterWorker" and isinstance(result, dict):
        worker_id = str(result.get("workerId") or clean.get("workerId") or "").strip()
        if worker_id:
            result = dict(result)
            result["workerToken"] = secrets.token_urlsafe(32)
            ensure_worker_credentials()
            cloud.store.db.execute(f"INSERT OR REPLACE INTO {WORKER_TOKEN_TABLE}(worker_id,token_hash,created_at,last_used_at,revoked_at) VALUES(?,?,?,?,NULL)", (worker_id, worker_hash(result["workerToken"]), cloud.now(), cloud.now()))
            cloud.store.db.commit()
            result["workerTokenType"] = "enrollment_issued"
            result["capabilityTrust"] = "REPORTED"
            result["hardwareAttestation"] = "NOT_ATTESTED"
    if method == "ListWorkers":
        result = _annotate(result)
    if not isinstance(result, dict): result = {"value": result}
    result = scrub(dict(result))
    meta = result.get("metadata") if isinstance(result.get("metadata"),dict) else {}
    meta.update({"executionId":execution,"role":role,"durationMs":round((time.perf_counter()-started)*1000,1)})
    result["metadata"] = meta
    if idem and method not in {"SarembokChat","Chat","SarembokDialogue","GetRuntimeInfo"}: GUARD.idempotency.put(subject,method,idem,result)
    try: cloud.store.event(None,"RPC_EXECUTION",scrub({"executionId":execution,"method":method,"subject":subject,"role":role,"status":"SUCCEEDED","durationMs":meta["durationMs"]}))
    except Exception: pass
    return result


def _annotate(value: Any) -> Any:
    if isinstance(value,list): return [_annotate(x) for x in value]
    if isinstance(value,dict):
        out={k:_annotate(v) for k,v in value.items()}
        if any(k in out for k in ("gpu_model","gpuModel","gpu","cuda_version","cudaVersion")):
            out.setdefault("capabilityTrust","REPORTED"); out.setdefault("hardwareAttestation","NOT_ATTESTED")
        return out
    return value


def stream_callback(callback):
    execution = EXECUTION_ID.get()
    def guarded(text: str):
        if execution and time.monotonic() - CANCELLED.get(execution, -1e30) < 900: return
        callback(text)
    return ORIGINAL_SET_STREAM_CALLBACK(guarded)


async def handler(websocket):
    if not GUARD.origin_allowed(websocket):
        await websocket.close(code=1008, reason="origin_not_allowed"); return
    GUARD.allow_ip(websocket)
    return await ORIGINAL_HANDLER(websocket)


ensure_worker_credentials()
cloud.validate_request = validate
cloud.dispatch = dispatch
cloud.handler = handler
cloud.process_http_request = ORIGINAL_PROCESS_HTTP_REQUEST
runtime.set_stream_callback = stream_callback
runtime.reset_stream_callback = reset_stream_callback
runtime.cloud_server.handler = handler

if __name__ == "__main__": asyncio.run(cloud.main())
