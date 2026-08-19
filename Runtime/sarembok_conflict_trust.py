"""Integration between conflict outcomes and knowledge trust state."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TrustState(str, Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class ConflictTrustDecision:
    knowledge_id: str
    previous_state: TrustState
    new_state: TrustState
    reason: str


class ConflictTrustIntegrator:
    """Maps conflict outcomes into conservative trust-state changes."""

    def evaluate(
        self,
        knowledge_id: str,
        current_state: TrustState,
        resolution: str,
        selected_knowledge_id: str | None,
    ) -> ConflictTrustDecision:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        if resolution not in ("prefer_supported", "escalate", "consistent"):
            raise ValueError("invalid_conflict_resolution")

        if resolution == "escalate":
            return ConflictTrustDecision(knowledge_id, current_state, TrustState.PENDING, "conflict_requires_review")

        if resolution == "prefer_supported":
            if not selected_knowledge_id:
                raise ValueError("selected_knowledge_required_for_preferred_resolution")
            if selected_knowledge_id == knowledge_id:
                return ConflictTrustDecision(knowledge_id, current_state, TrustState.TRUSTED, "claim_selected_by_supported_conflict_resolution")
            return ConflictTrustDecision(knowledge_id, current_state, TrustState.PENDING, "claim_not_selected_in_conflict_resolution")

        return ConflictTrustDecision(knowledge_id, current_state, TrustState.TRUSTED, "claim_consistent_with_competing_evidence")
