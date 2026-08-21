import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshotManager


class KnowledgeStateSnapshotTests(unittest.TestCase):
    def event(self, event_id, previous, new):
        return KnowledgeLifecycleEvent(event_id, LifecycleTransition("k1", previous, new, "test"))

    def test_snapshot_restore_preserves_state(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        manager = KnowledgeStateSnapshotManager()
        snapshot = manager.create(reducer, 1)
        restored = manager.restore(snapshot)
        self.assertEqual(restored.get("k1").state, LifecycleState.VERIFYING)

    def test_incremental_replay_applies_only_later_events(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        manager = KnowledgeStateSnapshotManager()
        snapshot = manager.create(reducer, 1)
        restored = manager.restore_and_replay(
            snapshot,
            [EventLogEntry(2, self.event("e2", LifecycleState.VERIFYING, LifecycleState.TRUSTED))],
        )
        self.assertEqual(restored.get("k1").state, LifecycleState.TRUSTED)

    def test_tampered_snapshot_is_rejected(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        manager = KnowledgeStateSnapshotManager()
        snapshot = manager.create(reducer, 1)
        object.__setattr__(snapshot, "last_sequence", 2)
        with self.assertRaises(ValueError):
            manager.restore(snapshot)

    def test_replay_sequence_gap_is_rejected(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        manager = KnowledgeStateSnapshotManager()
        snapshot = manager.create(reducer, 1)
        with self.assertRaises(ValueError):
            manager.restore_and_replay(snapshot, [EventLogEntry(3, self.event("e3", LifecycleState.VERIFYING, LifecycleState.TRUSTED))])


if __name__ == "__main__":
    unittest.main()
