"""Storage-neutral persistence adapter for knowledge events and snapshots."""
from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry, KnowledgeEventLog
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshot


@runtime_checkable
class KnowledgePersistenceBackend(Protocol):
    """Minimal backend contract; SQLite/WAL can implement this without changing core logic."""

    def append_event(self, entry: EventLogEntry) -> None: ...

    def load_events(self, after_sequence: int = 0) -> Iterable[EventLogEntry]: ...

    def save_snapshot(self, snapshot: KnowledgeStateSnapshot) -> None: ...

    def load_snapshots(self) -> Iterable[KnowledgeStateSnapshot]: ...


class KnowledgePersistenceAdapter:
    """Coordinates the event log/snapshot semantics with a persistence backend."""

    def __init__(self, backend: KnowledgePersistenceBackend):
        if not isinstance(backend, KnowledgePersistenceBackend):
            raise TypeError("backend_does_not_implement_knowledge_persistence_contract")
        self.backend = backend
        self.event_log = KnowledgeEventLog()

    def append(self, event: KnowledgeLifecycleEvent) -> EventLogEntry:
        entry = self.event_log.append(event)
        try:
            self.backend.append_event(entry)
        except Exception:
            # Keep the in-memory log consistent with a failed persistence operation.
            self.event_log._entries.pop()
            self.event_log._event_ids.discard(event.event_id)
            raise
        return entry

    def load_events(self, after_sequence: int = 0) -> list[EventLogEntry]:
        if after_sequence < 0:
            raise ValueError("sequence_must_not_be_negative")
        entries = sorted(self.backend.load_events(after_sequence), key=lambda entry: entry.sequence)
        return [entry for entry in entries if entry.sequence > after_sequence]

    def save_snapshot(self, snapshot: KnowledgeStateSnapshot) -> None:
        self.backend.save_snapshot(snapshot)

    def load_snapshots(self) -> list[KnowledgeStateSnapshot]:
        return list(self.backend.load_snapshots())
