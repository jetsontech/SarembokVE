"""In-process event bus for knowledge lifecycle transitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition


@dataclass(frozen=True)
class KnowledgeLifecycleEvent:
    event_id: str
    transition: LifecycleTransition


class KnowledgeLifecycleEventBus:
    """Publishes immutable lifecycle events to isolated subscribers."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[KnowledgeLifecycleEvent], None]]] = {}
        self._published: Dict[str, KnowledgeLifecycleEvent] = {}

    def subscribe(self, event_type: str, handler: Callable[[KnowledgeLifecycleEvent], None]) -> None:
        if not event_type or not callable(handler):
            raise ValueError("event_type_and_callable_handler_required")
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: KnowledgeLifecycleEvent) -> KnowledgeLifecycleEvent:
        if not event.event_id:
            raise ValueError("event_id_required")
        if event.event_id in self._published:
            raise RuntimeError(f"lifecycle_event_exists:{event.event_id}")
        if event.transition.previous_state == event.transition.new_state:
            raise ValueError("lifecycle_event_must_change_state")

        self._published[event.event_id] = event
        for handler in tuple(self._subscribers.get("knowledge.lifecycle", ())):
            handler(event)
        return event

    def history(self) -> List[KnowledgeLifecycleEvent]:
        return list(self._published.values())
