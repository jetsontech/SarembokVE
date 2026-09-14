"""Hardened SarembokVE production entrypoint.

Loads the authoritative runtime/knowledge gateway, then installs a narrow
security and truth-boundary layer before the websocket server starts.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import knowledge_rpc_server

cloud = knowledge_rpc_server.cloud_server


def _require_admin_secret() -> str:
    secret = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
    if not secret:
        raise RuntimeError(
            "SAREMBOK_ADMIN_PASSCODE must be configured; "
            "refusing to start with a default credential"
        )
    if len(secret) < 16:
        raise RuntimeError("SAREMBOK_ADMIN_PASSCODE must be at least 16 characters")
    return secret


ADMIN_SECRET = _require_admin_secret()
cloud.ADMIN_PASSCODE = ADMIN_SECRET
cloud.ADMIN_ALLOWED_PASSCODES = {ADMIN_SECRET}

# Browser sessions are intentionally limited to public/read-safe operations.
# Sensitive mutation, worker-registration, administrative, identity, rental,
# and user-session methods require stronger authentication paths.
cloud.BROWSER_ALLOWED_METHODS = {
    "SarembokChat",
    "GetRuntimeInfo",
    "GetProviderMetrics",
    "BrowserNavigate",
    "BrowserScreenshot",
    "BrowserRender",
    "GetDigitalHumanSession",
    "ListDigitalHumanSessions",
    "GetFeedbackSummary",
    "SearchMemories",
    "ListMemories",
    "ListWorkers",
    "ListTasks",
    "GetVisualEngineStatus",
    "GetVisionStatus",
    "GetGpuMarketplace",
    "GetCurrentUser",
}


# Truth boundary: production worker inventory is registration/heartbeat based.
# Never synthesize hardware at runtime startup.
def _no_synthetic_worker() -> None:
    return None


cloud.ensure_sovereign_worker = _no_synthetic_worker

# Remove any previously persisted synthetic worker without touching real workers.
cloud.store.db.execute(
    "DELETE FROM workers WHERE worker_id='sarembok-edge-frontier-01'"
)
cloud.store.db.commit()


def _real_gpu_worker(required_capability: str = "gpu") -> str | None:
    return cloud.select_worker(required_capability)


def _hardened_dispatch(method: str, params: dict):
    if method == "ExecuteSandboxCode":
        raise PermissionError(
            "sandbox_execution_unavailable: runtime code execution requires an isolated worker boundary"
        )

    if method == "AuthenticateSocialUser":
        raise PermissionError(
            "social_auth_unavailable: provider identity verification is not configured"
        )

    if method in {"ListUserChatSessions", "SaveUserChatSession", "DeleteUserChatSession"}:
        raise PermissionError(
            "user_session_authentication_required: authenticated user identity is required"
        )

    if method in {"RentGpuNode", "ListGpuRentals"}:
        if method == "RentGpuNode":
            return {
                "status": "PENDING_PROVISIONING",
                "message": "GPU rental provisioning is not connected to a live allocation provider; no active rental is claimed.",
                "timestamp": cloud.now(),
            }
        return {"rentals": []}

    if method == "ExecuteComputeTask":
        task_type = str(params.get("taskType", "inference")).strip()
        payload = params.get("payload", {})
        worker_id = _real_gpu_worker("gpu")
        if not worker_id:
            task = cloud.store.create_task(
                task_type,
                None,
                payload if isinstance(payload, dict) else {},
            )
            return {
                "taskId": task["taskId"],
                "workerId": None,
                "status": "PENDING_WORKER",
                "taskType": task_type,
                "message": (
                    "No eligible GPU worker is online. Task is queued until "
                    "a registered worker becomes available."
                ),
                "timestamp": cloud.now(),
            }

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        stamp = cloud.now()
        cloud.store.db.execute(
            """
            INSERT INTO tasks (
                task_id, task_type, required_capability, payload,
                assigned_worker_id, status, created_at, updated_at
            ) VALUES (?, ?, 'gpu', ?, ?, 'QUEUED', ?, ?)
            """,
            (
                task_id,
                task_type,
                cloud.json.dumps(payload if isinstance(payload, dict) else {}),
                worker_id,
                stamp,
                stamp,
            ),
        )
        cloud.store.db.commit()
        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": "QUEUED",
            "taskType": task_type,
            "timestamp": stamp,
        }

    if method in {"VerifyAdminPasscode", "AuthenticateMaster"}:
        supplied = str(
            params.get("passcode")
            or params.get("adminPasscode")
            or params.get("authToken")
            or ""
        )
        if not supplied or not cloud.hmac.compare_digest(supplied, ADMIN_SECRET):
            raise PermissionError("invalid_admin_credentials")
        return {"authenticated": True, "status": "AUTHORIZED"}

    return knowledge_rpc_server._original_dispatch(method, params)


cloud.dispatch = _hardened_dispatch
knowledge_rpc_server.dispatch = _hardened_dispatch


if __name__ == "__main__":
    asyncio.run(cloud.main())
