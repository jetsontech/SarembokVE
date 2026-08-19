"""Conflict detection and deterministic resolution for Sarembok knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class KnowledgeClaim:
    knowledge_id: str
    source_agent_id: str
    claim_key: str
    claim_value: str
    confidence: float
    evidence_count: int = 0


@dataclass(frozen=True)
class ConflictDecision:
    claim_key: str
    conflicting_ids: List[str]
    resolution: str
    selected_knowledge_id: str | None
    reason: str


class KnowledgeConflictResolver:
    """Detects contradictory claims and resolves them using evidence then confidence."""

    def resolve(self, claims: List[KnowledgeClaim]) -> ConflictDecision:
        if len(claims) < 2:
            raise ValueError("at_least_two_claims_required")
        keys = {claim.claim_key for claim in claims}
        if len(keys) != 1:
            raise ValueError("claims_must_share_claim_key")
        for claim in claims:
            if not claim.knowledge_id or not claim.source_agent_id or not claim.claim_value:
                raise ValueError("claim_requires_identity_source_and_value")
            if not 0.0 <= claim.confidence <= 1.0 or claim.evidence_count < 0:
                raise ValueError("invalid_claim_evidence_or_confidence")

        values = {claim.claim_value for claim in claims}
        if len(values) == 1:
            winner = max(claims, key=lambda c: (c.evidence_count, c.confidence, c.knowledge_id))
            return ConflictDecision(claims[0].claim_key, [c.knowledge_id for c in claims], "consistent", winner.knowledge_id, "claims_agree")

        ranked = sorted(claims, key=lambda c: (c.evidence_count, c.confidence), reverse=True)
        first, second = ranked[0], ranked[1]
        if (first.evidence_count, first.confidence) == (second.evidence_count, second.confidence):
            return ConflictDecision(claims[0].claim_key, [c.knowledge_id for c in claims], "escalate", None, "top_claims_are_equally_supported")
        return ConflictDecision(claims[0].claim_key, [c.knowledge_id for c in claims], "prefer_supported", first.knowledge_id, "higher_evidence_or_confidence")
