"""Durable, ordered knowledge lifecycle event log with replay support."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent


@dataclass(frozen=True)
class EventLogEntry:
    sequence: int
    event: KnowledgeLifecycleEvent


class KnowledgeEventLog:
    """Append-only in-memory durable-boundary abstraction with deterministic replay."""

    def __init__(self):
        self._entries: List[EventLogEntry] = []
        self._event_ids: set[str] = set()

    def append(self, event: KnowledgeLifecycleEvent) -> EventLogEntry:
        if not event.event_id:
            raise ValueError("event_id_required")
        if event.event_id in self._event_ids:
            raise RuntimeError(f"event_already_logged:{event.event_id}")
        entry = EventLogEntry(len(self._entries) + 1, event)
        self._entries.append(entry)
        self._event_ids.add(event.event_id)
        return entry

    def entries(self) -> List[EventLogEntry]:
        return list(self._entries)

    def replay(self, handler: Callable[[KnowledgeLifecycleEvent], None], from_sequence: int = 1) -> int:
        if not callable(handler):
            raise ValueError("callable_replay_handler_required")
        if from_sequence < 1:
            raise ValueError("sequence_must_start_at_one")
        replayed = 0
        for entry in self._entries:
            if entry.sequence >= from_sequence:
                handler(entry.event)
                replayed += 1
        return replayed

    def last_sequence(self) -> int:
        return len(self._entries)
