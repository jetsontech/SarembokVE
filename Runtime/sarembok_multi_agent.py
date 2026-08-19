"""Provider-neutral multi-agent coordination primitives for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Protocol


class AgentRole(str, Enum):
    MASTER = "master"
    RESEARCH = "research"
    CODING = "coding"
    VISION = "vision"
    EXECUTION = "execution"
    VERIFICATION = "verification"


class AgentStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    role: AgentRole
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentAssignment:
    assignment_id: str
    agent_id: str
    task_id: str
    objective: str
    dependencies: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentResult:
    assignment_id: str
    agent_id: str
    success: bool
    output_ref: str | None = None
    evidence_refs: List[str] = field(default_factory=list)
    error: str | None = None


class AgentExecutor(Protocol):
    def execute(self, agent: AgentDescriptor, assignment: AgentAssignment) -> AgentResult: ...


class MultiAgentCoordinator:
    """Assigns work to specialized agents and tracks normalized results."""

    def __init__(self, agents: List[AgentDescriptor], executor: AgentExecutor):
        self.agents = agents
        self.executor = executor

    def assign(self, assignment: AgentAssignment) -> AgentResult:
        agent = next((a for a in self.agents if a.agent_id == assignment.agent_id), None)
        if agent is None:
            raise RuntimeError(f"agent_not_found:{assignment.agent_id}")
        if agent.status not in {AgentStatus.IDLE, AgentStatus.ASSIGNED}:
            raise RuntimeError(f"agent_unavailable:{agent.agent_id}:{agent.status.value}")
        return self.executor.execute(agent, assignment)

    @staticmethod
    def update_status(agent: AgentDescriptor, status: AgentStatus) -> AgentDescriptor:
        return replace(agent, status=status)

    @staticmethod
    def successful(results: List[AgentResult]) -> bool:
        return bool(results) and all(result.success for result in results)
