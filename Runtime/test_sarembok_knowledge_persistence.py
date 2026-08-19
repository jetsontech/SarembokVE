import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_persistence import KnowledgePersistenceAdapter
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshotManager


class FakeBackend:
    def __init__(self):
        self.events = []
        self.snapshots = []

    def append_event(self, entry):
        self.events.append(entry)

    def load_events(self, after_sequence=0):
        return [entry for entry in self.events if entry.sequence > after_sequence]

    def save_snapshot(self, snapshot):
        self.snapshots.append(snapshot)

    def load_snapshots(self):
        return list(self.snapshots)


class FailingBackend(FakeBackend):
    def append_event(self, entry):
        raise IOError("persistence failure")


class KnowledgePersistenceTests(unittest.TestCase):
    def event(self):
        return KnowledgeLifecycleEvent(
            "e1",
            LifecycleTransition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "test"),
        )

    def test_append_persists_ordered_event(self):
        backend = FakeBackend()
        adapter = KnowledgePersistenceAdapter(backend)
        entry = adapter.append(self.event())
        self.assertEqual(entry.sequence, 1)
        self.assertEqual(backend.events, [entry])

    def test_load_events_filters_sequence(self):
        backend = FakeBackend()
        adapter = KnowledgePersistenceAdapter(backend)
        entry = EventLogEntry(2, self.event())
        backend.events.append(entry)
        self.assertEqual(adapter.load_events(1), [entry])
        self.assertEqual(adapter.load_events(2), [])

    def test_snapshot_round_trip(self):
        backend = FakeBackend()
        adapter = KnowledgePersistenceAdapter(backend)
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event(), 1)
        snapshot = KnowledgeStateSnapshotManager().create(reducer, 1)
        adapter.save_snapshot(snapshot)
        self.assertEqual(adapter.load_snapshots(), [snapshot])

    def test_failed_persistence_rolls_back_event_log(self):
        adapter = KnowledgePersistenceAdapter(FailingBackend())
        with self.assertRaises(IOError):
            adapter.append(self.event())
        self.assertEqual(adapter.event_log.last_sequence(), 0)

    def test_invalid_backend_is_rejected(self):
        with self.assertRaises(TypeError):
            KnowledgePersistenceAdapter(object())


if __name__ == "__main__":
    unittest.main()
