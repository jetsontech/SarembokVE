"""Adaptive age-aware confidence decay for Sarembok knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict


@dataclass(frozen=True)
class DecayResult:
    knowledge_id: str
    previous_confidence: float
    new_confidence: float
    age_days: float
    reason: str


class AdaptiveKnowledgeDecay:
    """Reduces stale confidence while allowing recent successful use to reinforce knowledge."""

    def __init__(self, half_life_days: float = 30.0, max_decay: float = 0.20):
        if half_life_days <= 0 or not 0.0 <= max_decay <= 1.0:
            raise ValueError("invalid_decay_parameters")
        self.half_life_days = half_life_days
        self.max_decay = max_decay
        self._confidence: Dict[str, float] = {}

    def set_confidence(self, knowledge_id: str, confidence: float) -> float:
        self._validate_id(knowledge_id)
        self._validate_confidence(confidence)
        self._confidence[knowledge_id] = confidence
        return confidence

    def apply_decay(
        self,
        knowledge_id: str,
        last_validated: datetime,
        now: datetime | None = None,
        recent_successes: int = 0,
    ) -> DecayResult:
        self._validate_id(knowledge_id)
        if knowledge_id not in self._confidence:
            raise RuntimeError(f"unknown_knowledge:{knowledge_id}")
        if recent_successes < 0:
            raise ValueError("recent_successes_must_not_be_negative")
        current_time = now or datetime.now(timezone.utc)
        if last_validated.tzinfo is None or current_time.tzinfo is None:
            raise ValueError("timestamps_must_be_timezone_aware")
        age_days = max(0.0, (current_time - last_validated).total_seconds() / 86400.0)
        previous = self._confidence[knowledge_id]
        decay_fraction = min(self.max_decay, age_days / self.half_life_days * self.max_decay)
        reinforcement = min(self.max_decay, recent_successes * 0.02)
        new_confidence = max(0.0, min(1.0, previous * (1.0 - decay_fraction) + reinforcement))
        self._confidence[knowledge_id] = new_confidence
        reason = f"age_days={age_days:.3f};decay={decay_fraction:.3f};recent_successes={recent_successes}"
        return DecayResult(knowledge_id, previous, new_confidence, age_days, reason)

    def get(self, knowledge_id: str) -> float:
        self._validate_id(knowledge_id)
        if knowledge_id not in self._confidence:
            raise RuntimeError(f"unknown_knowledge:{knowledge_id}")
        return self._confidence[knowledge_id]

    @staticmethod
    def _validate_id(knowledge_id: str) -> None:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")

    @staticmethod
    def _validate_confidence(value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
