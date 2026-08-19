"""Runtime integration facade for persistent knowledge lifecycle state."""
from __future__ import annotations

from pathlib import Path

from sarembok_knowledge_bus import KnowledgeLifecycleEventBus
from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_persistence import KnowledgePersistenceAdapter
from sarembok_knowledge_recovery import KnowledgeRecoveryManager, RecoveryReport
from sarembok_knowledge_sqlite import SQLiteKnowledgePersistenceBackend
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshotManager


class PersistentKnowledgeRuntime:
    """Coordinates lifecycle events, durable storage, reduction, snapshots, and recovery."""

    def __init__(self, database_path: str | Path):
        self.backend = SQLiteKnowledgePersistenceBackend(database_path)
        self.persistence = KnowledgePersistenceAdapter(self.backend)
        self.reducer = KnowledgeStateReducer()
        self.snapshots = KnowledgeStateSnapshotManager()
        self.recovery = KnowledgeRecoveryManager(self.snapshots)
        self.events = KnowledgeLifecycleEventBus()
        self.last_recovery_report: RecoveryReport | None = None

    def recover(self) -> RecoveryReport:
        reducer, report = self.recovery.recover(
            self.persistence.load_snapshots(),
            self.persistence.load_events(),
        )
        self.reducer = reducer
        self.last_recovery_report = report
        return report

    def publish(self, event: KnowledgeLifecycleEvent):
        entry = self.persistence.append(event)
        self.reducer.apply(event, entry.sequence)
        self.events.publish(event)
        return entry

    def checkpoint(self):
        sequence = self.persistence.event_log.last_sequence()
        snapshot = self.snapshots.create(self.reducer, sequence)
        self.persistence.save_snapshot(snapshot)
        return snapshot

    def get_state(self, knowledge_id: str):
        return self.reducer.get(knowledge_id)
