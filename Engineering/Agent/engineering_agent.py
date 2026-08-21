"""Sarembok-native, provider-neutral engineering execution controller.

The controller owns lifecycle, policy, checkpoints, recovery, and evidence.
A model or other reasoning system may produce an :class:`ExecutionPlan`, but
it is not required by this module and never receives execution authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


class AgentState(str, Enum):
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VALIDATING = "VALIDATING"
    CHECKPOINTED = "CHECKPOINTED"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


@dataclass(frozen=True)
class ToolDescriptor:
    id: str
    version: str
    capability_class: str
    required_permissions: frozenset[str]
    risk_level: str
    supports_dry_run: bool = False
    supports_rollback: bool = False
    provider: str = "sarembok"


class EngineeringTool(Protocol):
    descriptor: ToolDescriptor

    def invoke(self, input: Mapping[str, Any], *, dry_run: bool = False) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class PlanStep:
    id: str
    tool_id: str
    input: Mapping[str, Any]
    validation_tool_id: str | None = None


@dataclass(frozen=True)
class ExecutionPlan:
    task_id: str
    agent_id: str
    steps: tuple[PlanStep, ...]
    version: str = "1"


@dataclass(frozen=True)
class AgentPolicy:
    permissions: frozenset[str] = frozenset()
    maximum_risk: frozenset[str] = frozenset({"read_only"})
    max_steps: int = 32
    max_retries: int = 2
    checkpoint_interval: int = 1
    max_time_seconds: float = 300.0
    dry_run: bool = False

    def allows(self, descriptor: ToolDescriptor) -> bool:
        return (
            descriptor.required_permissions <= self.permissions
            and descriptor.risk_level in self.maximum_risk
        )


@dataclass
class ExecutionRecord:
    execution_id: str
    task_id: str
    agent_id: str
    state: AgentState = AgentState.QUEUED
    current_step: int = 0
    plan_version: str = ""
    retry_count: int = 0
    last_result: Mapping[str, Any] | None = None
    failure_reason: str | None = None
    checkpoint_id: str | None = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JsonlStore:
    """Small durable append-only store for checkpoints and audit evidence."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.path.chmod(0o600)

    def append(self, value: Mapping[str, Any]) -> None:
        line = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        self.path.chmod(0o600)

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


class EngineeringAgent:
    def __init__(
        self,
        tools: Sequence[EngineeringTool],
        *,
        policy: AgentPolicy,
        checkpoint_store: JsonlStore,
        audit_store: JsonlStore,
        clock=time.monotonic,
    ):
        self.tools = {tool.descriptor.id: tool for tool in tools}
        self.policy = policy
        self.checkpoints = checkpoint_store
        self.audit = audit_store
        self.clock = clock

    def execute(self, plan: ExecutionPlan, *, execution_id: str | None = None) -> ExecutionRecord:
        record = ExecutionRecord(
            execution_id=execution_id or str(uuid.uuid4()),
            task_id=plan.task_id,
            agent_id=plan.agent_id,
            plan_version=plan.version,
        )
        started = self.clock()
        self._transition(record, AgentState.PLANNING, "plan accepted", plan=plan)
        if len(plan.steps) > self.policy.max_steps:
            return self._fail(record, "plan exceeds max_steps")
        for index, step in enumerate(plan.steps):
            if self.clock() - started > self.policy.max_time_seconds:
                return self._fail(record, "execution time limit exceeded")
            record.current_step = index
            tool = self.tools.get(step.tool_id)
            if tool is None:
                return self._fail(record, f"unknown tool: {step.tool_id}")
            if not self.policy.allows(tool.descriptor):
                return self._fail(record, f"capability denied: {step.tool_id}")
            result = self._invoke_with_recovery(record, tool, step)
            if result is None:
                return record
            record.last_result = result
            self._transition(record, AgentState.OBSERVING, "tool result recorded", result=result)
            if step.validation_tool_id:
                validator = self.tools.get(step.validation_tool_id)
                if validator is None or not self.policy.allows(validator.descriptor):
                    return self._fail(record, f"validation capability denied: {step.validation_tool_id}")
                self._transition(record, AgentState.VALIDATING, "validation started")
                validation = validator.invoke({"step": asdict(step), "result": result}, dry_run=self.policy.dry_run)
                self._audit(record, "validation", step.validation_tool_id, validation)
                if validation.get("valid") is not True:
                    return self._fail(record, "validation failed")
            if (index + 1) % self.policy.checkpoint_interval == 0:
                self._checkpoint(record, plan)
        self._transition(record, AgentState.COMPLETED, "plan completed")
        self._checkpoint(record, plan)
        return record

    def _invoke_with_recovery(self, record, tool, step):
        for attempt in range(self.policy.max_retries + 1):
            record.retry_count = attempt
            self._transition(record, AgentState.EXECUTING, "tool invocation", tool=step.tool_id, attempt=attempt)
            try:
                result = tool.invoke(step.input, dry_run=self.policy.dry_run)
                self._audit(record, "tool", step.tool_id, result)
                return result
            except Exception as error:  # tool failures are evidence, never success
                self._audit(record, "tool_error", step.tool_id, {"error": str(error), "attempt": attempt})
                if attempt >= self.policy.max_retries:
                    return self._fail(record, f"tool failed after retries: {step.tool_id}")
                self._transition(record, AgentState.RECOVERY, "retry scheduled", error=str(error))
        return None

    def _checkpoint(self, record, plan):
        checkpoint_id = hashlib.sha256(f"{record.execution_id}:{record.current_step}:{record.updated_at}".encode()).hexdigest()[:16]
        record.checkpoint_id = checkpoint_id
        if record.state != AgentState.COMPLETED:
            self._transition(record, AgentState.CHECKPOINTED, "durable checkpoint written")
        self.checkpoints.append({"checkpoint_id": checkpoint_id, "record": asdict(record), "plan": asdict(plan)})

    def _transition(self, record, state, event, **details):
        record.state = state
        record.updated_at = time.time()
        self._audit(record, event, None, details)

    def _audit(self, record, event, tool_id, details):
        self.audit.append({"execution_id": record.execution_id, "task_id": record.task_id, "agent_id": record.agent_id, "event": event, "tool_id": tool_id, "state": record.state.value, "step": record.current_step, "details": details, "timestamp": time.time()})

    def _fail(self, record, reason):
        record.failure_reason = reason
        self._transition(record, AgentState.FAILED, reason)
        return record


class RepositoryReadTool:
    descriptor = ToolDescriptor("repository.read", "1", "observe", frozenset({"repository.read"}), "read_only", provider="sarembok")

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).resolve()

    def invoke(self, input, *, dry_run=False):
        relative = Path(str(input["path"]))
        target = (self.root / relative).resolve()
        if self.root not in target.parents and target != self.root:
            raise PermissionError("path escapes repository root")
        if target.is_dir():
            return {"path": str(relative), "entries": sorted(p.name for p in target.iterdir())}
        return {"path": str(relative), "content": target.read_text(encoding="utf-8")}


class ValidationTool:
    descriptor = ToolDescriptor("engineering.validate", "1", "execute", frozenset({"engineering.validate"}), "read_only", provider="sarembok")

    def __init__(self, commands: Mapping[str, Sequence[str]]):
        self.commands = {name: tuple(command) for name, command in commands.items()}

    def invoke(self, input, *, dry_run=False):
        name = str(input["command"])
        command = self.commands.get(name)
        if command is None:
            raise PermissionError(f"validation command is not allowlisted: {name}")
        if dry_run:
            return {"valid": True, "dry_run": True, "command": list(command)}
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return {"valid": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}

