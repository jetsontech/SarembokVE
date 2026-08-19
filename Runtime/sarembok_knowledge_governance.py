"""Unified governance decision layer for Sarembok knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GovernanceState(str, Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class GovernanceInput:
    knowledge_id: str
    confidence: float
    verified: bool
    conflict_resolution: str | None = None
    selected_knowledge_id: str | None = None
    recent_successes: int = 0


@dataclass(frozen=True)
class GovernanceDecision:
    knowledge_id: str
    previous_state: GovernanceState
    new_state: GovernanceState
    reason: str


class KnowledgeGovernanceEngine:
    """Coordinates verification, conflict, confidence, and usage signals conservatively."""

    def __init__(self, trust_threshold: float = 0.75, quarantine_threshold: float = 0.25):
        if not 0.0 <= quarantine_threshold < trust_threshold <= 1.0:
            raise ValueError("invalid_governance_thresholds")
        self.trust_threshold = trust_threshold
        self.quarantine_threshold = quarantine_threshold

    def decide(self, current_state: GovernanceState, signal: GovernanceInput) -> GovernanceDecision:
        if not signal.knowledge_id:
            raise ValueError("knowledge_id_required")
        if not 0.0 <= signal.confidence <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
        if signal.recent_successes < 0:
            raise ValueError("recent_successes_must_not_be_negative")

        if not signal.verified:
            return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.QUARANTINED, "verification_required")

        if signal.conflict_resolution == "escalate":
            return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.PENDING, "conflict_requires_review")

        if signal.conflict_resolution == "prefer_supported":
            if signal.selected_knowledge_id is None:
                raise ValueError("selected_knowledge_required_for_preferred_resolution")
            if signal.selected_knowledge_id != signal.knowledge_id:
                return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.PENDING, "claim_not_selected_in_conflict_resolution")

        if signal.confidence <= self.quarantine_threshold:
            return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.QUARANTINED, "confidence_below_quarantine_threshold")
        if signal.confidence >= self.trust_threshold:
            return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.TRUSTED, "confidence_meets_trust_threshold")
        return GovernanceDecision(signal.knowledge_id, current_state, GovernanceState.PENDING, "confidence_requires_more_evidence")
