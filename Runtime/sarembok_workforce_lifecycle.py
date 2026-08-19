"""Lifecycle management for Sarembok agent workforces."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, Optional


class WorkforceAgentState(str, Enum):
    CREATED = "created"
    DEPLOYED = "deployed"
    MONITORING = "monitoring"
    REASSIGNED = "reassigned"
    RETIRED = "retired"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkforceAgent:
    agent_id: str
    state: WorkforceAgentState = WorkforceAgentState.CREATED
    objective: str = ""
    performance_score: Optional[float] = None
    assignment_id: Optional[str] = None


class WorkforceLifecycleManager:
    """Owns explicit workforce-agent state transitions."""

    _allowed = {
        WorkforceAgentState.CREATED: {WorkforceAgentState.DEPLOYED, WorkforceAgentState.RETIRED},
        WorkforceAgentState.DEPLOYED: {WorkforceAgentState.MONITORING, WorkforceAgentState.FAILED},
        WorkforceAgentState.MONITORING: {
            WorkforceAgentState.REASSIGNED,
            WorkforceAgentState.RETIRED,
            WorkforceAgentState.FAILED,
        },
        WorkforceAgentState.REASSIGNED: {WorkforceAgentState.MONITORING, WorkforceAgentState.FAILED},
        WorkforceAgentState.FAILED: {WorkforceAgentState.REASSIGNED, WorkforceAgentState.RETIRED},
        WorkforceAgentState.RETIRED: set(),
    }

    def __init__(self):
        self._agents: Dict[str, WorkforceAgent] = {}

    def add(self, agent: WorkforceAgent) -> WorkforceAgent:
        if agent.agent_id in self._agents:
            raise RuntimeError(f"workforce_agent_exists:{agent.agent_id}")
        self._agents[agent.agent_id] = agent
        return agent

    def transition(
        self,
        agent_id: str,
        state: WorkforceAgentState,
        *,
        objective: Optional[str] = None,
        assignment_id: Optional[str] = None,
        performance_score: Optional[float] = None,
    ) -> WorkforceAgent:
        current = self.get(agent_id)
        if state not in self._allowed[current.state]:
            raise RuntimeError(f"invalid_workforce_transition:{current.state.value}->{state.value}")
        updated = replace(
            current,
            state=state,
            objective=current.objective if objective is None else objective,
            assignment_id=assignment_id if assignment_id is not None else current.assignment_id,
            performance_score=performance_score if performance_score is not None else current.performance_score,
        )
        self._agents[agent_id] = updated
        return updated

    def get(self, agent_id: str) -> WorkforceAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise RuntimeError(f"workforce_agent_not_found:{agent_id}") from exc

    def retire(self, agent_id: str) -> WorkforceAgent:
        return self.transition(agent_id, WorkforceAgentState.RETIRED)
