"""Deterministic reconstruction of knowledge state from lifecycle events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_lifecycle import LifecycleState


@dataclass(frozen=True)
class KnowledgeState:
    knowledge_id: str
    state: LifecycleState
    last_event_id: str
    last_sequence: int


class KnowledgeStateReducer:
    """Reduces ordered lifecycle events into authoritative current state."""

    def __init__(self):
        self._state: Dict[str, KnowledgeState] = {}

    def apply(self, event: KnowledgeLifecycleEvent, sequence: int) -> KnowledgeState:
        if not event.event_id:
            raise ValueError("event_id_required")
        if sequence < 1:
            raise ValueError("sequence_must_be_positive")
        transition = event.transition
        if transition.previous_state == transition.new_state:
            raise ValueError("state_transition_must_change_state")

        current = self._state.get(transition.knowledge_id)
        if current is not None:
            if sequence <= current.last_sequence:
                raise ValueError("event_sequence_must_be_monotonic")
            if current.state != transition.previous_state:
                raise ValueError(
                    f"state_reconstruction_mismatch:{current.state.value}!={transition.previous_state.value}"
                )

        result = KnowledgeState(
            transition.knowledge_id,
            transition.new_state,
            event.event_id,
            sequence,
        )
        self._state[transition.knowledge_id] = result
        return result

    def rebuild(self, entries: Iterable[object]) -> Dict[str, KnowledgeState]:
        self._state = {}
        expected_sequence = 1
        for entry in entries:
            sequence = getattr(entry, "sequence", None)
            event = getattr(entry, "event", None)
            if sequence != expected_sequence or event is None:
                raise ValueError("event_log_sequence_or_event_invalid")
            self.apply(event, sequence)
            expected_sequence += 1
        return self.snapshot()

    def get(self, knowledge_id: str) -> KnowledgeState | None:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        return self._state.get(knowledge_id)

    def snapshot(self) -> Dict[str, KnowledgeState]:
        return dict(self._state)
