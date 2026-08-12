"""Scheduler V3 for the Sarembok cloud runtime.

This module is intentionally layered on top of the frozen Scheduler V2
runtime. It adds durable worker leases, capacity-aware placement, retry and
failure states, task results, stale-worker recovery, and scheduler metrics.
All mutations are expected to run under the runtime's DB_LOCK.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

LOG = logging.getLogger("sarembok.scheduler.v3")

NOT_HANDLED = object()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def epoch() -> float:
    return time.time()


def iso_after(seconds: int) -> str:
    return datetime.fromtimestamp(epoch() + seconds, timezone.utc).isoformat()


def fresh(value: str | None, timeout: int) -> bool:
    if not value:
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() <= timeout
    except Exception:
        return False


class SchedulerV3:
    def __init__(self, store: Any):
        self.store = store
        self.db = store.db
        self.heartbeat_timeout = max(15, int(__import__("os").getenv("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT", "90")))
        self.default_lease = max(15, int(__import__("os").getenv("SAREMBOK_TASK_LEASE_SECONDS", "300")))
        self.max_attempts_default = max(1, int(__import__("os").getenv("SAREMBOK_TASK_MAX_ATTEMPTS", "3")))
        self.retry_delay = max(1, int(__import__("os").getenv("SAREMBOK_TASK_RETRY_DELAY_SECONDS", "5")))
        self.initialized = False
        self._ensure_schema()

    def _columns(self, table: str) -> set[str]:
        return {r[1] for r in self.db.execute(f"PRAGMA table_info({table})").fetchall()}

    def _add_column(self, table: str, name: str, definition: str) -> None:
        if name not in self._columns(table):
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _ensure_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS scheduler_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            worker_id TEXT,
            task_id TEXT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scheduler_events_created ON scheduler_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_worker_status ON tasks(assigned_worker_id,status);
        """)
        for name, definition in [
            ("max_concurrent_tasks", "INTEGER NOT NULL DEFAULT 1"),
            ("queued_tasks", "INTEGER NOT NULL DEFAULT 0"),
            ("lease_expires_at", "TEXT"),
            ("last_disconnect_at", "TEXT"),
        ]:
            self._add_column("workers", name, definition)
        for name, definition in [
            ("attempt_count", "INTEGER NOT NULL DEFAULT 0"),
            ("max_attempts", f"INTEGER NOT NULL DEFAULT {self.max_attempts_default}"),
            ("lease_expires_at", "TEXT"),
            ("result", "TEXT"),
            ("error", "TEXT"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT"),
            ("idempotency_key", "TEXT"),
            ("retry_at", "TEXT"),
        ]:
            self._add_column("tasks", name, definition)
        self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
        self.db.execute("UPDATE workers SET max_concurrent_tasks=1 WHERE max_concurrent_tasks IS NULL OR max_concurrent_tasks<1")
        self.db.execute("UPDATE workers SET queued_tasks=0 WHERE queued_tasks IS NULL OR queued_tasks<0")
        self.db.commit()
        self.initialized = True

    def _event(self, event_type: str, worker_id: str | None = None, task_id: str | None = None, **payload: Any) -> None:
        self.db.execute(
            "INSERT INTO scheduler_events(event_type,worker_id,task_id,payload,created_at) VALUES(?,?,?,?,?)",
            (event_type, worker_id, task_id, json.dumps(payload, separators=(",", ":")), utcnow()),
        )

    def _worker(self, worker_id: str):
        return self.db.execute(
            "SELECT worker_id,status,last_heartbeat,active_tasks,queued_tasks,max_concurrent_tasks,lease_expires_at,available_memory_mb,latency_ms,capabilities,supported_models FROM workers WHERE worker_id=?",
            (worker_id,),
        ).fetchone()

    def _worker_can_run(self, row: Any, capability: str) -> bool:
        if not row or row[1] != "ONLINE" or not fresh(row[2], self.heartbeat_timeout):
            return False
        try:
            caps = json.loads(row[9] or "[]")
        except Exception:
            caps = []
        if capability not in caps:
            return False
        return int(row[4] or 0) + int(row[3] or 0) < max(1, int(row[5] or 1))

    def _select_worker(self, capability: str, payload: Any = None) -> str | None:
        rows = self.db.execute(
            "SELECT worker_id,status,last_heartbeat,active_tasks,queued_tasks,max_concurrent_tasks,lease_expires_at,available_memory_mb,latency_ms,capabilities,supported_models FROM workers WHERE status='ONLINE'"
        ).fetchall()
        model = payload.get("model") if isinstance(payload, dict) else None
        candidates = []
        for row in rows:
            if not self._worker_can_run(row, capability):
                continue
            if model:
                try:
                    models = json.loads(row[10] or "[]")
                except Exception:
                    models = []
                if model not in models and "default" not in models:
                    continue
            load = int(row[3] or 0) + int(row[4] or 0)
            candidates.append((load, float(row[8] or 999999), -int(row[7] or 0), row[0]))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][3]

    def _requeue_task(self, task_id: str, reason: str) -> str:
        row = self.db.execute("SELECT assigned_worker_id,attempt_count,max_attempts,status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return "NOT_FOUND"
        worker_id, attempts, max_attempts, status = row
        if status not in ("RUNNING", "LEASE_EXPIRED"):
            return status
        attempts = int(attempts or 0)
        max_attempts = int(max_attempts or self.max_attempts_default)
        if worker_id:
            self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?", (worker_id,))
        if attempts < max_attempts:
            retry_at = iso_after(self.retry_delay)
            self.db.execute("UPDATE tasks SET status='RETRY_WAIT',retry_at=?,lease_expires_at=NULL,error=?,updated_at=? WHERE task_id=?", (retry_at, reason, utcnow(), task_id))
            self._event("TASK_RETRY_SCHEDULED", worker_id, task_id, attempt=attempts, maxAttempts=max_attempts, retryAt=retry_at, reason=reason)
            return "RETRY_WAIT"
        self.db.execute("UPDATE tasks SET status='FAILED',lease_expires_at=NULL,error=?,completed_at=?,updated_at=? WHERE task_id=?", (reason, utcnow(), utcnow(), task_id))
        self._event("TASK_FAILED", worker_id, task_id, attempts=attempts, reason=reason)
        return "FAILED"

    def reap(self) -> dict[str, int]:
        """Expire stale worker leases and task leases, and make retryable work visible."""
        self._ensure_schema()
        now_value = utcnow()
        stale_workers = 0
        expired_tasks = 0
        retried = 0
        rows = self.db.execute("SELECT worker_id,status,last_heartbeat FROM workers WHERE status='ONLINE'").fetchall()
        for row in rows:
            if not fresh(row[2], self.heartbeat_timeout):
                self.db.execute("UPDATE workers SET status='STALE',last_disconnect_at=? WHERE worker_id=?", (now_value, row[0]))
                self._event("WORKER_STALE", row[0], None, heartbeat=row[2])
                stale_workers += 1
                task_rows = self.db.execute("SELECT task_id FROM tasks WHERE assigned_worker_id=? AND status='RUNNING'", (row[0],)).fetchall()
                for task in task_rows:
                    result = self._requeue_task(task[0], "worker_heartbeat_stale")
                    expired_tasks += 1
                    retried += int(result == "RETRY_WAIT")
        lease_rows = self.db.execute("SELECT task_id,assigned_worker_id FROM tasks WHERE status='RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?", (now_value,)).fetchall()
        for task in lease_rows:
            result = self._requeue_task(task[0], "task_lease_expired")
            expired_tasks += 1
            retried += int(result == "RETRY_WAIT")
        self.db.execute("UPDATE tasks SET status='QUEUED',retry_at=NULL,updated_at=? WHERE status='RETRY_WAIT' AND retry_at IS NOT NULL AND retry_at<=?", (now_value, now_value))
        self._assign_pending()
        self.db.commit()
        return {"staleWorkers": stale_workers, "expiredTasks": expired_tasks, "retryScheduled": retried}

    def _assign_pending(self) -> int:
        assigned = 0
        rows = self.db.execute("SELECT task_id,required_capability,payload FROM tasks WHERE status IN ('PENDING_WORKER','QUEUED') AND assigned_worker_id IS NULL ORDER BY created_at LIMIT 100").fetchall()
        for row in rows:
            try:
                payload = json.loads(row[2] or "{}")
            except Exception:
                payload = {}
            worker_id = self._select_worker(row[1], payload)
            if not worker_id:
                continue
            self.db.execute("UPDATE tasks SET assigned_worker_id=?,status='QUEUED',updated_at=? WHERE task_id=? AND assigned_worker_id IS NULL", (worker_id, utcnow(), row[0]))
            self.db.execute("UPDATE workers SET queued_tasks=queued_tasks+1 WHERE worker_id=?", (worker_id,))
            self._event("TASK_ASSIGNED", worker_id, row[0], capability=row[1])
            assigned += 1
        return assigned

    def register_worker(self, params: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(params.get("workerId", "")).strip()
        if not worker_id:
            raise ValueError("workerId is required")
        caps = json.dumps(params.get("capabilities", ["inference"]))
        models = json.dumps(params.get("supportedModels", ["default"]))
        max_tasks = max(1, int(params.get("maxConcurrentTasks", params.get("concurrency", 1))))
        stamp = utcnow()
        existing = self.db.execute("SELECT active_tasks,queued_tasks FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
        active = int(existing[0]) if existing else 0
        queued = int(existing[1]) if existing else 0
        self.db.execute("""
            INSERT INTO workers(worker_id,capabilities,gpu_vendor,gpu_model,vram_mb,cuda_version,available_memory_mb,supported_models,latency_ms,status,last_heartbeat,active_tasks,max_concurrent_tasks,queued_tasks,lease_expires_at,last_disconnect_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)
            ON CONFLICT(worker_id) DO UPDATE SET capabilities=excluded.capabilities,gpu_vendor=excluded.gpu_vendor,gpu_model=excluded.gpu_model,vram_mb=excluded.vram_mb,cuda_version=excluded.cuda_version,available_memory_mb=excluded.available_memory_mb,supported_models=excluded.supported_models,latency_ms=excluded.latency_ms,status='ONLINE',last_heartbeat=excluded.last_heartbeat,max_concurrent_tasks=excluded.max_concurrent_tasks,last_disconnect_at=NULL
        """, (worker_id,caps,str(params.get("gpuVendor","NVIDIA")),str(params.get("gpuModel","RTX 4090")),int(params.get("vramMb",24576)),str(params.get("cudaVersion","12.2")),int(params.get("availableMemoryMb",params.get("vramMb",24576))),models,float(params.get("latencyMs",10.0)),"ONLINE",stamp,active,max_tasks,queued))
        self._event("WORKER_REGISTERED", worker_id, None, maxConcurrentTasks=max_tasks)
        self._assign_pending()
        self.db.commit()
        return {"workerId":worker_id,"registered":True,"status":"ONLINE","capabilities":json.loads(caps),"maxConcurrentTasks":max_tasks}

    def heartbeat(self, params: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(params.get("workerId", "")).strip()
        if not worker_id:
            raise ValueError("workerId is required")
        if not self._worker(worker_id):
            raise ValueError(f"worker_not_found: {worker_id}")
        stamp = utcnow()
        self.db.execute("UPDATE workers SET last_heartbeat=?,status='ONLINE',last_disconnect_at=NULL WHERE worker_id=?", (stamp,worker_id))
        self._event("WORKER_HEARTBEAT", worker_id)
        self._assign_pending()
        self.db.commit()
        return {"workerId":worker_id,"status":"ONLINE","lastHeartbeat":stamp}

    def schedule(self, params: dict[str, Any]) -> dict[str, Any]:
        task = params.get("task", {})
        if not isinstance(task, dict): task = {}
        task_type = str(params.get("taskType") or task.get("type") or "inference").strip()
        capability = str(params.get("requiredCapability") or task.get("requiredCapability") or "compute").strip()
        payload = params.get("payload", task)
        idem = str(params.get("idempotencyKey", "")).strip() or None
        if idem:
            old = self.db.execute("SELECT task_id,status,assigned_worker_id FROM tasks WHERE idempotency_key=?", (idem,)).fetchone()
            if old:
                return {"taskId":old[0],"taskType":task_type,"requiredCapability":capability,"assignedWorkerId":old[2],"status":old[1],"idempotentReplay":True}
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        worker_id = self._select_worker(capability, payload)
        status = "QUEUED" if worker_id else "PENDING_WORKER"
        stamp = utcnow()
        self.db.execute("INSERT INTO tasks(task_id,task_type,required_capability,payload,assigned_worker_id,status,created_at,updated_at,attempt_count,max_attempts,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (task_id,task_type,capability,json.dumps(payload,separators=(",",":")),worker_id,status,stamp,stamp,0,max(1,int(params.get("maxAttempts",self.max_attempts_default))),idem))
        if worker_id:
            self.db.execute("UPDATE workers SET queued_tasks=queued_tasks+1 WHERE worker_id=?", (worker_id,))
            self._event("TASK_ASSIGNED",worker_id,task_id,capability=capability)
        else:
            self._event("TASK_PENDING",None,task_id,capability=capability)
        self.db.commit()
        return {"taskId":task_id,"taskType":task_type,"requiredCapability":capability,"assignedWorkerId":worker_id,"status":status,"attemptCount":0}

    def claim(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = str(params.get("taskId","")).strip(); worker_id = str(params.get("workerId","")).strip()
        if not task_id: raise ValueError("taskId is required")
        if not worker_id: raise ValueError("workerId is required")
        task = self.db.execute("SELECT assigned_worker_id,status,attempt_count,max_attempts,payload FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not task: raise ValueError(f"task_not_found: {task_id}")
        if task[0] != worker_id: raise ValueError("worker_mismatch")
        if task[1] != "QUEUED": raise ValueError(f"task_not_queued: {task[1]}")
        worker = self._worker(worker_id)
        if not worker: raise ValueError(f"worker_not_found: {worker_id}")
        if not self._worker_can_run(worker,"" if not task[4] else self._task_capability(task_id)): raise ValueError("worker_not_available")
        stamp=utcnow(); lease=iso_after(self.default_lease); attempt=int(task[2] or 0)+1
        self.db.execute("UPDATE tasks SET status='RUNNING',attempt_count=?,started_at=COALESCE(started_at,?),lease_expires_at=?,retry_at=NULL,updated_at=? WHERE task_id=? AND status='QUEUED'", (attempt,stamp,lease,stamp,task_id))
        if self.db.execute("SELECT changes()").fetchone()[0] != 1: raise ValueError("task_claim_conflict")
        self.db.execute("UPDATE workers SET queued_tasks=MAX(queued_tasks-1,0),active_tasks=active_tasks+1,lease_expires_at=? WHERE worker_id=?", (lease,worker_id))
        self._event("TASK_STARTED",worker_id,task_id,attempt=attempt,leaseExpiresAt=lease)
        self.db.commit()
        return {"taskId":task_id,"workerId":worker_id,"status":"RUNNING","attemptCount":attempt,"leaseExpiresAt":lease}

    def _task_capability(self, task_id: str) -> str:
        row=self.db.execute("SELECT required_capability FROM tasks WHERE task_id=?",(task_id,)).fetchone()
        return row[0] if row else ""

    def complete(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id=str(params.get("taskId","")).strip(); worker_id=str(params.get("workerId","")).strip()
        if not task_id: raise ValueError("taskId is required")
        if not worker_id: raise ValueError("workerId is required")
        row=self.db.execute("SELECT assigned_worker_id,status FROM tasks WHERE task_id=?",(task_id,)).fetchone()
        if not row: raise ValueError(f"task_not_found: {task_id}")
        if row[0]!=worker_id: raise ValueError("worker_mismatch")
        if row[1]!="RUNNING": raise ValueError(f"task_not_running: {row[1]}")
        result=params.get("result")
        stamp=utcnow()
        self.db.execute("UPDATE tasks SET status='COMPLETED',result=?,error=NULL,lease_expires_at=NULL,completed_at=?,updated_at=? WHERE task_id=? AND status='RUNNING' AND assigned_worker_id=?",(json.dumps(result,separators=(",",":")) if result is not None else None,stamp,stamp,task_id,worker_id))
        if self.db.execute("SELECT changes()").fetchone()[0]!=1: raise ValueError("task_completion_conflict")
        self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?",(worker_id,))
        self._event("TASK_COMPLETED",worker_id,task_id,hasResult=result is not None)
        self.db.commit()
        return {"taskId":task_id,"workerId":worker_id,"status":"COMPLETED","result":result}

    def fail(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id=str(params.get("taskId","")).strip(); worker_id=str(params.get("workerId","")).strip(); error=str(params.get("error","worker_reported_failure"))
        row=self.db.execute("SELECT assigned_worker_id,status FROM tasks WHERE task_id=?",(task_id,)).fetchone()
        if not row: raise ValueError(f"task_not_found: {task_id}")
        if row[0]!=worker_id: raise ValueError("worker_mismatch")
        if row[1]!="RUNNING": raise ValueError(f"task_not_running: {row[1]}")
        status=self._requeue_task(task_id,error)
        self.db.commit()
        return {"taskId":task_id,"workerId":worker_id,"status":status,"error":error}

    def get_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id=str(params.get("taskId","")).strip()
        row=self.db.execute("SELECT task_id,task_type,required_capability,payload,assigned_worker_id,status,created_at,updated_at,attempt_count,max_attempts,lease_expires_at,result,error,started_at,completed_at,idempotency_key FROM tasks WHERE task_id=?",(task_id,)).fetchone()
        if not row: raise ValueError(f"task_not_found: {task_id}")
        def load(v):
            if v is None:return None
            try:return json.loads(v)
            except Exception:return v
        return {"taskId":row[0],"taskType":row[1],"requiredCapability":row[2],"payload":load(row[3]),"assignedWorkerId":row[4],"status":row[5],"createdAt":row[6],"updatedAt":row[7],"attemptCount":row[8],"maxAttempts":row[9],"leaseExpiresAt":row[10],"result":load(row[11]),"error":row[12],"startedAt":row[13],"completedAt":row[14],"idempotencyKey":row[15]}

    def list_workers(self, params: dict[str, Any]) -> dict[str, Any]:
        cap=str(params.get("capability","")).strip(); status=str(params.get("status","")).strip().upper()
        rows=self.db.execute("SELECT worker_id,capabilities,gpu_vendor,gpu_model,vram_mb,cuda_version,available_memory_mb,supported_models,latency_ms,status,last_heartbeat,active_tasks,max_concurrent_tasks,queued_tasks,lease_expires_at,last_disconnect_at FROM workers").fetchall()
        workers=[]
        for r in rows:
            try:caps=json.loads(r[1] or "[]")
            except Exception:caps=[]
            if cap and cap not in caps:continue
            if status and status!=r[9]:continue
            workers.append({"workerId":r[0],"capabilities":caps,"gpuVendor":r[2],"gpuModel":r[3],"vramMb":r[4],"cudaVersion":r[5],"availableMemoryMb":r[6],"supportedModels":json.loads(r[7] or "[]"),"latencyMs":r[8],"status":r[9],"lastHeartbeat":r[10],"activeTasks":r[11],"maxConcurrentTasks":r[12],"queuedTasks":r[13],"leaseExpiresAt":r[14],"lastDisconnectAt":r[15],"heartbeatFresh":fresh(r[10],self.heartbeat_timeout)})
        return {"workers":workers,"count":len(workers)}

    def metrics(self, _params: dict[str, Any]) -> dict[str, Any]:
        counts={r[0]:r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM tasks GROUP BY status").fetchall()}
        worker_counts={r[0]:r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM workers GROUP BY status").fetchall()}
        return {"scheduler":"v3","tasks":counts,"workers":worker_counts,"heartbeatTimeoutSeconds":self.heartbeat_timeout,"taskLeaseSeconds":self.default_lease,"defaultMaxAttempts":self.max_attempts_default,"timestamp":utcnow()}

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        self._ensure_schema()
        if method=="RegisterWorkerV3" or (method=="RegisterWorker" and ("maxConcurrentTasks" in params or params.get("schedulerVersion")==3)):
            return self.register_worker(params)
        if method=="HeartbeatV3" or method=="Heartbeat":
            return self.heartbeat(params)
        if method=="ScheduleComputeV3" or (method=="ScheduleCompute" and ("idempotencyKey" in params or "maxAttempts" in params)):
            return self.schedule(params)
        if method=="ClaimTaskV3" or method=="ClaimTask":
            return self.claim(params)
        if method=="CompleteTaskV3" or method=="CompleteTask":
            return self.complete(params)
        if method=="FailTask":
            return self.fail(params)
        if method=="GetTask":
            return self.get_task(params)
        if method=="ListWorkersV3":
            return self.list_workers(params)
        if method=="GetSchedulerMetrics":
            return self.metrics(params)
        if method=="ReapScheduler":
            return self.reap()
        return NOT_HANDLED
