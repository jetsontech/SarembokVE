"""Sarembok workforce planning primitives.

Builds a temporary, capability-driven agent workforce for a goal. This layer
plans composition; the existing registry, coordinator, and execution layers
remain responsible for creation and execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class WorkforceRequirement:
    capability: str
    objective: str
    required: bool = True
    max_agents: int = 1


@dataclass(frozen=True)
class WorkforceAssignment:
    agent_id: str
    capability: str
    objective: str
    temporary: bool = True


@dataclass(frozen=True)
class WorkforcePlan:
    goal: str
    assignments: List[WorkforceAssignment] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.missing_capabilities


class WorkforcePlanner:
    """Selects existing capable agents before requesting new workforce capacity."""

    def plan(
        self,
        goal: str,
        requirements: List[WorkforceRequirement],
        available_agents: Dict[str, List[str]],
    ) -> WorkforcePlan:
        assignments: List[WorkforceAssignment] = []
        missing: List[str] = []

        for requirement in requirements:
            candidates = available_agents.get(requirement.capability, [])
            selected = candidates[: requirement.max_agents]
            if not selected and requirement.required:
                missing.append(requirement.capability)
                continue
            assignments.extend(
                WorkforceAssignment(agent_id, requirement.capability, requirement.objective)
                for agent_id in selected
            )

        return WorkforcePlan(goal, assignments, missing)

    @staticmethod
    def merge_capabilities(*capability_sets: List[str]) -> List[str]:
        return sorted({capability for capabilities in capability_sets for capability in capabilities})
