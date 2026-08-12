from __future__ import annotations

import sqlite3
import tempfile

from scheduler_v3 import SchedulerV3


class Store:
    def __init__(self, db):
        self.db = db


def rpc(s, method, params):
    result = s.dispatch(method, params)
    assert result is not None, method
    return result


def main():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = sqlite3.connect(f.name)
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE workers(
            worker_id TEXT PRIMARY KEY, capabilities TEXT NOT NULL, gpu_vendor TEXT,
            gpu_model TEXT, vram_mb INTEGER, cuda_version TEXT, available_memory_mb INTEGER,
            supported_models TEXT, latency_ms REAL, status TEXT NOT NULL, last_heartbeat TEXT NOT NULL
        );
        CREATE TABLE tasks(
            task_id TEXT PRIMARY KEY, task_type TEXT NOT NULL, required_capability TEXT NOT NULL,
            payload TEXT NOT NULL, assigned_worker_id TEXT, status TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)
        db.commit()
        scheduler = SchedulerV3(Store(db))

        # Simulate a V2 database where active_tasks is created by the V2 migration.
        assert "active_tasks" in {r[1] for r in db.execute("PRAGMA table_info(workers)")}

        a = rpc(scheduler, "RegisterWorkerV3", {"workerId":"v3-a","capabilities":["compute"],"maxConcurrentTasks":2,"availableMemoryMb":16000})
        assert a["status"] == "ONLINE"

        first = rpc(scheduler, "ScheduleComputeV3", {"taskType":"inference","requiredCapability":"compute","payload":{"test":1},"idempotencyKey":"e2e-1"})
        replay = rpc(scheduler, "ScheduleComputeV3", {"taskType":"inference","requiredCapability":"compute","payload":{"test":1},"idempotencyKey":"e2e-1"})
        assert replay["taskId"] == first["taskId"] and replay["idempotentReplay"] is True

        claimed = rpc(scheduler, "ClaimTaskV3", {"taskId":first["taskId"],"workerId":"v3-a"})
        assert claimed["status"] == "RUNNING" and claimed["attemptCount"] == 1
        completed = rpc(scheduler, "CompleteTaskV3", {"taskId":first["taskId"],"workerId":"v3-a","result":{"ok":True}})
        assert completed["status"] == "COMPLETED" and completed["result"]["ok"] is True
        task = rpc(scheduler, "GetTask", {"taskId":first["taskId"]})
        assert task["result"] == {"ok": True}

        retry = rpc(scheduler, "ScheduleComputeV3", {"taskType":"inference","requiredCapability":"compute","payload":{"test":2},"maxAttempts":2})
        rpc(scheduler, "ClaimTaskV3", {"taskId":retry["taskId"],"workerId":"v3-a"})
        failed = rpc(scheduler, "FailTask", {"taskId":retry["taskId"],"workerId":"v3-a","error":"simulated"})
        assert failed["status"] == "RETRY_WAIT"
        db.execute("UPDATE tasks SET retry_at='1970-01-01T00:00:00+00:00' WHERE task_id=?", (retry["taskId"],))
        db.commit()
        scheduler.reap()
        task = rpc(scheduler, "GetTask", {"taskId":retry["taskId"]})
        assert task["status"] in {"QUEUED", "PENDING_WORKER"}

        db.execute("UPDATE workers SET last_heartbeat='1970-01-01T00:00:00+00:00' WHERE worker_id='v3-a'")
        db.commit()
        result = scheduler.reap()
        assert result["staleWorkers"] >= 1

        metrics = rpc(scheduler, "GetSchedulerMetrics", {})
        assert metrics["scheduler"] == "V3"
        print("[OK] Scheduler V3 regression suite passed")
        db.close()


if __name__ == "__main__":
    main()
