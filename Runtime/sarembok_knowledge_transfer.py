"""Cross-agent knowledge sharing primitives for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class KnowledgeArtifact:
    knowledge_id: str
    source_agent_id: str
    lesson: str
    strategy: str = ""
    capabilities: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(frozen=True)
class KnowledgeMatch:
    knowledge_id: str
    source_agent_id: str
    score: float
    lesson: str
    strategy: str


class CrossAgentKnowledgeBase:
    """Publishes validated knowledge and retrieves it for other agents."""

    def __init__(self):
        self._knowledge: Dict[str, KnowledgeArtifact] = {}

    def publish(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact:
        if artifact.knowledge_id in self._knowledge:
            raise RuntimeError(f"knowledge_exists:{artifact.knowledge_id}")
        if not artifact.source_agent_id or not artifact.lesson:
            raise ValueError("knowledge_requires_source_agent_and_lesson")
        if not 0.0 <= artifact.confidence <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
        self._knowledge[artifact.knowledge_id] = artifact
        return artifact

    def share(
        self,
        target_agent_id: str,
        capability: str = "",
        limit: int = 5,
    ) -> List[KnowledgeMatch]:
        if not target_agent_id:
            raise ValueError("target_agent_required")
        if limit < 1:
            raise ValueError("limit_must_be_positive")

        matches: List[KnowledgeMatch] = []
        for artifact in self._knowledge.values():
            score = artifact.confidence
            if capability and capability in artifact.capabilities:
                score += 1.0
            if artifact.source_agent_id == target_agent_id:
                # Knowledge is still reusable by its source, but receives no special privilege.
                score += 0.0
            matches.append(
                KnowledgeMatch(
                    artifact.knowledge_id,
                    artifact.source_agent_id,
                    score,
                    artifact.lesson,
                    artifact.strategy,
                )
            )
        return sorted(matches, key=lambda item: (-item.score, item.knowledge_id))[:limit]
