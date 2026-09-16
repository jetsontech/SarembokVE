"""SarembokVE frontier production boundary."""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Any

import knowledge_rpc_server as runtime
from production_guard_v2 import CANCELLATION_METHODS, METHOD_REQUIREMENTS, ProductionGuard, scrub
from provider_router import reset_stream_callback, set_stream_callback
from frontier_runtime_policy import apply as apply_frontier_policy

cloud = runtime.cloud_server
GUARD = ProductionGuard()
CURRENT_EXECUTION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_execution_id", default="")
CURRENT_SUBJECT: contextvars.ContextVar[str] = contextvars.ContextVar("sarembok_subject", default="anonymous")
DB_GUARD = threading.Lock()
EXECUTION_TABLE = "rpc_execution_ledger"
IDEMPOTENCY_TABLE = "rpc_idempotency"
WORKER_TOKEN_TABLE = "worker_credentials"
_MUTATING_EXCLUSIONS = {"SarembokChat", "Chat", "SarembokDialogue", "GetRuntimeInfo"}

# Apply production policy before capturing the HTTP handler so the restricted
# handler cannot be overwritten by the compatibility runtime.
apply_frontier_policy(runtime)

ORIGINAL_VALIDATE = cloud.validate_request
ORIGINAL_DISPATCH = cloud.dispatch
ORIGINAL_HANDLER = cloud.handler
ORIGINAL_PROCESS_HTTP_REQUEST = cloud.process_http_request
ORIGINAL_SET_STREAM_CALLBACK = set_stream_callback

_admin_passcode = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
cloud.ADMIN_PASSCODE = _admin_passcode
cloud.ADMIN_ALLOWED_PASSCODES = {_admin_passcode} if _admin_passcode else set()


