"""Knowledge usage and outcome impact tracking for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class KnowledgeUsage:
    usage_id: str
    knowledge_id: str
    agent_id: str
    task_id: str
    outcome: str
    impact_score: float
    notes: str = ""


@dataclass(frozen=True)
class KnowledgeImpact:
    knowledge_id: str
    usage_count: int
    success_count: int
    failure_count: int
    average_impact: float
    success_rate: float


class KnowledgeImpactTracker:
    """Records knowledge usage and derives outcome-based impact metrics."""

    def __init__(self):
        self._usage: Dict[str, KnowledgeUsage] = {}

    def record(self, usage: KnowledgeUsage) -> KnowledgeUsage:
        if usage.usage_id in self._usage:
            raise RuntimeError(f"usage_exists:{usage.usage_id}")
        if not usage.knowledge_id or not usage.agent_id or not usage.task_id:
            raise ValueError("usage_requires_knowledge_agent_and_task")
        if usage.outcome not in ("success", "failure"):
            raise ValueError("outcome_must_be_success_or_failure")
        if not 0.0 <= usage.impact_score <= 1.0:
            raise ValueError("impact_score_must_be_between_zero_and_one")
        self._usage[usage.usage_id] = usage
        return usage

    def impact(self, knowledge_id: str) -> KnowledgeImpact:
        records = [u for u in self._usage.values() if u.knowledge_id == knowledge_id]
        if not records:
            raise RuntimeError(f"no_usage_history:{knowledge_id}")
        successes = sum(u.outcome == "success" for u in records)
        failures = len(records) - successes
        return KnowledgeImpact(
            knowledge_id=knowledge_id,
            usage_count=len(records),
            success_count=successes,
            failure_count=failures,
            average_impact=sum(u.impact_score for u in records) / len(records),
            success_rate=successes / len(records),
        )

    def history(self, knowledge_id: str) -> List[KnowledgeUsage]:
        return sorted(
            (u for u in self._usage.values() if u.knowledge_id == knowledge_id),
            key=lambda u: u.usage_id,
        )
