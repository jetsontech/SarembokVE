import json
import sqlite3

from platform_contract import EvidenceKind, RunState
from runtime_workload import DurableWorkloadStore


class FakeStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row


def test_durable_run_lifecycle_evidence_trace_and_artifact():
    runtime = DurableWorkloadStore(FakeStore())
    run = runtime.create_run(tenant_id="user:test", request_id="req-1", idempotency_key="idem-1")
    assert run["state"] == "accepted"
    runtime.transition(run["runId"], RunState.AUTHORIZED)
    runtime.transition(run["runId"], RunState.PLANNED)
    runtime.transition(run["runId"], RunState.EXECUTING)
    runtime.add_evidence(run["runId"], EvidenceKind.RUNTIME_FACT.value, {"workers": 0}, "runtime")
    runtime.trace(run["runId"], "request.test", "pytest")
    artifact = runtime.add_artifact(run["runId"], "result.txt", "text/plain", b"hello", "sarembok://artifact/test")
    runtime.transition(run["runId"], RunState.VERIFYING)
    runtime.transition(run["runId"], RunState.COMPLETED)

    assert runtime.get_run(run["runId"])["state"] == "completed"
    assert runtime.get_evidence(run["runId"])[0]["kind"] == "runtime_fact"
    assert runtime.get_traces(run["runId"])[0]["eventType"] == "request.test"
    assert runtime.get_artifacts(run["runId"])[0]["sha256"] == artifact.sha256
    assert runtime.create_run(tenant_id="user:test", request_id="req-duplicate", idempotency_key="idem-1")["runId"] == run["runId"]


def test_scheduler_uses_only_feasible_live_workers():
    store = FakeStore()
    runtime = DurableWorkloadStore(store)
    store.db.execute("""CREATE TABLE workers (worker_id TEXT, status TEXT, capabilities TEXT, gpu_model TEXT, vram_mb INTEGER, available_memory_mb INTEGER, supported_models TEXT, latency_ms REAL, active_tasks INTEGER)""")
    store.db.execute("INSERT INTO workers VALUES (?,?,?,?,?,?,?,?,?)", ("gpu-a", "ONLINE", json.dumps(["compute","gpu"]), "RTX", 24576, 32768, json.dumps(["model-a"]), 20, 1))
    store.db.execute("INSERT INTO workers VALUES (?,?,?,?,?,?,?,?,?)", ("gpu-b", "OFFLINE", json.dumps(["compute","gpu"]), "RTX", 24576, 32768, json.dumps(["model-a"]), 5, 0))
    store.db.commit()
    decision = runtime.schedule({"capabilities": ["gpu"], "models": ["model-a"], "minVramMb": 16000})
    assert decision["feasible"] is True
    assert decision["selectedWorkerId"] == "gpu-a"
