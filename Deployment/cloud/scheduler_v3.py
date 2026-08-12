"""Durable Scheduler V3 layered on the frozen Sarembok Cloud runtime."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

LOG = logging.getLogger("sarembok.scheduler.v3")
NOT_HANDLED = object()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def after(seconds: int) -> str:
    return datetime.fromtimestamp(time.time() + seconds, timezone.utc).isoformat()


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
        self.db = store.db
        self.heartbeat_timeout = max(15, int(os.getenv("SAREMBOK_WORKER_HEARTBEAT_TIMEOUT", "90")))
        self.lease_seconds = max(15, int(os.getenv("SAREMBOK_TASK_LEASE_SECONDS", "300")))
        self.retry_delay = max(1, int(os.getenv("SAREMBOK_TASK_RETRY_DELAY_SECONDS", "5")))
        self.default_attempts = max(1, int(os.getenv("SAREMBOK_TASK_MAX_ATTEMPTS", "3")))
        self.ensure_schema()

    def cols(self, table: str) -> set[str]:
        return {r[1] for r in self.db.execute(f"PRAGMA table_info({table})")}

    def add_column(self, table: str, name: str, definition: str) -> None:
        if name not in self.cols(table):
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def ensure_schema(self) -> None:
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS scheduler_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                worker_id TEXT,
                task_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_scheduler_events_time ON scheduler_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_worker_status ON tasks(assigned_worker_id,status);
        """)
        for n, d in (
            ("max_concurrent_tasks", "INTEGER NOT NULL DEFAULT 1"),
            ("queued_tasks", "INTEGER NOT NULL DEFAULT 0"),
            ("lease_expires_at", "TEXT"),
            ("last_disconnect_at", "TEXT"),
        ):
            self.add_column("workers", n, d)
        for n, d in (
            ("attempt_count", "INTEGER NOT NULL DEFAULT 0"),
            ("max_attempts", f"INTEGER NOT NULL DEFAULT {self.default_attempts}"),
            ("lease_expires_at", "TEXT"),
            ("result", "TEXT"),
            ("error", "TEXT"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT"),
            ("idempotency_key", "TEXT"),
            ("retry_at", "TEXT"),
        ):
            self.add_column("tasks", n, d)
        self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
        self.db.execute("UPDATE workers SET max_concurrent_tasks=1 WHERE max_concurrent_tasks IS NULL OR max_concurrent_tasks<1")
        self.db.execute("UPDATE workers SET queued_tasks=0 WHERE queued_tasks IS NULL OR queued_tasks<0")
        self.db.commit()

    def event(self, kind: str, worker: str | None = None, task: str | None = None, **data: Any) -> None:
        self.db.execute(
            "INSERT INTO scheduler_events(event_type,worker_id,task_id,payload,created_at) VALUES(?,?,?,?,?)",
            (kind, worker, task, json.dumps(data, separators=(",", ":")), now()),
        )

    def worker(self, worker_id: str):
        return self.db.execute(
            "SELECT worker_id,status,last_heartbeat,active_tasks,queued_tasks,max_concurrent_tasks,available_memory_mb,latency_ms,capabilities,supported_models FROM workers WHERE worker_id=?",
            (worker_id,),
        ).fetchone()

    def can_run(self, row: Any, capability: str) -> bool:
        if not row or row[1] != "ONLINE" or not fresh(row[2], self.heartbeat_timeout):
            return False
        try:
            capabilities = json.loads(row[8] or "[]")
        except Exception:
            capabilities = []
        if capability and capability not in capabilities:
            return False
        return int(row[3] or 0) + int(row[4] or 0) < max(1, int(row[5] or 1))

    def choose(self, capability: str, payload: Any = None) -> str | None:
        requested_model = payload.get("model") if isinstance(payload, dict) else None
        rows = self.db.execute(
            "SELECT worker_id,status,last_heartbeat,active_tasks,queued_tasks,max_concurrent_tasks,available_memory_mb,latency_ms,capabilities,supported_models FROM workers WHERE status='ONLINE'"
        ).fetchall()
        candidates = []
        for row in rows:
            if not self.can_run(row, capability):
                continue
            if requested_model:
                try:
                    models = json.loads(row[9] or "[]")
                except Exception:
                    models = []
                if requested_model not in models and "default" not in models:
                    continue
            load = int(row[3] or 0) + int(row[4] or 0)
            candidates.append((load, float(row[7] or 999999), -int(row[6] or 0), row[0]))
        return min(candidates)[3] if candidates else None

    def register(self, p: dict[str, Any]) -> dict[str, Any]:
        wid = str(p.get("workerId", "")).strip()
        if not wid:
            raise ValueError("workerId is required")
        caps = json.dumps(p.get("capabilities", ["inference"]))
        models = json.dumps(p.get("supportedModels", ["default"]))
        maximum = max(1, int(p.get("maxConcurrentTasks", p.get("concurrency", 1))))
        old = self.worker(wid)
        active = int(old[3]) if old else 0
        queued = int(old[4]) if old else 0
        stamp = now()
        values = (
            wid, caps, str(p.get("gpuVendor", "NVIDIA")), str(p.get("gpuModel", "RTX 4090")),
            int(p.get("vramMb", 24576)), str(p.get("cudaVersion", "12.2")),
            int(p.get("availableMemoryMb", p.get("vramMb", 24576))), models,
            float(p.get("latencyMs", 10.0)), "ONLINE", stamp, active, maximum, queued,
        )
        self.db.execute("""
            INSERT INTO workers(
                worker_id,capabilities,gpu_vendor,gpu_model,vram_mb,cuda_version,
                available_memory_mb,supported_models,latency_ms,status,last_heartbeat,
                active_tasks,max_concurrent_tasks,queued_tasks
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(worker_id) DO UPDATE SET
                capabilities=excluded.capabilities,gpu_vendor=excluded.gpu_vendor,
                gpu_model=excluded.gpu_model,vram_mb=excluded.vram_mb,
                cuda_version=excluded.cuda_version,available_memory_mb=excluded.available_memory_mb,
                supported_models=excluded.supported_models,latency_ms=excluded.latency_ms,
                status='ONLINE',last_heartbeat=excluded.last_heartbeat,
                max_concurrent_tasks=excluded.max_concurrent_tasks,last_disconnect_at=NULL
        """, values)
        self.event("WORKER_REGISTERED", wid, None, maxConcurrentTasks=maximum)
        self.assign_pending()
        self.db.commit()
        return {"workerId": wid, "registered": True, "status": "ONLINE", "capabilities": json.loads(caps), "maxConcurrentTasks": maximum}

    def heartbeat(self, p: dict[str, Any]) -> dict[str, Any]:
        wid = str(p.get("workerId", "")).strip()
        if not wid:
            raise ValueError("workerId is required")
        if not self.worker(wid):
            raise ValueError(f"worker_not_found: {wid}")
        stamp = now()
        self.db.execute("UPDATE workers SET status='ONLINE',last_heartbeat=?,last_disconnect_at=NULL WHERE worker_id=?", (stamp, wid))
        self.event("WORKER_HEARTBEAT", wid)
        self.assign_pending()
        self.db.commit()
        return {"workerId": wid, "status": "ONLINE", "lastHeartbeat": stamp}

    def schedule(self, p: dict[str, Any]) -> dict[str, Any]:
        task = p.get("task", {})
        if not isinstance(task, dict):
            task = {}
        task_type = str(p.get("taskType") or task.get("type") or "inference").strip()
        capability = str(p.get("requiredCapability") or task.get("requiredCapability") or "compute").strip()
        payload = p.get("payload", task)
        idem = str(p.get("idempotencyKey", "")).strip() or None
        if idem:
            existing = self.db.execute("SELECT task_id,task_type,required_capability,assigned_worker_id,status,attempt_count FROM tasks WHERE idempotency_key=?", (idem,)).fetchone()
            if existing:
                return {"taskId": existing[0], "taskType": existing[1], "requiredCapability": existing[2], "assignedWorkerId": existing[3], "status": existing[4], "attemptCount": existing[5], "idempotentReplay": True}
        wid = self.choose(capability, payload)
        status = "QUEUED" if wid else "PENDING_WORKER"
        tid = f"task-{uuid.uuid4().hex[:12]}"
        stamp = now()
        attempts = max(1, int(p.get("maxAttempts", self.default_attempts)))
        self.db.execute("""
            INSERT INTO tasks(task_id,task_type,required_capability,payload,assigned_worker_id,status,created_at,updated_at,attempt_count,max_attempts,idempotency_key)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (tid, task_type, capability, json.dumps(payload, separators=(",", ":")), wid, status, stamp, stamp, 0, attempts, idem))
        if wid:
            self.db.execute("UPDATE workers SET queued_tasks=queued_tasks+1 WHERE worker_id=?", (wid,))
            self.event("TASK_ASSIGNED", wid, tid, capability=capability)
        else:
            self.event("TASK_PENDING", None, tid, capability=capability)
        self.db.commit()
        return {"taskId": tid, "taskType": task_type, "requiredCapability": capability, "assignedWorkerId": wid, "status": status, "attemptCount": 0, "maxAttempts": attempts}

    def claim(self, p: dict[str, Any]) -> dict[str, Any]:
        tid = str(p.get("taskId", "")).strip(); wid = str(p.get("workerId", "")).strip()
        if not tid: raise ValueError("taskId is required")
        if not wid: raise ValueError("workerId is required")
        task = self.db.execute("SELECT assigned_worker_id,status,attempt_count,max_attempts,required_capability FROM tasks WHERE task_id=?", (tid,)).fetchone()
        if not task: raise ValueError(f"task_not_found: {tid}")
        if task[0] != wid: raise ValueError("worker_mismatch")
        if task[1] != "QUEUED": raise ValueError(f"task_not_queued: {task[1]}")
        worker = self.worker(wid)
        if not self.can_run(worker, task[4]): raise ValueError("worker_not_available")
        stamp = now(); lease = after(self.lease_seconds); attempt = int(task[2] or 0) + 1
        self.db.execute("UPDATE tasks SET status='RUNNING',attempt_count=?,started_at=COALESCE(started_at,?),lease_expires_at=?,retry_at=NULL,updated_at=? WHERE task_id=? AND status='QUEUED'", (attempt, stamp, lease, stamp, tid))
        if self.db.execute("SELECT changes()").fetchone()[0] != 1: raise ValueError("task_claim_conflict")
        self.db.execute("UPDATE workers SET queued_tasks=MAX(queued_tasks-1,0),active_tasks=active_tasks+1,lease_expires_at=? WHERE worker_id=?", (lease, wid))
        self.event("TASK_STARTED", wid, tid, attempt=attempt, leaseExpiresAt=lease)
        self.db.commit()
        return {"taskId": tid, "workerId": wid, "status": "RUNNING", "attemptCount": attempt, "leaseExpiresAt": lease}

    def complete(self, p: dict[str, Any]) -> dict[str, Any]:
        tid = str(p.get("taskId", "")).strip(); wid = str(p.get("workerId", "")).strip()
        task = self.db.execute("SELECT assigned_worker_id,status FROM tasks WHERE task_id=?", (tid,)).fetchone()
        if not task: raise ValueError(f"task_not_found: {tid}")
        if task[0] != wid: raise ValueError("worker_mismatch")
        if task[1] != "RUNNING": raise ValueError(f"task_not_running: {task[1]}")
        result = p.get("result")
        stamp = now()
        encoded = json.dumps(result, separators=(",", ":")) if result is not None else None
        self.db.execute("UPDATE tasks SET status='COMPLETED',result=?,error=NULL,lease_expires_at=NULL,completed_at=?,updated_at=? WHERE task_id=? AND status='RUNNING'", (encoded, stamp, stamp, tid))
        if self.db.execute("SELECT changes()").fetchone()[0] != 1: raise ValueError("task_completion_conflict")
        self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?", (wid,))
        self.event("TASK_COMPLETED", wid, tid, hasResult=result is not None)
        self.db.commit()
        return {"taskId": tid, "workerId": wid, "status": "COMPLETED", "result": result}

    def fail(self, p: dict[str, Any]) -> dict[str, Any]:
        tid = str(p.get("taskId", "")).strip(); wid = str(p.get("workerId", "")).strip(); reason = str(p.get("error", "worker_reported_failure"))
        task = self.db.execute("SELECT assigned_worker_id,status,attempt_count,max_attempts FROM tasks WHERE task_id=?", (tid,)).fetchone()
        if not task: raise ValueError(f"task_not_found: {tid}")
        if task[0] != wid: raise ValueError("worker_mismatch")
        if task[1] != "RUNNING": raise ValueError(f"task_not_running: {task[1]}")
        self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?", (wid,))
        if int(task[2] or 0) < int(task[3] or self.default_attempts):
            retry = after(self.retry_delay)
            self.db.execute("UPDATE tasks SET status='RETRY_WAIT',assigned_worker_id=NULL,lease_expires_at=NULL,retry_at=?,error=?,updated_at=? WHERE task_id=?", (retry, reason, now(), tid))
            result = "RETRY_WAIT"
        else:
            self.db.execute("UPDATE tasks SET status='FAILED',lease_expires_at=NULL,error=?,completed_at=?,updated_at=? WHERE task_id=?", (reason, now(), now(), tid))
            result = "FAILED"
        self.event("TASK_FAILED" if result == "FAILED" else "TASK_RETRY_SCHEDULED", wid, tid, reason=reason)
        self.db.commit()
        return {"taskId": tid, "workerId": wid, "status": result, "error": reason}

    def get_task(self, p: dict[str, Any]) -> dict[str, Any]:
        tid = str(p.get("taskId", "")).strip()
        row = self.db.execute("SELECT task_id,task_type,required_capability,payload,assigned_worker_id,status,created_at,updated_at,attempt_count,max_attempts,lease_expires_at,result,error,started_at,completed_at,idempotency_key FROM tasks WHERE task_id=?", (tid,)).fetchone()
        if not row: raise ValueError(f"task_not_found: {tid}")
        def decode(v):
            if v is None: return None
            try: return json.loads(v)
            except Exception: return v
        return {"taskId":row[0],"taskType":row[1],"requiredCapability":row[2],"payload":decode(row[3]),"assignedWorkerId":row[4],"status":row[5],"createdAt":row[6],"updatedAt":row[7],"attemptCount":row[8],"maxAttempts":row[9],"leaseExpiresAt":row[10],"result":decode(row[11]),"error":row[12],"startedAt":row[13],"completedAt":row[14],"idempotencyKey":row[15]}

    def offline(self, p: dict[str, Any]) -> dict[str, Any]:
        wid = str(p.get("workerId", "")).strip()
        if not self.worker(wid): raise ValueError(f"worker_not_found: {wid}")
        self.db.execute("UPDATE workers SET status='OFFLINE',last_disconnect_at=? WHERE worker_id=?", (now(), wid))
        self.event("WORKER_OFFLINE", wid)
        self.db.commit()
        return {"workerId": wid, "status": "OFFLINE"}

    def list_workers(self, p: dict[str, Any]) -> dict[str, Any]:
        cap = str(p.get("capability", "")).strip(); status = str(p.get("status", "")).strip().upper()
        rows = self.db.execute("SELECT worker_id,capabilities,gpu_vendor,gpu_model,vram_mb,cuda_version,available_memory_mb,supported_models,latency_ms,status,last_heartbeat,active_tasks,max_concurrent_tasks,queued_tasks,lease_expires_at,last_disconnect_at FROM workers").fetchall()
        out=[]
        for r in rows:
            try: caps=json.loads(r[1] or "[]")
            except Exception: caps=[]
            if cap and cap not in caps: continue
            if status and r[9] != status: continue
            out.append({"workerId":r[0],"capabilities":caps,"gpuVendor":r[2],"gpuModel":r[3],"vramMb":r[4],"cudaVersion":r[5],"availableMemoryMb":r[6],"supportedModels":json.loads(r[7] or "[]"),"latencyMs":r[8],"status":r[9],"lastHeartbeat":r[10],"activeTasks":r[11],"maxConcurrentTasks":r[12],"queuedTasks":r[13],"leaseExpiresAt":r[14],"lastDisconnectAt":r[15],"heartbeatFresh":fresh(r[10],self.heartbeat_timeout)})
        return {"workers":out,"count":len(out)}

    def assign_pending(self) -> int:
        assigned=0
        rows=self.db.execute("SELECT task_id,required_capability,payload FROM tasks WHERE status IN ('PENDING_WORKER','RETRY_WAIT') AND (retry_at IS NULL OR retry_at<=?) AND assigned_worker_id IS NULL ORDER BY created_at LIMIT 100",(now(),)).fetchall()
        for r in rows:
            try: payload=json.loads(r[2] or "{}")
            except Exception: payload={}
            wid=self.choose(r[1],payload)
            if not wid: continue
            self.db.execute("UPDATE tasks SET status='QUEUED',assigned_worker_id=?,retry_at=NULL,updated_at=? WHERE task_id=? AND assigned_worker_id IS NULL",(wid,now(),r[0]))
            if self.db.execute("SELECT changes()").fetchone()[0] == 1:
                self.db.execute("UPDATE workers SET queued_tasks=queued_tasks+1 WHERE worker_id=?",(wid,))
                self.event("TASK_ASSIGNED",wid,r[0],capability=r[1]); assigned+=1
        return assigned

    def reap(self) -> dict[str, int]:
        stale=expired=retried=0; stamp=now()
        workers=self.db.execute("SELECT worker_id,last_heartbeat FROM workers WHERE status='ONLINE'").fetchall()
        for r in workers:
            if fresh(r[1],self.heartbeat_timeout): continue
            wid=r[0]
            self.db.execute("UPDATE workers SET status='STALE',last_disconnect_at=?,queued_tasks=0 WHERE worker_id=?",(stamp,wid))
            queued=self.db.execute("SELECT task_id FROM tasks WHERE assigned_worker_id=? AND status='QUEUED'",(wid,)).fetchall()
            for t in queued:
                self.db.execute("UPDATE tasks SET status='PENDING_WORKER',assigned_worker_id=NULL,updated_at=? WHERE task_id=?",(stamp,t[0]))
            running=self.db.execute("SELECT task_id,attempt_count,max_attempts FROM tasks WHERE assigned_worker_id=? AND status='RUNNING'",(wid,)).fetchall()
            for t in running:
                self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?",(wid,))
                if int(t[1] or 0) < int(t[2] or self.default_attempts):
                    self.db.execute("UPDATE tasks SET status='RETRY_WAIT',assigned_worker_id=NULL,retry_at=?,lease_expires_at=NULL,error=?,updated_at=? WHERE task_id=?",(after(self.retry_delay),"worker_heartbeat_stale",stamp,t[0])); retried+=1
                else:
                    self.db.execute("UPDATE tasks SET status='FAILED',assigned_worker_id=NULL,lease_expires_at=NULL,error=?,completed_at=?,updated_at=? WHERE task_id=?",("worker_heartbeat_stale",stamp,stamp,t[0]))
                expired+=1
            self.event("WORKER_STALE",wid)
            stale+=1
        leases=self.db.execute("SELECT task_id,assigned_worker_id,attempt_count,max_attempts FROM tasks WHERE status='RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?",(stamp,)).fetchall()
        for t in leases:
            wid=t[1]
            self.db.execute("UPDATE workers SET active_tasks=MAX(active_tasks-1,0),lease_expires_at=NULL WHERE worker_id=?",(wid,))
            if int(t[2] or 0) < int(t[3] or self.default_attempts):
                self.db.execute("UPDATE tasks SET status='RETRY_WAIT',assigned_worker_id=NULL,retry_at=?,lease_expires_at=NULL,error=?,updated_at=? WHERE task_id=?",(after(self.retry_delay),"task_lease_expired",stamp,t[0])); retried+=1
            else:
                self.db.execute("UPDATE tasks SET status='FAILED',assigned_worker_id=NULL,lease_expires_at=NULL,error=?,completed_at=?,updated_at=? WHERE task_id=?",("task_lease_expired",stamp,stamp,t[0]))
            self.event("TASK_LEASE_EXPIRED",wid,t[0]); expired+=1
        assigned=self.assign_pending()
        self.db.commit()
        return {"staleWorkers":stale,"expiredTasks":expired,"retryScheduled":retried,"reassignedTasks":assigned}

    def metrics(self, _p: dict[str, Any]) -> dict[str, Any]:
        tasks={r[0]:r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM tasks GROUP BY status")}
        workers={r[0]:r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM workers GROUP BY status")}
        return {"scheduler":"V3","tasks":tasks,"workers":workers,"heartbeatTimeoutSeconds":self.heartbeat_timeout,"taskLeaseSeconds":self.lease_seconds,"defaultMaxAttempts":self.default_attempts,"timestamp":now()}

    def dispatch(self, method: str, params: dict[str, Any]):
        self.ensure_schema()
        if method in ("RegisterWorkerV3", "RegisterWorker") and (method.endswith("V3") or "maxConcurrentTasks" in params or params.get("schedulerVersion") == 3): return self.register(params)
        if method in ("HeartbeatV3",): return self.heartbeat(params)
        if method == "ScheduleComputeV3": return self.schedule(params)
        if method == "ClaimTaskV3": return self.claim(params)
        if method == "CompleteTaskV3": return self.complete(params)
        if method == "FailTask": return self.fail(params)
        if method == "GetTask": return self.get_task(params)
        if method == "WorkerOffline": return self.offline(params)
        if method == "ListWorkersV3": return self.list_workers(params)
        if method == "GetSchedulerMetrics": return self.metrics(params)
        if method == "ReapScheduler": return self.reap()
        return NOT_HANDLED
