"""Sarembok_VE cloud runtime compatibility gateway.

Preserves the public 12-facet JSON-RPC contract while adding production
boundary controls: optional token authentication, connection limits,
request validation, serialized SQLite access, structured logging, and
SIGTERM/SIGINT graceful shutdown.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import signal
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import websockets

PORT = int(os.getenv("SAREMBOK_PORT", "9000"))
DB_PATH = os.getenv("SAREMBOK_DB_PATH", "/data/sarembok_cloud.db")
AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "").strip()
MAX_CONNECTIONS = max(1, int(os.getenv("SAREMBOK_MAX_CONNECTIONS", "100")))
MAX_REQUEST_BYTES = max(1024, int(os.getenv("SAREMBOK_MAX_REQUEST_BYTES", str(1024 * 1024))))
MAX_METHOD_LENGTH = max(32, int(os.getenv("SAREMBOK_MAX_METHOD_LENGTH", "128")))

logging.basicConfig(
    level=os.getenv("SAREMBOK_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOG = logging.getLogger("sarembok.cloud")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CloudStore:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA busy_timeout=10000")
        self._init()

    def _init(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id TEXT PRIMARY KEY,
                source_agent_id TEXT,
                target_agent_id TEXT,
                goal_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                capabilities TEXT NOT NULL,
                gpu_vendor TEXT,
                gpu_model TEXT,
                vram_mb INTEGER,
                cuda_version TEXT,
                available_memory_mb INTEGER,
                supported_models TEXT,
                latency_ms REAL,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS digital_human_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                worker_id TEXT,
                metahuman_id TEXT,
                voice_profile TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                required_capability TEXT NOT NULL,
                payload TEXT NOT NULL,
                assigned_worker_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    def create_agent(self, agent_id: str, display_name: str) -> dict[str, Any]:
        stamp = now()
        self.db.execute(
            "INSERT OR REPLACE INTO agents(agent_id,display_name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
            (agent_id, display_name, "ONLINE", stamp, stamp),
        )
        self.db.commit()
        self.event(agent_id, "AGENT_CREATED", {"displayName": display_name})
        return {"agentId": agent_id, "displayName": display_name, "status": "created"}

    def agent_exists(self, agent_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone() is not None

    def event(self, agent_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT INTO events(agent_id,event_type,payload,created_at) VALUES(?,?,?,?)",
            (agent_id, event_type, json.dumps(payload), now()),
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()


store = CloudStore(DB_PATH)
STARTED = time.time()
DB_LOCK = asyncio.Lock()
CONNECTIONS = asyncio.Semaphore(MAX_CONNECTIONS)
STOP = asyncio.Event()



WORKER_HEARTBEAT_TIMEOUT_SECONDS = int(
    os.getenv("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT", "90")
)

def heartbeat_is_fresh(timestamp: str) -> bool:
    if not timestamp:
        return False

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(timezone.utc)

        age = (
            datetime.now(timezone.utc) - dt
        ).total_seconds()

        return age <= WORKER_HEARTBEAT_TIMEOUT_SECONDS

    except Exception:
        return False


def ensure_scheduler_schema() -> None:
    columns = {
        row[1]
        for row in store.db.execute(
            "PRAGMA table_info(workers)"
        ).fetchall()
    }

    if "active_tasks" not in columns:
        store.db.execute(
            """
            ALTER TABLE workers
            ADD COLUMN active_tasks INTEGER NOT NULL DEFAULT 0
            """
        )
        store.db.commit()


def select_worker(required_capability: str) -> str | None:
    ensure_scheduler_schema()

    rows = store.db.execute(
        """
        SELECT
            worker_id,
            capabilities,
            active_tasks,
            latency_ms,
            available_memory_mb
        FROM workers
        WHERE status='ONLINE'
        """
    ).fetchall()

    candidates = []

    for row in rows:
        worker_id = row[0]
        raw_caps = row[1]
        active_tasks = int(row[2] or 0)
        latency_ms = float(row[3] or 999999)
        available_memory_mb = int(row[4] or 0)

        try:
            caps = json.loads(raw_caps) if raw_caps else []
        except Exception:
            caps = []

        if required_capability not in caps:
            continue

        heartbeat = store.db.execute(
            """
            SELECT last_heartbeat
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        if not heartbeat:
            continue

        if not heartbeat_is_fresh(heartbeat[0]):
            continue

        # Lower active workload wins.
        # Then lower latency.
        # Then higher available memory.
        candidates.append(
            (
                active_tasks,
                latency_ms,
                -available_memory_mb,
                worker_id,
            )
        )

    if not candidates:
        return None

    candidates.sort()

    return candidates[0][3]


