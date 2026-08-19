import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_recovery import KnowledgeRecoveryManager
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshotManager


class KnowledgeRecoveryTests(unittest.TestCase):
    def event(self, event_id, previous, new):
        return KnowledgeLifecycleEvent(event_id, LifecycleTransition("k1", previous, new, "test"))

    def test_recovers_from_latest_valid_checkpoint(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        snapshot = KnowledgeStateSnapshotManager().create(reducer, 1)
        events = [
            EventLogEntry(2, self.event("e2", LifecycleState.VERIFYING, LifecycleState.PENDING)),
            EventLogEntry(3, self.event("e3", LifecycleState.PENDING, LifecycleState.TRUSTED)),
        ]
        restored, report = KnowledgeRecoveryManager().recover([snapshot], events)
        self.assertEqual(restored.get("k1").state, LifecycleState.TRUSTED)
        self.assertEqual(report.status, "recovered")
        self.assertEqual(report.replayed_events, 2)

    def test_invalid_checkpoint_falls_back_to_full_replay(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        snapshot = KnowledgeStateSnapshotManager().create(reducer, 1)
        object.__setattr__(snapshot, "digest", "tampered")
        events = [EventLogEntry(1, self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))]
        restored, report = KnowledgeRecoveryManager().recover([snapshot], events)
        self.assertEqual(restored.get("k1").state, LifecycleState.VERIFYING)
        self.assertEqual(report.status, "full_replay")

    def test_event_gap_fails_closed(self):
        events = [EventLogEntry(2, self.event("e2", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))]
        with self.assertRaises(ValueError):
            KnowledgeRecoveryManager().recover([], events)

    def test_empty_recovery_is_explicit(self):
        _, report = KnowledgeRecoveryManager().recover([], [])
        self.assertEqual(report.status, "empty")


if __name__ == "__main__":
    unittest.main()
