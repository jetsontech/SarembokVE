import tempfile
import unittest
from pathlib import Path

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_sqlite import SQLiteKnowledgePersistenceBackend
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshotManager


class SQLiteKnowledgePersistenceTests(unittest.TestCase):
    def event(self, event_id="e1"):
        return KnowledgeLifecycleEvent(
            event_id,
            LifecycleTransition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "test"),
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "knowledge.db"
        self.backend = SQLiteKnowledgePersistenceBackend(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_event_round_trip_preserves_sequence_and_transition(self):
        entry = EventLogEntry(1, self.event())
        self.backend.append_event(entry)
        loaded = list(self.backend.load_events())
        self.assertEqual(loaded, [entry])

    def test_wal_mode_is_enabled(self):
        import sqlite3
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

    def test_duplicate_event_id_is_rejected(self):
        self.backend.append_event(EventLogEntry(1, self.event()))
        with self.assertRaises(Exception):
            self.backend.append_event(EventLogEntry(2, self.event()))

    def test_snapshot_round_trip(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event(), 1)
        snapshot = KnowledgeStateSnapshotManager().create(reducer, 1)
        self.backend.save_snapshot(snapshot)
        self.assertEqual(list(self.backend.load_snapshots()), [snapshot])

    def test_incremental_event_loading(self):
        self.backend.append_event(EventLogEntry(1, self.event("e1")))
        self.backend.append_event(EventLogEntry(2, self.event("e2")))
        self.assertEqual([e.sequence for e in self.backend.load_events(1)], [2])


if __name__ == "__main__":
    unittest.main()
