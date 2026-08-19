"""Outcome-driven confidence feedback for Sarembok knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ConfidenceUpdate:
    knowledge_id: str
    previous_confidence: float
    new_confidence: float
    outcome: str
    reason: str


class KnowledgeConfidenceFeedback:
    """Adjusts knowledge confidence from observed usage outcomes."""

    def __init__(self, initial: Dict[str, float] | None = None):
        self._confidence = dict(initial or {})

    def set_initial(self, knowledge_id: str, confidence: float) -> float:
        self._validate_confidence(confidence)
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        self._confidence[knowledge_id] = confidence
        return confidence

    def apply(self, knowledge_id: str, outcome: str, impact_score: float) -> ConfidenceUpdate:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        if outcome not in ("success", "failure"):
            raise ValueError("outcome_must_be_success_or_failure")
        self._validate_confidence(impact_score)
        if knowledge_id not in self._confidence:
            raise RuntimeError(f"unknown_knowledge:{knowledge_id}")

        previous = self._confidence[knowledge_id]
        adjustment = 0.20 * impact_score
        if outcome == "failure":
            adjustment = -adjustment
        new_confidence = max(0.0, min(1.0, previous + adjustment))
        self._confidence[knowledge_id] = new_confidence
        reason = f"usage_outcome={outcome};impact_score={impact_score:.3f}"
        return ConfidenceUpdate(knowledge_id, previous, new_confidence, outcome, reason)

    def get(self, knowledge_id: str) -> float:
        if knowledge_id not in self._confidence:
            raise RuntimeError(f"unknown_knowledge:{knowledge_id}")
        return self._confidence[knowledge_id]

    @staticmethod
    def _validate_confidence(value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
