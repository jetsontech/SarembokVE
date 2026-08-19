"""Memory-guided planning primitives for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PlanningMemory:
    lesson: str
    strategy: str = ""
    outcome: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class MemoryGuidedPlan:
    goal: str
    preferred_strategies: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)


class MemoryGuidedPlanner:
    """Uses recalled experience to bias planning toward proven strategies."""

    def plan(self, goal: str, memories: List[PlanningMemory], limit: int = 3) -> MemoryGuidedPlan:
        if not goal.strip():
            raise ValueError("goal_required")
        if limit < 1:
            raise ValueError("limit_must_be_positive")
        relevant = [memory for memory in memories if memory.outcome in ("success", "")]
        ranked = sorted(relevant, key=lambda memory: memory.score, reverse=True)
        strategies = list(dict.fromkeys(m.strategy for m in ranked if m.strategy))[:limit]
        lessons = list(dict.fromkeys(m.lesson for m in ranked if m.lesson))[:limit]
        return MemoryGuidedPlan(goal, strategies, lessons)