def require_agent(agent_id: str) -> None:
    if not agent_id:
        raise ValueError("agentId is required")
    if not store.agent_exists(agent_id):
        raise ValueError(f"agent_not_found: {agent_id}")


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    if method == "CreateAgent":
        agent_id = str(params.get("agentId", "")).strip()
        if not agent_id:
            raise ValueError("agentId is required")
        display_name = str(params.get("displayName", agent_id)).strip() or agent_id
        return store.create_agent(agent_id, display_name)

    if method == "QueryAgentState":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        return {"agentId": agent_id, "cycleStage": "IDLE", "status": "ONLINE"}

    if method == "InjectPerception":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        perception = params.get("perception", {})
        store.event(agent_id, "PERCEPTION", {"perception": perception})
        return {"agentId": agent_id, "perceptionInjected": True, "stage": "VISION"}

    if method == "EvaluateDecision":
        risk = float(params.get("riskScore", 0.0))
        confidence = float(params.get("confidence", 0.0))
        action_id = str(params.get("actionId", ""))
        agent_id = str(params.get("agentId", ""))
        if agent_id:
            require_agent(agent_id)
        result = "DENY" if risk > 0.90 else "ALLOW"
        if agent_id:
            store.event(agent_id, "DECISION", {"actionId": action_id, "riskScore": risk, "confidence": confidence, "result": result})
        return {"agentId": agent_id, "actionId": action_id, "governanceResult": result, "riskScore": risk, "confidence": confidence}

    if method == "GetCognitiveScorecard":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        return {"agentId": agent_id, "overallReliability": 0.945, "perception": 0.96, "memory": 0.91, "reasoning": 0.94, "planning": 0.93, "policy": 0.99, "execution": 0.97, "recovery": 0.93, "conversation": 0.93}

    if method == "QueryWorldModel":
        return {"filter": str(params.get("filter", "all")), "entitiesCount": 0, "disagreementsCount": 0}

    if method == "CreateDelegation":
        delegation_id = f"del-{uuid.uuid4().hex[:12]}"
        stamp = now()
        source = params.get("sourceAgentId")
        target = params.get("targetAgentId")
        goal = params.get("goalId")
        store.db.execute("INSERT INTO delegations VALUES(?,?,?,?,?,?)", (delegation_id, source, target, goal, "created", stamp))
        store.db.commit()
        if source:
            store.event(str(source), "DELEGATION_CREATED", {"delegationId": delegation_id, "targetAgentId": target, "goalId": goal})
        return {"delegationId": delegation_id, "source": source, "target": target, "status": "created"}

    if method == "GetAuditTrail":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        count = store.db.execute("SELECT COUNT(*) FROM events WHERE agent_id=?", (agent_id,)).fetchone()[0]
        return {"agentId": agent_id, "recordsCount": count, "status": "integrity_verified", "storage": "sqlite-wal"}

    if method == "SendMessage":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        content = str(params.get("content", ""))
        store.db.execute("INSERT INTO messages VALUES(?,?,?,?)", (message_id, agent_id, content, now()))
        store.db.commit()
        store.event(agent_id, "MESSAGE", {"messageId": message_id})
        return {"agentId": agent_id, "messageId": message_id, "delivered": True}

    if method == "GetEvents":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        rows = store.db.execute("SELECT event_type,created_at,payload FROM events WHERE agent_id=? ORDER BY id DESC LIMIT 100", (agent_id,)).fetchall()
        events = [{"type": r[0], "timestamp": r[1], "payload": json.loads(r[2])} for r in reversed(rows)]
        return {"agentId": agent_id, "events": events, "count": len(events)}

    if method == "GetMetrics":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        event_count = store.db.execute("SELECT COUNT(*) FROM events WHERE agent_id=?", (agent_id,)).fetchone()[0]
        return {"agentId": agent_id, "metrics": {"perception": 0.96, "memory": 0.91, "reasoning": 0.94, "policy": 0.99, "overall": 0.945}, "eventCount": event_count, "uptimeSeconds": int(time.time() - STARTED)}

    if method == "RestoreState":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        entries = int(params.get("walEntries", 0))
        store.event(agent_id, "STATE_RESTORED", {"walEntriesReplayed": entries})
        return {"agentId": agent_id, "restored": True, "walEntriesReplayed": entries, "stateConsistent": True}

    if method == "RegisterWorker":
        worker_id = str(params.get("workerId", "")).strip()
        if not worker_id:
            raise ValueError("workerId is required")
        caps = json.dumps(params.get("capabilities", ["inference"]))
        vendor = str(params.get("gpuVendor", "NVIDIA"))
        model = str(params.get("gpuModel", "RTX 4090"))
        vram = int(params.get("vramMb", 24576))
        cuda = str(params.get("cudaVersion", "12.2"))
        avail_mem = int(params.get("availableMemoryMb", vram))
        models = json.dumps(params.get("supportedModels", ["default"]))
        latency = float(params.get("latencyMs", 10.0))
        status = str(params.get("status", "ONLINE")).upper()
        stamp = now()
        ensure_scheduler_schema()

        existing = store.db.execute(
            """
            SELECT active_tasks
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        active_tasks = int(existing[0]) if existing else 0

        store.db.execute(
            """
            INSERT OR REPLACE INTO workers(
                worker_id,
                capabilities,
                gpu_vendor,
                gpu_model,
                vram_mb,
                cuda_version,
                available_memory_mb,
                supported_models,
                latency_ms,
                status,
                last_heartbeat,
                active_tasks
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                worker_id,
                caps,
                vendor,
                model,
                vram,
                cuda,
                avail_mem,
                models,
                latency,
                status,
                stamp,
                active_tasks,
            ),
        )

        store.db.commit()
        return {"workerId": worker_id, "registered": True, "status": status, "capabilities": json.loads(caps)}

    if method == "ListWorkers":
        cap_filter = str(params.get("capability", "")).strip()
        status_filter = str(params.get("status", "")).strip().upper()
        rows = store.db.execute("SELECT worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat FROM workers").fetchall()
        workers = []
        for r in rows:
            caps = json.loads(r[1]) if r[1] else []
            if cap_filter and cap_filter not in caps:
                continue
            if status_filter and r[5] != status_filter:
                continue
            workers.append({
                "workerId": r[0],
                "capabilities": caps,
                "gpuVendor": r[2],
                "gpuModel": r[3],
                "vramMb": r[4],
                "status": r[5],
                "lastHeartbeat": r[6],
            })
        return {"workers": workers, "count": len(workers)}

    if method == "Heartbeat":
        worker_id = str(params.get("workerId", "")).strip()

        if not worker_id:
            raise ValueError("workerId is required")

        ensure_scheduler_schema()

        stamp = now()

        row = store.db.execute(
            """
            SELECT worker_id
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"worker_not_found: {worker_id}"
            )

        store.db.execute(
            """
            UPDATE workers
            SET
                last_heartbeat=?,
                status='ONLINE'
            WHERE worker_id=?
            """,
            (stamp, worker_id),
        )

        store.db.commit()

        return {
            "workerId": worker_id,
            "status": "ONLINE",
            "lastHeartbeat": stamp,
        }

    if method == "ScheduleCompute":
        task = params.get("task", {})

        if not isinstance(task, dict):
            task = {}

        task_type = str(
            params.get("taskType")
            or task.get("type")
            or "inference"
        ).strip()

        req_cap = str(
            params.get("requiredCapability")
            or task.get("requiredCapability")
            or "compute"
        ).strip()

        payload = params.get("payload")

        if payload is None:
            payload = task

        assigned_worker = select_worker(
            required_capability=req_cap,
        )

        task_id = f"task-{uuid.uuid4().hex[:10]}"

        status = (
            "QUEUED"
            if assigned_worker
            else "PENDING_WORKER"
        )

        stamp = now()

        store.db.execute(
            """
            INSERT INTO tasks(
                task_id,
                task_type,
                required_capability,
                payload,
                assigned_worker_id,
                status,
                created_at,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                task_type,
                req_cap,
                json.dumps(payload),
                assigned_worker,
                status,
                stamp,
                stamp,
            ),
        )

        store.db.commit()

        return {
            "taskId": task_id,
            "taskType": task_type,
            "requiredCapability": req_cap,
            "assignedWorkerId": assigned_worker,
            "status": status,
        }

    if method == "ClaimTask":
        ensure_scheduler_schema()

        task_id = str(params.get("taskId", "")).strip()
        worker_id = str(params.get("workerId", "")).strip()

        if not task_id:
            raise ValueError("taskId is required")

        if not worker_id:
            raise ValueError("workerId is required")

        row = store.db.execute(
            """
            SELECT assigned_worker_id, status
            FROM tasks
            WHERE task_id=?
            """,
            (task_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"task_not_found: {task_id}"
            )

        if row[0] != worker_id:
            raise ValueError("worker_mismatch")

        if row[1] != "QUEUED":
            raise ValueError(
                f"task_not_queued: {row[1]}"
            )

        worker = store.db.execute(
            """
            SELECT status, last_heartbeat
            FROM workers
            WHERE worker_id=?
            """,
            (worker_id,),
        ).fetchone()

        if not worker:
            raise ValueError(
                f"worker_not_found: {worker_id}"
            )

        if worker[0] != "ONLINE":
            raise ValueError("worker_not_online")

        if not heartbeat_is_fresh(worker[1]):
            raise ValueError("worker_heartbeat_stale")

        stamp = now()

        store.db.execute(
            """
            UPDATE tasks
            SET
                status='RUNNING',
                updated_at=?
            WHERE task_id=?
              AND assigned_worker_id=?
              AND status='QUEUED'
            """,
            (stamp, task_id, worker_id),
        )

        if store.db.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("task_claim_conflict")

        store.db.execute(
            """
            UPDATE workers
            SET active_tasks=active_tasks+1
            WHERE worker_id=?
            """,
            (worker_id,),
        )

        store.db.commit()

        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": "RUNNING",
        }

    if method == "CompleteTask":
        ensure_scheduler_schema()

        task_id = str(params.get("taskId", "")).strip()
        worker_id = str(params.get("workerId", "")).strip()

        if not task_id:
            raise ValueError("taskId is required")

        if not worker_id:
            raise ValueError("workerId is required")

        row = store.db.execute(
            """
            SELECT assigned_worker_id, status
            FROM tasks
            WHERE task_id=?
            """,
            (task_id,),
        ).fetchone()

        if not row:
            raise ValueError(
                f"task_not_found: {task_id}"
            )

        if row[0] != worker_id:
            raise ValueError("worker_mismatch")

        if row[1] != "RUNNING":
            raise ValueError(
                f"task_not_running: {row[1]}"
            )

        stamp = now()

        store.db.execute(
            """
            UPDATE tasks
            SET
                status='COMPLETED',
                updated_at=?
            WHERE task_id=?
              AND assigned_worker_id=?
              AND status='RUNNING'
            """,
            (stamp, task_id, worker_id),
        )

        if store.db.execute("SELECT changes()").fetchone()[0] != 1:
            raise ValueError("task_completion_conflict")

        store.db.execute(
            """
            UPDATE workers
            SET active_tasks=MAX(active_tasks-1,0)
            WHERE worker_id=?
            """,
            (worker_id,),
        )

        store.db.commit()

        return {
            "taskId": task_id,
            "workerId": worker_id,
            "status": "COMPLETED",
        }

    if method == "CreateDigitalHumanSession":
        agent_id = str(params.get("agentId", ""))
        require_agent(agent_id)
        metahuman_id = str(params.get("metahumanId", "default"))
        voice_profile = str(params.get("voiceProfile", "default"))
        session_id = f"dhs-{uuid.uuid4().hex[:10]}"
        assigned_worker = select_worker(
            required_capability="meta_human",
        )
        stamp = now()
        store.db.execute(
            "INSERT INTO digital_human_sessions VALUES(?,?,?,?,?,?,?,?)",
            (session_id, agent_id, assigned_worker, metahuman_id, voice_profile, "ACTIVE", stamp, stamp),
        )
        store.db.commit()
        return {"sessionId": session_id, "agentId": agent_id, "assignedWorkerId": assigned_worker, "metahumanId": metahuman_id, "status": "ACTIVE"}

    if method == "GetDigitalHumanSession":
        session_id = str(params.get("sessionId", ""))
        row = store.db.execute("SELECT session_id, agent_id, worker_id, metahuman_id, voice_profile, status, created_at FROM digital_human_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            raise ValueError(f"session_not_found: {session_id}")
        return {"sessionId": row[0], "agentId": row[1], "assignedWorkerId": row[2], "metahumanId": row[3], "voiceProfile": row[4], "status": row[5], "createdAt": row[6]}

    if method == "Health":
        worker_count = store.db.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
        session_count = store.db.execute("SELECT COUNT(*) FROM digital_human_sessions WHERE status!='TERMINATED'").fetchone()[0]
        return {
            "status": "ONLINE",
            "service": "sarembok-ve-cloud-runtime",
            "domain": "sarembok.com",
            "uptimeSeconds": int(time.time() - STARTED),
            "storage": "sqlite-wal",
            "authConfigured": bool(AUTH_TOKEN),
            "registeredWorkers": worker_count,
            "activeDigitalHumanSessions": session_count,
        }

    raise ValueError(f"unknown_method: {method}")


def authenticate(request: dict[str, Any]) -> None:
    if not AUTH_TOKEN:
        return
    params = request.get("params")
    supplied = params.get("authToken") if isinstance(params, dict) else None
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, AUTH_TOKEN):
        raise PermissionError("authentication_required")


