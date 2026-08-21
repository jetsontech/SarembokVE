"""Automated knowledge trust-state transitions for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TrustState(str, Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class TrustDecision:
    knowledge_id: str
    previous_state: TrustState
    new_state: TrustState
    confidence: float
    reason: str


class KnowledgeTrustStateMachine:
    """Maps bounded confidence and evidence signals to explicit trust states."""

    def __init__(self, trust_threshold: float = 0.75, quarantine_threshold: float = 0.25):
        if not 0.0 <= quarantine_threshold < trust_threshold <= 1.0:
            raise ValueError("invalid_trust_thresholds")
        self.trust_threshold = trust_threshold
        self.quarantine_threshold = quarantine_threshold

    def evaluate(self, knowledge_id: str, current_state: TrustState, confidence: float, verified: bool) -> TrustDecision:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")

        if not verified:
            new_state = TrustState.QUARANTINED
            reason = "verification_required"
        elif confidence >= self.trust_threshold:
            new_state = TrustState.TRUSTED
            reason = "confidence_meets_trust_threshold"
        elif confidence <= self.quarantine_threshold:
            new_state = TrustState.QUARANTINED
            reason = "confidence_below_quarantine_threshold"
        else:
            new_state = TrustState.PENDING
            reason = "confidence_requires_more_evidence"

        return TrustDecision(knowledge_id, current_state, new_state, confidence, reason)
