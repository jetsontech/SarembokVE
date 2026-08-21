"""Sarembok agent registry and dynamic agent creation primitives.

The registry owns agent identity, capability discovery, lifecycle, and creation
requests. Model providers and execution runtimes remain replaceable adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Protocol


class AgentLifecycle(str, Enum):
    PROPOSED = "proposed"
    READY = "ready"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True)
class AgentSpecification:
    role: str
    capabilities: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    purpose: str = ""


@dataclass(frozen=True)
class RegisteredAgent:
    agent_id: str
    specification: AgentSpecification
    lifecycle: AgentLifecycle = AgentLifecycle.PROPOSED
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentFactory(Protocol):
    def create(self, agent_id: str, specification: AgentSpecification) -> RegisteredAgent: ...


class AgentRegistry:
    """Central registry for reusable and dynamically created Sarembok agents."""

    def __init__(self, factory: AgentFactory):
        self.factory = factory
        self._agents: Dict[str, RegisteredAgent] = {}

    def register(self, agent: RegisteredAgent) -> RegisteredAgent:
        if agent.agent_id in self._agents:
            raise RuntimeError(f"agent_already_registered:{agent.agent_id}")
        self._agents[agent.agent_id] = agent
        return agent

    def create(self, agent_id: str, specification: AgentSpecification) -> RegisteredAgent:
        if agent_id in self._agents:
            raise RuntimeError(f"agent_already_registered:{agent_id}")
        agent = self.factory.create(agent_id, specification)
        return self.register(agent)

    def get(self, agent_id: str) -> RegisteredAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise RuntimeError(f"agent_not_found:{agent_id}") from exc

    def find_by_capability(self, capability: str) -> List[RegisteredAgent]:
        return [
            agent for agent in self._agents.values()
            if capability in agent.specification.capabilities
            and agent.lifecycle != AgentLifecycle.RETIRED
        ]

    def activate(self, agent_id: str) -> RegisteredAgent:
        agent = self.get(agent_id)
        active = RegisteredAgent(agent.agent_id, agent.specification, AgentLifecycle.ACTIVE, agent.metadata)
        self._agents[agent_id] = active
        return active
