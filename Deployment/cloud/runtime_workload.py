"""Durable AI workload integration for SarembokVE."""
from __future__ import annotations
import json, sqlite3
from typing import Any
from platform_contract import Artifact, Evidence, EvidenceKind, RunRecord, RunState, TraceEvent, WorkRequirement, WorkScheduler, WorkerProfile, new_id, utc_now

RUN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_runs (
 run_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, parent_run_id TEXT, tenant_id TEXT NOT NULL,
 state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deadline_at TEXT,
 idempotency_key TEXT, attempt INTEGER NOT NULL DEFAULT 0, checkpoint_id TEXT,
 cancellation_requested INTEGER NOT NULL DEFAULT 0, metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runtime_runs_tenant_updated ON runtime_runs(tenant_id,updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_runs_idempotency ON runtime_runs(tenant_id,idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS runtime_run_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, event_type TEXT NOT NULL, state TEXT,
 payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runtime_run_events_run ON runtime_run_events(run_id,id);
CREATE TABLE IF NOT EXISTS runtime_evidence (
 evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL, content_json TEXT NOT NULL,
 source TEXT NOT NULL, observed_at TEXT NOT NULL, confidence REAL, scope TEXT, provenance_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runtime_evidence_run ON runtime_evidence(run_id,observed_at);
CREATE TABLE IF NOT EXISTS runtime_artifacts (
 artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, name TEXT NOT NULL, media_type TEXT NOT NULL,
 size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL, storage_uri TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runtime_artifacts_run ON runtime_artifacts(run_id,created_at);
CREATE TABLE IF NOT EXISTS runtime_traces (
 trace_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, event_type TEXT NOT NULL, timestamp TEXT NOT NULL,
 component TEXT NOT NULL, duration_ms REAL, attributes_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runtime_traces_run ON runtime_traces(run_id,timestamp);
"""

class DurableWorkloadStore:
    def __init__(self, cloud_store: Any):
        self.store = cloud_store
        self.db: sqlite3.Connection = cloud_store.db
        self.db.executescript(RUN_TABLE_SQL); self.db.commit()

    def _row(self, run_id):
        return self.db.execute("SELECT * FROM runtime_runs WHERE run_id=?", (run_id,)).fetchone()

    def create_run(self, *, tenant_id, request_id, parent_run_id=None, deadline_at=None, idempotency_key=None, metadata=None):
        if idempotency_key:
            row = self.db.execute("SELECT * FROM runtime_runs WHERE tenant_id=? AND idempotency_key=?", (tenant_id,idempotency_key)).fetchone()
            if row: return self._serialize(row)
        rid, stamp = new_id("run"), utc_now()
        self.db.execute("INSERT INTO runtime_runs(run_id,request_id,parent_run_id,tenant_id,state,created_at,updated_at,deadline_at,idempotency_key,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (rid,request_id,parent_run_id,tenant_id,RunState.ACCEPTED.value,stamp,stamp,deadline_at,idempotency_key,json.dumps(metadata or {},sort_keys=True)))
        self.db.commit(); self._event(rid,"run.accepted",RunState.ACCEPTED.value,metadata or {})
        return self.get_run(rid)

    def transition(self, run_id, state: RunState, **metadata):
        row=self._row(run_id)
        if row is None: raise KeyError(f"run_not_found: {run_id}")
        record=RunRecord(row["run_id"],row["request_id"],row["parent_run_id"],row["tenant_id"],RunState(row["state"]),row["created_at"],row["updated_at"],row["deadline_at"],row["idempotency_key"],int(row["attempt"] or 0),row["checkpoint_id"],bool(row["cancellation_requested"]),json.loads(row["metadata_json"] or "{}"))
        updated=record.transition(state,**metadata)
        self.db.execute("UPDATE runtime_runs SET state=?,updated_at=?,checkpoint_id=?,metadata_json=? WHERE run_id=?",(updated.state.value,updated.updated_at,updated.checkpoint_id,json.dumps(dict(updated.metadata),sort_keys=True),run_id))
        self.db.commit(); self._event(run_id,f"run.{state.value}",state.value,metadata)
        return self.get_run(run_id)

    def request_cancel(self,run_id):
        row=self._row(run_id)
        if row is None: raise KeyError(f"run_not_found: {run_id}")
        if row["state"] in {RunState.COMPLETED.value,RunState.FAILED.value,RunState.CANCELLED.value}: return self._serialize(row)
        self.db.execute("UPDATE runtime_runs SET cancellation_requested=1,updated_at=? WHERE run_id=?",(utc_now(),run_id)); self.db.commit()
        self._event(run_id,"run.cancel_requested",row["state"],{}); return self.get_run(run_id)

    def get_run(self,run_id):
        row=self._row(run_id)
        if row is None: raise KeyError(f"run_not_found: {run_id}")
        return self._serialize(row)

    def list_runs(self,tenant_id,limit=50):
        limit=max(1,min(int(limit),200)); rows=self.db.execute("SELECT * FROM runtime_runs WHERE tenant_id=? ORDER BY updated_at DESC LIMIT ?",(tenant_id,limit)).fetchall()
        return [self._serialize(r) for r in rows]

    def add_evidence(self,run_id,kind,content,source,*,confidence=None,scope=None,provenance=None):
        ev=Evidence.create(EvidenceKind(kind),content,source,confidence=confidence,scope=scope,provenance=provenance)
        self.db.execute("INSERT INTO runtime_evidence(evidence_id,run_id,kind,content_json,source,observed_at,confidence,scope,provenance_json) VALUES(?,?,?,?,?,?,?,?,?)",
                        (ev.evidence_id,run_id,ev.kind.value,json.dumps(ev.content,default=str),ev.source,ev.observed_at,ev.confidence,ev.scope,json.dumps(dict(ev.provenance),sort_keys=True)))
        self.db.commit(); return ev

    def get_evidence(self,run_id):
        rows=self.db.execute("SELECT * FROM runtime_evidence WHERE run_id=? ORDER BY observed_at ASC",(run_id,)).fetchall()
        return [{"evidenceId":r["evidence_id"],"runId":run_id,"kind":r["kind"],"content":json.loads(r["content_json"]),"source":r["source"],"observedAt":r["observed_at"],"confidence":r["confidence"],"scope":r["scope"],"provenance":json.loads(r["provenance_json"] or "{}")} for r in rows]

    def add_artifact(self,run_id,name,media_type,payload,storage_uri,metadata=None):
        artifact=Artifact.from_bytes(run_id,name,media_type,payload,storage_uri,metadata)
        self.db.execute("INSERT INTO runtime_artifacts(artifact_id,run_id,name,media_type,size_bytes,sha256,created_at,storage_uri,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                        (artifact.artifact_id,artifact.run_id,artifact.name,artifact.media_type,artifact.size_bytes,artifact.sha256,artifact.created_at,artifact.storage_uri,json.dumps(dict(artifact.metadata),sort_keys=True)))
        self.db.commit(); return artifact

    def get_artifacts(self,run_id):
        rows=self.db.execute("SELECT * FROM runtime_artifacts WHERE run_id=? ORDER BY created_at ASC",(run_id,)).fetchall()
        return [{"artifactId":r["artifact_id"],"runId":run_id,"name":r["name"],"mediaType":r["media_type"],"sizeBytes":r["size_bytes"],"sha256":r["sha256"],"createdAt":r["created_at"],"storageUri":r["storage_uri"],"metadata":json.loads(r["metadata_json"] or "{}")} for r in rows]

    def trace(self,run_id,event_type,component,*,duration_ms=None,attributes=None):
        trace=TraceEvent.create(run_id,event_type,component,duration_ms=duration_ms,attributes=attributes)
        self.db.execute("INSERT INTO runtime_traces(trace_id,run_id,event_type,timestamp,component,duration_ms,attributes_json) VALUES(?,?,?,?,?,?,?)",
                        (trace.trace_id,trace.run_id,trace.event_type,trace.timestamp,trace.component,trace.duration_ms,json.dumps(dict(trace.attributes),sort_keys=True,default=str)))
        self.db.commit(); return trace

    def get_traces(self,run_id):
        rows=self.db.execute("SELECT * FROM runtime_traces WHERE run_id=? ORDER BY timestamp ASC",(run_id,)).fetchall()
        return [{"traceId":r["trace_id"],"runId":run_id,"eventType":r["event_type"],"timestamp":r["timestamp"],"component":r["component"],"durationMs":r["duration_ms"],"attributes":json.loads(r["attributes_json"] or "{}")} for r in rows]

    def schedule(self,requirement):
        req=WorkRequirement(capabilities=frozenset(requirement.get("capabilities") or []),models=frozenset(requirement.get("models") or []),min_cpu_cores=float(requirement.get("minCpuCores",0) or 0),min_ram_mb=int(requirement.get("minRamMb",0) or 0),min_vram_mb=int(requirement.get("minVramMb",0) or 0),locality=requirement.get("locality"),max_latency_ms=requirement.get("maxLatencyMs"),max_cost_per_minute=requirement.get("maxCostPerMinute"),priority=int(requirement.get("priority",0) or 0))
        rows=self.db.execute("SELECT worker_id,status,capabilities,gpu_model,vram_mb,available_memory_mb,supported_models,latency_ms,active_tasks FROM workers").fetchall(); workers=[]
        for r in rows:
            try: caps=frozenset(json.loads(r["capabilities"] or "[]"))
            except Exception: caps=frozenset()
            try: models=frozenset(json.loads(r["supported_models"] or "[]"))
            except Exception: models=frozenset()
            workers.append(WorkerProfile(r["worker_id"],r["status"],ram_mb=int(r["available_memory_mb"] or 0),gpu_model=r["gpu_model"],vram_mb=int(r["vram_mb"] or 0),capabilities=caps,models=models,latency_ms=float(r["latency_ms"] or 0),load=float(r["active_tasks"] or 0)))
        ranked=WorkScheduler().rank(workers,req)
        return {"feasible":bool(ranked),"selectedWorkerId":ranked[0].worker_id if ranked else None,"candidates":[{"workerId":w.worker_id,"score":WorkScheduler.score(w,req)} for w in ranked]}

    def _event(self,run_id,event_type,state,payload):
        self.db.execute("INSERT INTO runtime_run_events(run_id,event_type,state,payload_json,created_at) VALUES(?,?,?,?,?)",(run_id,event_type,state,json.dumps(payload,sort_keys=True,default=str),utc_now())); self.db.commit()

    @staticmethod
    def _serialize(row):
        return {"runId":row["run_id"],"requestId":row["request_id"],"parentRunId":row["parent_run_id"],"tenantId":row["tenant_id"],"state":row["state"],"createdAt":row["created_at"],"updatedAt":row["updated_at"],"deadlineAt":row["deadline_at"],"idempotencyKey":row["idempotency_key"],"attempt":row["attempt"],"checkpointId":row["checkpoint_id"],"cancellationRequested":bool(row["cancellation_requested"]),"metadata":json.loads(row["metadata_json"] or "{}")}


def install_runtime_workload_api(cloud_server):
    runtime=DurableWorkloadStore(cloud_server.store)
    methods={"GetRun","ListRuns","CancelRun","GetRunEvidence","GetRunArtifacts","GetRunTrace","RecordEvidence","RecordArtifact","GetSchedulerDecision"}
    if isinstance(getattr(cloud_server,"BROWSER_ALLOWED_METHODS",None),set): cloud_server.BROWSER_ALLOWED_METHODS.update(methods)
    original=cloud_server.dispatch
    def dispatch(method,params):
        if method=="GetRun": return runtime.get_run(str(params.get("runId","")))
        if method=="ListRuns": return {"runs":runtime.list_runs(str(params.get("tenantId") or "user:anonymous"),params.get("limit",50))}
        if method=="CancelRun": return runtime.request_cancel(str(params.get("runId","")))
        if method=="GetRunEvidence": return {"evidence":runtime.get_evidence(str(params.get("runId","")))}
        if method=="GetRunArtifacts": return {"artifacts":runtime.get_artifacts(str(params.get("runId","")))}
        if method=="GetRunTrace": return {"trace":runtime.get_traces(str(params.get("runId","")))}
        if method=="RecordEvidence": return {"evidence":runtime.add_evidence(str(params["runId"]),str(params["kind"]),params.get("content"),str(params.get("source","unknown")),confidence=params.get("confidence"),scope=params.get("scope"),provenance=params.get("provenance")).__dict__}
        if method=="RecordArtifact":
            payload=params.get("content",""); payload=payload.encode() if isinstance(payload,str) else bytes(payload)
            a=runtime.add_artifact(str(params["runId"]),str(params["name"]),str(params.get("mediaType","application/octet-stream")),payload,str(params.get("storageUri","sarembok://artifact/"+new_id("artifact"))),params.get("metadata")); return {"artifact":a.__dict__}
        if method=="GetSchedulerDecision": return runtime.schedule(params.get("requirement") or {})
        return original(method,params)
    cloud_server.dispatch=dispatch
    return runtime


def install_chat_lifecycle(cloud_server,runtime):
    original=cloud_server.dispatch
    lifecycle_methods={"SarembokChat","Chat","SarembokDialogue","GenerateImage","ExecuteComputeTask","ScheduleCompute"}
    def dispatch(method,params):
        if method not in lifecycle_methods: return original(method,params)
        request_id=str(params.get("requestId") or new_id("request")); tenant_id=str(params.get("tenantId") or params.get("userId") or "user:anonymous")
        run=runtime.create_run(tenant_id=tenant_id,request_id=request_id,parent_run_id=params.get("parentRunId"),idempotency_key=params.get("idempotencyKey"),metadata={"method":method,"sessionId":params.get("sessionId")}); run_id=run["runId"]
        started=__import__("time").perf_counter(); runtime.trace(run_id,"request.accepted","runtime",attributes={"method":method,"requestId":request_id})
        try:
            runtime.transition(run_id,RunState.AUTHORIZED,method=method); runtime.transition(run_id,RunState.PLANNED,method=method); runtime.transition(run_id,RunState.EXECUTING,method=method)
            result=original(method,params); source=str(result.get("source","runtime")) if isinstance(result,dict) else "runtime"; content=result.get("response") if isinstance(result,dict) else result
            runtime.add_evidence(run_id,EvidenceKind.MODEL_INFERENCE.value,content,source,provenance={"method":method}); runtime.transition(run_id,RunState.VERIFYING,method=method); runtime.transition(run_id,RunState.COMPLETED,method=method)
            runtime.trace(run_id,"request.completed","runtime",duration_ms=round((__import__("time").perf_counter()-started)*1000,1),attributes={"method":method,"source":source})
            if isinstance(result,dict): result["runId"]=run_id
            return result
        except Exception as exc:
            runtime.add_evidence(run_id,EvidenceKind.RUNTIME_FACT.value,{"error":str(exc)},"runtime",provenance={"method":method}); runtime.trace(run_id,"request.failed","runtime",attributes={"method":method,"error":str(exc)})
            try: runtime.transition(run_id,RunState.FAILED,method=method,error=str(exc))
            except Exception: pass
            raise
    cloud_server.dispatch=dispatch
