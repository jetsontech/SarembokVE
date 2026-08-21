"""Runtime-owned gateway for the Sarembok Engineering Agent."""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from Engineering.Agent.engineering_agent import (
    AgentPolicy,
    EngineeringAgent,
    ExecutionPlan,
    JsonlStore,
    PlanStep,
    RepositoryReadTool,
    ValidationTool,
)
from Engineering.Agent.remote_connector import OpenSSHTransport, RemoteServer, RemoteTerminalTool


def _jsonable(value):
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


class EngineeringRuntime:
    """Bind the provider-neutral agent to Sarembok runtime persistence and RPC."""

    def __init__(self, *, root: str | os.PathLike[str], data_root: str | os.PathLike[str]):
        self.root = Path(root).resolve()
        self.data_root = Path(data_root).resolve()
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.checkpoints = JsonlStore(self.data_root / "engineering_checkpoints.jsonl")
        self.audit = JsonlStore(self.data_root / "engineering_audit.jsonl")
        self.records: dict[str, dict[str, Any]] = {}
        self.records_lock = threading.Lock()

        validation_commands = {
            "python_compile": (sys.executable, "-m", "compileall", "-q", str(self.root)),
            "agent_tests": (sys.executable, "-m", "unittest", "discover", "-s", str(self.root / "Engineering" / "Agent"), "-p", "test_*.py"),
        }
        tools = [RepositoryReadTool(self.root), ValidationTool(validation_commands)]
        permissions = {"repository.read", "engineering.validate"}
        maximum_risk = {"read_only"}
        self.remote_enabled = os.getenv("SAREMBOK_ENGINEERING_REMOTE_ENABLED", "false").lower() == "true"
        if self.remote_enabled:
            server = RemoteServer.from_environment()
            allowed = tuple(filter(None, os.getenv("SAREMBOK_ENGINEERING_REMOTE_COMMANDS", "git status,git log,python3 -m unittest").split(",")))
            tools.append(RemoteTerminalTool(OpenSSHTransport(server), allowed_commands=allowed))
            permissions.update({"server.connect", "server.execute"})
            maximum_risk.add("external")
        self.agent = EngineeringAgent(
            tools,
            policy=AgentPolicy(
                permissions=frozenset(permissions),
                maximum_risk=frozenset(maximum_risk),
                max_steps=min(32, int(os.getenv("SAREMBOK_ENGINEERING_MAX_STEPS", "32"))),
                max_retries=min(5, int(os.getenv("SAREMBOK_ENGINEERING_MAX_RETRIES", "2"))),
                checkpoint_interval=1,
                max_time_seconds=float(os.getenv("SAREMBOK_ENGINEERING_MAX_SECONDS", "300")),
            ),
            checkpoint_store=self.checkpoints,
            audit_store=self.audit,
        )

    def info(self) -> dict[str, Any]:
        return {
            "agentId": "sarembok-engineering-agent",
            "provider": "sarembok",
            "remoteEnabled": self.remote_enabled,
            "tools": [
                {"id": tool.descriptor.id, "version": tool.descriptor.version, "class": tool.descriptor.capability_class, "risk": tool.descriptor.risk_level, "provider": tool.descriptor.provider}
                for tool in self.agent.tools.values()
            ],
            "limits": {
                "maxSteps": self.agent.policy.max_steps,
                "maxRetries": self.agent.policy.max_retries,
                "maxSeconds": self.agent.policy.max_time_seconds,
            },
        }

    def execute(self, params: Mapping[str, Any]) -> dict[str, Any]:
        task_id = str(params.get("taskId", "")).strip()
        agent_id = str(params.get("agentId", "sarembok-engineering-agent")).strip()
        raw_steps = params.get("steps")
        if not task_id:
            raise ValueError("taskId is required")
        if not isinstance(raw_steps, list):
            raise ValueError("steps must be an array")
        steps = []
        for index, raw in enumerate(raw_steps):
            if not isinstance(raw, dict):
                raise ValueError(f"step {index} must be an object")
            step_id = str(raw.get("id", f"step-{index + 1}"))
            tool_id = str(raw.get("toolId", ""))
            tool_input = raw.get("input", {})
            if not tool_id or not isinstance(tool_input, dict):
                raise ValueError(f"step {step_id} requires toolId and object input")
            steps.append(PlanStep(step_id, tool_id, tool_input, raw.get("validationToolId")))
        plan = ExecutionPlan(task_id=task_id, agent_id=agent_id, steps=tuple(steps), version=str(params.get("planVersion", "1")))
        record = self.agent.execute(plan, execution_id=str(params.get("executionId")) if params.get("executionId") else None)
        result = _jsonable(record)
        with self.records_lock:
            self.records[record.execution_id] = result
        return result

    def get(self, execution_id: str) -> dict[str, Any]:
        with self.records_lock:
            if execution_id in self.records:
                return self.records[execution_id]
        for checkpoint in reversed(self.checkpoints.read_all()):
            record = checkpoint.get("record", {})
            if record.get("execution_id") == execution_id:
                return record
        raise ValueError(f"execution_not_found: {execution_id}")