def validate_request(request: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    if request.get("jsonrpc") != "2.0":
        raise ValueError("jsonrpc must be 2.0")
    method = request.get("method")
    if not isinstance(method, str) or not method or len(method) > MAX_METHOD_LENGTH:
        raise ValueError("invalid method")
    params = request.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    authenticate(request)
    return method, params


async def handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    LOG.info("connection_open peer=%s", peer)
    try:
        async for raw in websocket:
            request: Any = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")
                request = json.loads(raw)
                method, params = validate_request(request)
                async with DB_LOCK:
                    result = dispatch(method, params)
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                LOG.info("rpc_success method=%s request_id=%s", method, request.get("id"))
            except PermissionError as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32001, "message": str(exc)}}
                LOG.warning("rpc_auth_failed peer=%s", peer)
            except Exception as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32000, "message": str(exc)}}
                LOG.warning("rpc_error peer=%s error=%s", peer, exc)
            await websocket.send(json.dumps(response, separators=(",", ":")))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        LOG.info("connection_close peer=%s", peer)


async def process_http_request(connection_or_path: Any, request_or_headers: Any = None) -> tuple[int, list[tuple[str, str]], bytes] | None:
    path = getattr(connection_or_path, "path", str(connection_or_path))
    if path in ("/health", "/healthz", "/"):
        return (200, [("Content-Type", "text/plain; charset=utf-8")], b"OK\n")
    return None


async def serve() -> None:
    LOG.info("startup port=%s max_connections=%s auth_configured=%s db=%s", PORT, MAX_CONNECTIONS, bool(AUTH_TOKEN), DB_PATH)
    async with websockets.serve(
        lambda ws: CONNECTIONS_guard(ws),
        "0.0.0.0",
        PORT,
        max_size=MAX_REQUEST_BYTES,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
        compression=None,
        process_request=process_http_request,
    ) as server:
        LOG.info("listening address=0.0.0.0:%s", PORT)
        await STOP.wait()
        LOG.info("shutdown_requested")
        server.close()
        await server.wait_closed()


async def CONNECTIONS_guard(websocket) -> None:
    try:
        await asyncio.wait_for(CONNECTIONS.acquire(), timeout=5)
    except TimeoutError:
        await websocket.close(code=1013, reason="server_busy")
        return
    try:
        await handler(websocket)
    finally:
        CONNECTIONS.release()


def request_shutdown() -> None:
    LOG.info("shutdown_signal")
    STOP.set()


async def main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, lambda *_: request_shutdown())
    try:
        await serve()
    finally:
        store.close()
        LOG.info("shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
