"""Hardened SarembokVE production entrypoint, v2."""
from __future__ import annotations

import asyncio
import os
import uuid

import knowledge_rpc_server

cloud = knowledge_rpc_server.cloud_server

secret = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
if not secret:
    raise RuntimeError("SAREMBOK_ADMIN_PASSCODE must be configured; refusing to start with a default credential")
if len(secret) < 16:
    raise RuntimeError("SAREMBOK_ADMIN_PASSCODE must be at least 16 characters")

cloud.ADMIN_PASSCODE = secret
cloud.ADMIN_ALLOWED_PASSCODES = {secret}
cloud.BROWSER_ALLOWED_METHODS = {
    "SarembokChat", "GetRuntimeInfo", "GetProviderMetrics",
    "BrowserNavigate", "BrowserScreenshot", "BrowserRender",
    "GetDigitalHumanSession", "ListDigitalHumanSessions",
    "GetFeedbackSummary", "SearchMemories", "ListMemories",
    "ListWorkers", "ListTasks", "GetVisualEngineStatus",
    "GetVisionStatus", "GetGpuMarketplace", "GetCurrentUser",
}


def _no_synthetic_worker() -> None:
    return None


cloud.ensure_sovereign_worker = _no_synthetic_worker
cloud.store.db.execute("DELETE FROM workers WHERE worker_id='sarembok-edge-frontier-01'")
cloud.store.db.commit()


def _real_gpu_worker(capability: str = "gpu") -> str | None:
    return cloud.select_worker(capability)


def hardened_dispatch(method: str, params: dict):
    if method == "AdminExecuteDirective":
        raise PermissionError("admin_execution_unavailable: shell and Python execution require an isolated worker boundary")
    if method == "ExecuteSandboxCode":
        raise PermissionError("sandbox_execution_unavailable: runtime code execution requires an isolated worker boundary")
    if method == "AuthenticateSocialUser":
        raise PermissionError("social_auth_unavailable: provider identity verification is not configured")
    if method in {"ListUserChatSessions", "SaveUserChatSession", "DeleteUserChatSession"}:
        raise PermissionError("user_session_authentication_required: authenticated user identity is required")
    if method == "RentGpuNode":
        return {"status": "PENDING_PROVISIONING", "message": "No live GPU allocation provider is connected; no active rental is claimed.", "timestamp": cloud.now()}
    if method == "ListGpuRentals":
        return {"rentals": []}
    if method == "ExecuteComputeTask":
        task_type = str(params.get("taskType", "inference")).strip()
        payload = params.get("payload", {})
        worker_id = _real_gpu_worker("gpu")
        if not worker_id:
            task = cloud.store.create_task(task_type, None, payload if isinstance(payload, dict) else {})
            return {"taskId": task["taskId"], "workerId": None, "status": "PENDING_WORKER", "taskType": task_type,
                    "message": "No eligible GPU worker is online. Task is queued until a registered worker becomes available.", "timestamp": cloud.now()}
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        stamp = cloud.now()
        cloud.store.db.execute(
            "INSERT INTO tasks (task_id, task_type, required_capability, payload, assigned_worker_id, status, created_at, updated_at) VALUES (?, ?, 'gpu', ?, ?, 'QUEUED', ?, ?)",
            (task_id, task_type, cloud.json.dumps(payload if isinstance(payload, dict) else {}), worker_id, stamp, stamp),
        )
        cloud.store.db.commit()
        return {"taskId": task_id, "workerId": worker_id, "status": "QUEUED", "taskType": task_type, "timestamp": stamp}
    if method == "CreateDigitalHumanSession":
        agent_id = str(params.get("agentId", ""))
        cloud.require_agent(agent_id)
        worker_id = _real_gpu_worker("meta_human")
        if not worker_id:
            return {"sessionId": None, "agentId": agent_id, "assignedWorkerId": None, "status": "PENDING_WORKER",
                    "message": "No registered MetaHuman-capable worker is online."}
    if method == "GenerateImage":
        result = knowledge_rpc_server._original_dispatch(method, params)
        if isinstance(result, dict):
            result = dict(result)
            result["workerId"] = None
            result["executionMode"] = "provider_routed"
        return result
    if method == "GetVisualEngineStatus":
        result = knowledge_rpc_server._original_dispatch(method, params)
        if isinstance(result, dict):
            result = dict(result)
            tier3 = result.get("tier3_community")
            if isinstance(tier3, dict) and tier3.get("status") == "ONLINE":
                tier3 = dict(tier3)
                tier3["status"] = "AVAILABLE_IF_REACHABLE"
                result["tier3_community"] = tier3
        return result
    if method in {"VerifyAdminPasscode", "AuthenticateMaster"}:
        supplied = str(params.get("passcode") or params.get("adminPasscode") or params.get("authToken") or "")
        if not supplied or not cloud.hmac.compare_digest(supplied, secret):
            raise PermissionError("invalid_admin_credentials")
        return {"authenticated": True, "status": "AUTHORIZED"}
    return knowledge_rpc_server._original_dispatch(method, params)


cloud.dispatch = hardened_dispatch
knowledge_rpc_server.dispatch = hardened_dispatch

if __name__ == "__main__":
    asyncio.run(cloud.main())
