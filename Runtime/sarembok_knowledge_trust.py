"""Knowledge validation, trust scoring, and quarantine primitives for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, List


class KnowledgeStatus(str, Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"
    EXPIRED = "expired"


@dataclass(frozen=True)
class KnowledgeEvidence:
    evidence_id: str
    reproduced: bool = False
    verification_score: float = 0.0


@dataclass(frozen=True)
class TrustedKnowledge:
    knowledge_id: str
    lesson: str
    confidence: float
    status: KnowledgeStatus = KnowledgeStatus.PENDING
    evidence: List[KnowledgeEvidence] = None


class KnowledgeTrustManager:
    """Promotes or quarantines shared knowledge using explicit evidence."""

    def __init__(self):
        self._knowledge: Dict[str, TrustedKnowledge] = {}

    def register(self, knowledge: TrustedKnowledge) -> TrustedKnowledge:
        if knowledge.knowledge_id in self._knowledge:
            raise RuntimeError(f"knowledge_exists:{knowledge.knowledge_id}")
        if not knowledge.lesson:
            raise ValueError("knowledge_requires_lesson")
        if not 0.0 <= knowledge.confidence <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
        self._knowledge[knowledge.knowledge_id] = knowledge
        return knowledge

    def validate(self, knowledge_id: str) -> TrustedKnowledge:
        current = self._get(knowledge_id)
        evidence = current.evidence or []
        if not evidence:
            return replace(current, status=KnowledgeStatus.QUARANTINED)
        verified = [e for e in evidence if e.reproduced and 0.0 <= e.verification_score <= 1.0]
        if not verified:
            return replace(current, status=KnowledgeStatus.QUARANTINED)
        score = min(1.0, (current.confidence + sum(e.verification_score for e in verified) / len(verified)) / 2)
        status = KnowledgeStatus.TRUSTED if score >= 0.75 else KnowledgeStatus.PENDING
        updated = replace(current, confidence=score, status=status)
        self._knowledge[knowledge_id] = updated
        return updated

    def quarantine(self, knowledge_id: str) -> TrustedKnowledge:
        current = self._get(knowledge_id)
        updated = replace(current, status=KnowledgeStatus.QUARANTINED)
        self._knowledge[knowledge_id] = updated
        return updated

    def expire(self, knowledge_id: str) -> TrustedKnowledge:
        current = self._get(knowledge_id)
        updated = replace(current, status=KnowledgeStatus.EXPIRED)
        self._knowledge[knowledge_id] = updated
        return updated

    def get(self, knowledge_id: str) -> TrustedKnowledge:
        return self._get(knowledge_id)

    def _get(self, knowledge_id: str) -> TrustedKnowledge:
        try:
            return self._knowledge[knowledge_id]
        except KeyError as exc:
            raise RuntimeError(f"knowledge_not_found:{knowledge_id}") from exc
