"""Dependency-light contracts for the SarembokVE AI workload runtime.

Contracts are intentionally separate from capability advertising: defining a
contract does not imply the corresponding production subsystem is enabled.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib, json, uuid
from typing import Any, Iterable, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


class RunState(str, Enum):
    ACCEPTED="accepted"; AUTHORIZED="authorized"; PLANNED="planned"; EXECUTING="executing"
    AWAITING_TOOL="awaiting_tool"; AWAITING_HUMAN="awaiting_human"; VERIFYING="verifying"
    COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"


_ALLOWED = {
    RunState.ACCEPTED:{RunState.AUTHORIZED,RunState.CANCELLED,RunState.FAILED},
    RunState.AUTHORIZED:{RunState.PLANNED,RunState.CANCELLED,RunState.FAILED},
    RunState.PLANNED:{RunState.EXECUTING,RunState.AWAITING_HUMAN,RunState.CANCELLED,RunState.FAILED},
    RunState.EXECUTING:{RunState.AWAITING_TOOL,RunState.AWAITING_HUMAN,RunState.VERIFYING,RunState.COMPLETED,RunState.FAILED,RunState.CANCELLED},
    RunState.AWAITING_TOOL:{RunState.EXECUTING,RunState.FAILED,RunState.CANCELLED},
    RunState.AWAITING_HUMAN:{RunState.EXECUTING,RunState.CANCELLED,RunState.FAILED},
    RunState.VERIFYING:{RunState.COMPLETED,RunState.EXECUTING,RunState.FAILED,RunState.CANCELLED},
    RunState.COMPLETED:set(),RunState.FAILED:set(),RunState.CANCELLED:set(),
}


@dataclass(frozen=True)
class RunRecord:
    run_id:str; request_id:str; parent_run_id:str|None; tenant_id:str; state:RunState
    created_at:str; updated_at:str; deadline_at:str|None=None; idempotency_key:str|None=None
    attempt:int=0; checkpoint_id:str|None=None; cancellation_requested:bool=False
    metadata:Mapping[str,Any]=field(default_factory=dict)

    def transition(self,state:RunState,*,checkpoint_id:str|None=None,**metadata:Any)->"RunRecord":
        if state not in _ALLOWED[self.state]:
            raise ValueError(f"invalid run transition: {self.state.value} -> {state.value}")
        merged=dict(self.metadata); merged.update(metadata)
        return RunRecord(self.run_id,self.request_id,self.parent_run_id,self.tenant_id,state,
            self.created_at,utc_now(),self.deadline_at,self.idempotency_key,self.attempt,
            checkpoint_id or self.checkpoint_id,self.cancellation_requested,merged)

    def request_cancel(self)->"RunRecord":
        if self.state in {RunState.COMPLETED,RunState.FAILED,RunState.CANCELLED}: return self
        return RunRecord(self.run_id,self.request_id,self.parent_run_id,self.tenant_id,self.state,
            self.created_at,utc_now(),self.deadline_at,self.idempotency_key,self.attempt,
            self.checkpoint_id,True,self.metadata)


class RunStore:
    """Reference state machine; production adapters can persist the same contract."""
    def __init__(self)->None:
        self._runs={}; self._idempotency={}
    def create(self,tenant_id:str,request_id:str,*,parent_run_id=None,deadline_at=None,idempotency_key=None)->RunRecord:
        if idempotency_key and (tenant_id,idempotency_key) in self._idempotency:
            return self._runs[self._idempotency[(tenant_id,idempotency_key)]]
        r=RunRecord(new_id("run"),request_id,parent_run_id,tenant_id,RunState.ACCEPTED,utc_now(),utc_now(),deadline_at,idempotency_key)
        self._runs[r.run_id]=r
        if idempotency_key:self._idempotency[(tenant_id,idempotency_key)]=r.run_id
        return r
    def get(self,run_id): return self._runs[run_id]
    def transition(self,run_id,state,**metadata):
        r=self.get(run_id).transition(state,**metadata); self._runs[run_id]=r; return r


@dataclass(frozen=True)
class WorkerProfile:
    worker_id:str; status:str; cpu_cores:float=0; ram_mb:int=0; gpu_model:str|None=None; vram_mb:int=0
    capabilities:frozenset[str]=frozenset(); models:frozenset[str]=frozenset(); latency_ms:float=0
    cost_per_minute:float=0; locality:str|None=None; load:float=0

@dataclass(frozen=True)
class WorkRequirement:
    capabilities:frozenset[str]=frozenset(); models:frozenset[str]=frozenset(); min_cpu_cores:float=0
    min_ram_mb:int=0; min_vram_mb:int=0; locality:str|None=None; max_latency_ms:float|None=None
    max_cost_per_minute:float|None=None; priority:int=0

class WorkScheduler:
    """Filter feasible workers, then rank by explicit capability, locality and cost/latency objectives."""
    @staticmethod
    def feasible(w:WorkerProfile,r:WorkRequirement)->bool:
        return (w.status.upper()=="ONLINE" and r.capabilities.issubset(w.capabilities)
            and (not r.models or bool(r.models.intersection(w.models)))
            and w.cpu_cores>=r.min_cpu_cores and w.ram_mb>=r.min_ram_mb and w.vram_mb>=r.min_vram_mb
            and (not r.locality or w.locality==r.locality)
            and (r.max_latency_ms is None or w.latency_ms<=r.max_latency_ms)
            and (r.max_cost_per_minute is None or w.cost_per_minute<=r.max_cost_per_minute))
    @staticmethod
    def score(w:WorkerProfile,r:WorkRequirement)->float:
        return (r.priority*1000 + len(r.capabilities&w.capabilities)*25 + len(r.models&w.models)*40
            + (30 if r.locality and r.locality==w.locality else 0) - w.load*100 - w.latency_ms*.5 - w.cost_per_minute*10)
    def rank(self,workers:Iterable[WorkerProfile],r:WorkRequirement)->list[WorkerProfile]:
        return sorted((w for w in workers if self.feasible(w,r)),key=lambda w:self.score(w,r),reverse=True)


class EvidenceKind(str,Enum):
    RUNTIME_FACT="runtime_fact"; MEMORY="memory"; RETRIEVED_EVIDENCE="retrieved_evidence"
    TOOL_RESULT="tool_result"; MODEL_INFERENCE="model_inference"; USER_PROVIDED="user_provided"

@dataclass(frozen=True)
class Evidence:
    evidence_id:str; kind:EvidenceKind; content:Any; source:str; observed_at:str
    confidence:float|None=None; scope:str|None=None; provenance:Mapping[str,Any]=field(default_factory=dict)
    @classmethod
    def create(cls,kind,content,source,*,confidence=None,scope=None,provenance=None):
        if confidence is not None and not 0<=confidence<=1: raise ValueError("confidence must be between 0 and 1")
        return cls(new_id("ev"),kind,content,source,utc_now(),confidence,scope,provenance or {})

@dataclass(frozen=True)
class ToolSpec:
    name:str; version:str; description:str; input_schema:Mapping[str,Any]
    scopes:frozenset[str]=frozenset(); trust_level:str="untrusted"; side_effect:str="none"
    requires_confirmation:bool=False; timeout_seconds:int=30; rate_limit_per_minute:int=60; cost_units:float=0
    def authorize(self,granted_scopes:Iterable[str],*,approved=False):
        missing=self.scopes-set(granted_scopes)
        if missing: raise PermissionError(f"tool scope denied: {sorted(missing)}")
        if self.requires_confirmation and not approved: raise PermissionError(f"tool requires explicit confirmation: {self.name}")
        if self.timeout_seconds<=0 or self.rate_limit_per_minute<=0: raise ValueError("invalid tool runtime limits")

@dataclass(frozen=True)
class Artifact:
    artifact_id:str; run_id:str; name:str; media_type:str; size_bytes:int; sha256:str; created_at:str; storage_uri:str
    metadata:Mapping[str,Any]=field(default_factory=dict)
    @classmethod
    def from_bytes(cls,run_id,name,media_type,payload,storage_uri,metadata=None):
        return cls(new_id("artifact"),run_id,name,media_type,len(payload),hashlib.sha256(payload).hexdigest(),utc_now(),storage_uri,metadata or {})

@dataclass(frozen=True)
class TraceEvent:
    trace_id:str; run_id:str; event_type:str; timestamp:str; component:str; duration_ms:float|None=None
    attributes:Mapping[str,Any]=field(default_factory=dict)
    @classmethod
    def create(cls,run_id,event_type,component,*,duration_ms=None,attributes=None):
        return cls(new_id("trace"),run_id,event_type,utc_now(),component,duration_ms,attributes or {})
    def otel_attributes(self): return {f"sarembok.{k}":v for k,v in self.attributes.items()}


def canonical_json(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

__all__=["Artifact","Evidence","EvidenceKind","RunRecord","RunState","RunStore","ToolSpec","TraceEvent","WorkRequirement","WorkScheduler","WorkerProfile","canonical_json","new_id","utc_now"]
