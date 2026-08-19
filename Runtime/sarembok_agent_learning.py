"""Agent experience memory and evidence-based learning primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AgentExperience:
    experience_id: str
    agent_id: str
    task_id: str
    outcome: str
    lesson: str
    strategy: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentLearning:
    agent_id: str
    lessons: List[str]
    successful_strategies: List[str]
    failed_strategies: List[str]
    experience_count: int


class AgentLearningMemory:
    """Stores normalized experience and derives reusable lessons."""

    def __init__(self):
        self._experiences: Dict[str, AgentExperience] = {}

    def remember(self, experience: AgentExperience) -> AgentExperience:
        if experience.experience_id in self._experiences:
            raise RuntimeError(f"experience_exists:{experience.experience_id}")
        if not experience.agent_id or not experience.task_id or not experience.lesson:
            raise ValueError("experience_requires_agent_task_and_lesson")
        self._experiences[experience.experience_id] = experience
        return experience

    def recall(self, agent_id: str, tag: Optional[str] = None) -> List[AgentExperience]:
        results = [e for e in self._experiences.values() if e.agent_id == agent_id]
        if tag is not None:
            results = [e for e in results if tag in e.tags]
        return sorted(results, key=lambda e: e.experience_id)

    def learn(self, agent_id: str) -> AgentLearning:
        experiences = self.recall(agent_id)
        if not experiences:
            raise RuntimeError(f"no_experience_history:{agent_id}")
        successful = [e.strategy for e in experiences if e.outcome == "success" and e.strategy]
        failed = [e.strategy for e in experiences if e.outcome == "failure" and e.strategy]
        lessons = list(dict.fromkeys(e.lesson for e in experiences))
        successful = list(dict.fromkeys(successful))
        failed = list(dict.fromkeys(failed))
        return AgentLearning(agent_id, lessons, successful, failed, len(experiences))
