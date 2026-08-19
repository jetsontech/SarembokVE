"""Explicit lifecycle state machine for Sarembok knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet


class LifecycleState(str, Enum):
    DISCOVERED = "discovered"
    VERIFYING = "verifying"
    TRUSTED = "trusted"
    PENDING = "pending"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


@dataclass(frozen=True)
class LifecycleTransition:
    knowledge_id: str
    previous_state: LifecycleState
    new_state: LifecycleState
    reason: str


class KnowledgeLifecycleOrchestrator:
    """Authoritative, fail-closed lifecycle transition controller."""

    _ALLOWED: Dict[LifecycleState, FrozenSet[LifecycleState]] = {
        LifecycleState.DISCOVERED: frozenset({LifecycleState.VERIFYING, LifecycleState.QUARANTINED}),
        LifecycleState.VERIFYING: frozenset({LifecycleState.TRUSTED, LifecycleState.PENDING, LifecycleState.QUARANTINED}),
        LifecycleState.TRUSTED: frozenset({LifecycleState.PENDING, LifecycleState.QUARANTINED, LifecycleState.RETIRED}),
        LifecycleState.PENDING: frozenset({LifecycleState.VERIFYING, LifecycleState.TRUSTED, LifecycleState.QUARANTINED, LifecycleState.RETIRED}),
        LifecycleState.QUARANTINED: frozenset({LifecycleState.VERIFYING, LifecycleState.RETIRED}),
        LifecycleState.RETIRED: frozenset({LifecycleState.VERIFYING}),
    }

    def transition(self, knowledge_id: str, current: LifecycleState, target: LifecycleState, reason: str) -> LifecycleTransition:
        if not knowledge_id or not reason:
            raise ValueError("knowledge_id_and_reason_required")
        if target not in self._ALLOWED[current]:
            raise ValueError(f"invalid_lifecycle_transition:{current.value}->{target.value}")
        return LifecycleTransition(knowledge_id, current, target, reason)

    def can_transition(self, current: LifecycleState, target: LifecycleState) -> bool:
        return target in self._ALLOWED[current]