def _init_security_schema() -> None:
    with DB_GUARD:
        cloud.store.db.execute(f"CREATE TABLE IF NOT EXISTS {WORKER_TOKEN_TABLE}(worker_id TEXT PRIMARY KEY,token_hash TEXT NOT NULL,created_at TEXT NOT NULL,last_used_at TEXT,revoked_at TEXT)")
        cloud.store.db.execute(f"CREATE TABLE IF NOT EXISTS {EXECUTION_TABLE}(execution_id TEXT PRIMARY KEY,subject TEXT NOT NULL,role TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        cloud.store.db.execute(f"CREATE TABLE IF NOT EXISTS {IDEMPOTENCY_TABLE}(subject TEXT NOT NULL,method TEXT NOT NULL,idempotency_key TEXT NOT NULL,response_json TEXT NOT NULL,expires_at REAL NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(subject,method,idempotency_key))")
        cloud.store.db.commit()


def _worker_token_hash(token: str) -> str:
    salt = os.getenv("SAREMBOK_WORKER_TOKEN_HASH_SALT", "").strip().encode("utf-8")
    return hashlib.sha256(salt + token.encode("utf-8")).hexdigest()


def _browser_session_valid(token: str) -> bool:
    if not token:
        return False
    sessions = getattr(cloud, "BROWSER_SESSIONS", {})
    expiry = sessions.get(token)
    if not expiry or float(expiry) <= time.time():
        sessions.pop(token, None)
        return False
    return True


def _worker_token_valid(worker_id: str, token: str) -> bool:
    if not worker_id or not token:
        return False
    row = cloud.store.db.execute(f"SELECT token_hash,revoked_at FROM {WORKER_TOKEN_TABLE} WHERE worker_id=?", (worker_id,)).fetchone()
    if not row or row[1]:
        return False
    ok = hmac.compare_digest(str(row[0]), _worker_token_hash(token))
    if ok:
        cloud.store.db.execute(f"UPDATE {WORKER_TOKEN_TABLE} SET last_used_at=? WHERE worker_id=?", (cloud.now(), worker_id))
        cloud.store.db.commit()
    return ok


def _identity(method: str, params: dict[str, Any]) -> tuple[str, str]:
    if method == "RegisterWorker":
        enrollment = str(params.get("enrollmentToken") or "").strip()
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        if configured and enrollment and hmac.compare_digest(configured, enrollment):
            return "WORKER", str(params.get("workerId") or "registration").strip() or "registration"
        return "PUBLIC", "anonymous"
    token = str(params.get("sessionToken") or params.get("authToken") or "").strip()
    if _browser_session_valid(token):
        return "USER", f"browser:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}"
    master = os.getenv("SAREMBOK_MASTER_TOKEN", "").strip()
    admin = os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()
    operator = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
    if master and token and hmac.compare_digest(token, master): return "MASTER", "master"
    if admin and token and hmac.compare_digest(token, admin): return "ADMIN", "admin"
    if operator and token and hmac.compare_digest(token, operator): return "OPERATOR", "operator"
    worker_id = str(params.get("workerId") or "").strip()
    worker_token = str(params.get("workerToken") or "").strip()
    if _worker_token_valid(worker_id, worker_token): return "WORKER", worker_id
    return "PUBLIC", "anonymous"


def _required_role(method: str) -> str | None:
    if method == "ping" or method in {"AuthenticateMaster", "AuthenticateSocialUser"}: return None
    if method == "VerifyAdminPasscode": return "ADMIN"
    return METHOD_REQUIREMENTS.get(method, "ADMIN")


def _level(role: str) -> int:
    return {"PUBLIC":0,"USER":1,"WORKER":2,"OPERATOR":3,"ADMIN":4,"MASTER":5,"SYSTEM":6}.get(role,0)


def _validate(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    # Do not call legacy validate_request: it requires the legacy bearer token
    # before the frontier worker-token path can authenticate server-to-server nodes.
    if not isinstance(request, dict): raise ValueError("request must be a JSON object")
    if request.get("jsonrpc") != "2.0": raise ValueError("jsonrpc must be 2.0")
    method = request.get("method")
    if not isinstance(method, str) or not method or len(method) > 128: raise ValueError("invalid method")
    raw_params = request.get("params") or {}
    if not isinstance(raw_params, dict): raise ValueError("params must be an object")
    params = dict(raw_params)
    role, subject = _identity(method, params)

    if method == "VerifyAdminPasscode":
        configured = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
        supplied = str(params.get("passcode") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(supplied, configured): raise PermissionError("invalid_admin_credentials")
        role, subject = "ADMIN", "admin-passcode"
    else:
        required = _required_role(method)
        if required is not None and _level(role) < _level(required):
            raise PermissionError("authenticated_session_required" if role == "PUBLIC" else "insufficient_privilege")

    if method == "RegisterWorker":
        configured = os.getenv("SAREMBOK_WORKER_ENROLLMENT_TOKEN", "").strip()
        supplied = str(params.get("enrollmentToken") or "").strip()
        if not configured or not supplied or not hmac.compare_digest(supplied, configured): raise PermissionError("worker_enrollment_required")
    if role == "WORKER" and method in {"Heartbeat","ClaimTask","CompleteTask","FailTask"}:
        requested_worker = str(params.get("workerId") or "").strip()
        if not requested_worker or requested_worker != subject: raise PermissionError("worker_identity_mismatch")

    execution_id = str(request.get("id") or f"rpc-{time.time_ns()}")
    if len(execution_id) > 128: raise ValueError("execution_id_too_long")
    idem = str(params.get("idempotencyKey") or "").strip()
    if len(idem) > 128: raise ValueError("idempotency_key_too_long")
    params["executionId"] = execution_id
    params["_sarembokRole"] = role
    params["_sarembokSubject"] = subject
    CURRENT_EXECUTION_ID.set(execution_id)
    CURRENT_SUBJECT.set(subject)
    now_stamp = cloud.now()
    with DB_GUARD:
        cloud.store.db.execute(f"INSERT OR REPLACE INTO {EXECUTION_TABLE}(execution_id,subject,role,status,created_at,updated_at) VALUES(?,?,?,?,?,?)", (execution_id,subject,role,"ACCEPTED",now_stamp,now_stamp))
        cloud.store.db.commit()
    GUARD.allow_subject(GUARD.identify(params, browser_session_valid=(role == "USER")))
    return method, params


def _get_idempotent(subject: str, method: str, key: str) -> dict[str, Any] | None:
    if not key or method in _MUTATING_EXCLUSIONS: return None
    row = cloud.store.db.execute(f"SELECT response_json,expires_at FROM {IDEMPOTENCY_TABLE} WHERE subject=? AND method=? AND idempotency_key=?", (subject,method,key)).fetchone()
    if not row: return None
    if float(row[1]) <= time.time():
        cloud.store.db.execute(f"DELETE FROM {IDEMPOTENCY_TABLE} WHERE subject=? AND method=? AND idempotency_key=?", (subject,method,key)); cloud.store.db.commit(); return None
    try:
        value=json.loads(row[0])
        if isinstance(value,dict):
            value.setdefault("metadata",{})["idempotentReplay"]=True
            return value
    except (TypeError,ValueError,json.JSONDecodeError): pass
    return None


def _put_idempotent(subject: str, method: str, key: str, value: dict[str, Any]) -> None:
    if not key or method in _MUTATING_EXCLUSIONS: return
    ttl=max(30,min(86400,int(os.getenv("SAREMBOK_IDEMPOTENCY_TTL_SECONDS","300"))))
    cloud.store.db.execute(f"INSERT OR REPLACE INTO {IDEMPOTENCY_TABLE}(subject,method,idempotency_key,response_json,expires_at,created_at) VALUES(?,?,?,?,?,?)", (subject,method,key,json.dumps(value,separators=(",",":"),ensure_ascii=False),time.time()+ttl,cloud.now()))
    cloud.store.db.commit()


def _dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    execution_id=str(params.get("executionId") or CURRENT_EXECUTION_ID.get())
    subject=str(params.get("_sarembokSubject") or CURRENT_SUBJECT.get() or "anonymous")
    role=str(params.get("_sarembokRole") or "PUBLIC")
    idem=str(params.get("idempotencyKey") or "").strip()
    if method in CANCELLATION_METHODS:
        target=str(params.get("requestId") or params.get("executionId") or "").strip()
        owner_row=cloud.store.db.execute(f"SELECT subject,status FROM {EXECUTION_TABLE} WHERE execution_id=?",(target,)).fetchone()
        if not owner_row: raise PermissionError("unknown_execution")
        owner,status=str(owner_row[0]),str(owner_row[1])
        if owner != subject and role not in {"ADMIN","MASTER","SYSTEM"}: raise PermissionError("cannot_cancel_other_principal")
        cloud.store.db.execute(f"UPDATE {EXECUTION_TABLE} SET status='CANCEL_REQUESTED',updated_at=? WHERE execution_id=?",(cloud.now(),target)); cloud.store.db.commit()
        try: legacy=ORIGINAL_DISPATCH("CancelActiveStream",{"requestId":target})
        except Exception: legacy={"cancelled":True}
        return {"cancelled":True,"executionId":target,"status":"CANCEL_REQUESTED","legacy":scrub(legacy),"previousStatus":status}
    cached=_get_idempotent(subject,method,idem)
    if cached is not None: return cached
    if role=="WORKER" and method=="ExecuteComputeTask": raise PermissionError("direct_compute_execution_disabled_use_worker_task_protocol")
    clean_params={k:v for k,v in params.items() if not k.startswith("_sarembok") and k not in {"enrollmentToken","workerToken","authToken","sessionToken"}}
    started=time.perf_counter()
    try:
        result=ORIGINAL_DISPATCH(method,clean_params)
        if not isinstance(result,dict): result={"value":result}
        result=scrub(dict(result))
        if method=="RegisterWorker":
            worker_id=str(result.get("workerId") or clean_params.get("workerId") or "").strip()
            if worker_id:
                issued=secrets.token_urlsafe(32)
                cloud.store.db.execute(f"INSERT OR REPLACE INTO {WORKER_TOKEN_TABLE}(worker_id,token_hash,created_at,last_used_at,revoked_at) VALUES(?,?,?,?,NULL)",(worker_id,_worker_token_hash(issued),cloud.now(),cloud.now()))
                cloud.store.db.commit()
                result.update({"workerToken":issued,"workerTokenType":"enrollment_issued_once","capabilityTrust":"REPORTED","hardwareAttestation":"NOT_ATTESTED"})
        if method=="ListWorkers": result=_annotate_workers(result)
        if method=="GenerateImage":
            image=result.get("image")
            if isinstance(image,dict): image.pop("workerId",None); image["capabilityTrust"]="PROVIDER_REPORTED"
        if method=="GetGpuMarketplace": result["marketplaceTrust"]="CATALOG_ONLY_NO_COMPUTE_CAPACITY_ASSERTION"
        if method=="RentGpuNode": result.update({"status":"REQUEST_RECORDED","executionSemantics":"lease_record_only; no hardware allocation is asserted"})
        metadata=result.get("metadata") if isinstance(result.get("metadata"),dict) else {}
        metadata.update({"executionId":execution_id,"role":role,"subject":subject,"durationMs":round((time.perf_counter()-started)*1000,1)})
        result["metadata"]=metadata
        _put_idempotent(subject,method,idem,result)
        cloud.store.db.execute(f"UPDATE {EXECUTION_TABLE} SET status='SUCCEEDED',updated_at=? WHERE execution_id=?",(cloud.now(),execution_id)); cloud.store.db.commit()
        try: cloud.store.event(None,"RPC_EXECUTION",scrub({"executionId":execution_id,"method":method,"subject":subject,"role":role,"status":"SUCCEEDED","durationMs":metadata["durationMs"]}))
        except Exception: pass
        return result
    except Exception as exc:
        try:
            cloud.store.db.execute(f"UPDATE {EXECUTION_TABLE} SET status='FAILED',updated_at=? WHERE execution_id=?",(cloud.now(),execution_id)); cloud.store.db.commit()
            cloud.store.event(None,"RPC_EXECUTION",scrub({"executionId":execution_id,"method":method,"subject":subject,"role":role,"status":"FAILED","error":str(exc)}))
        except Exception: pass
        raise


def _annotate_workers(value: Any) -> Any:
    if isinstance(value,list): return [_annotate_workers(x) for x in value]
    if isinstance(value,dict):
        out={k:_annotate_workers(v) for k,v in value.items()}
        if any(k in out for k in ("gpu_model","gpuModel","gpu","cuda_version","cudaVersion")):
            out.setdefault("capabilityTrust","REPORTED"); out.setdefault("hardwareAttestation","NOT_ATTESTED")
        return out
    return value


def _stream_callback(callback):
    execution_id=CURRENT_EXECUTION_ID.get()
    def guarded(text:str):
        row=cloud.store.db.execute(f"SELECT status FROM {EXECUTION_TABLE} WHERE execution_id=?",(execution_id,)).fetchone() if execution_id else None
        if row and str(row[0]) in {"CANCEL_REQUESTED","CANCELLED"}: return
        callback(text)
    return ORIGINAL_SET_STREAM_CALLBACK(guarded)


async def _handler(websocket):
    if not GUARD.origin_allowed(websocket):
        await websocket.close(code=1008,reason="origin_not_allowed"); return
    GUARD.allow_ip(websocket)
    return await ORIGINAL_HANDLER(websocket)


_init_security_schema()
cloud.validate_request=_validate
cloud.dispatch=_dispatch
cloud.handler=_handler
runtime.set_stream_callback=_stream_callback
runtime.reset_stream_callback=reset_stream_callback
runtime.cloud_server.handler=_handler
# Keep the restricted process_http_request installed by frontier_runtime_policy.
if __name__ == "__main__": asyncio.run(cloud.main())
