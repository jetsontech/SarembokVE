import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_state_reducer import KnowledgeStateReducer


class KnowledgeStateReducerTests(unittest.TestCase):
    def event(self, event_id, previous, new, reason="test"):
        return KnowledgeLifecycleEvent(
            event_id,
            LifecycleTransition("k1", previous, new, reason),
        )

    def test_reduces_ordered_events_to_current_state(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        state = reducer.apply(self.event("e2", LifecycleState.VERIFYING, LifecycleState.TRUSTED), 2)
        self.assertEqual(state.state, LifecycleState.TRUSTED)
        self.assertEqual(state.last_sequence, 2)

    def test_rebuild_reconstructs_state_from_event_log(self):
        entries = [
            EventLogEntry(1, self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING)),
            EventLogEntry(2, self.event("e2", LifecycleState.VERIFYING, LifecycleState.PENDING)),
        ]
        snapshot = KnowledgeStateReducer().rebuild(entries)
        self.assertEqual(snapshot["k1"].state, LifecycleState.PENDING)

    def test_state_chain_mismatch_fails_closed(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        with self.assertRaises(ValueError):
            reducer.apply(self.event("e2", LifecycleState.DISCOVERED, LifecycleState.TRUSTED), 2)

    def test_sequence_regression_fails_closed(self):
        reducer = KnowledgeStateReducer()
        reducer.apply(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING), 1)
        with self.assertRaises(ValueError):
            reducer.apply(self.event("e2", LifecycleState.VERIFYING, LifecycleState.TRUSTED), 1)

    def test_rebuild_rejects_missing_sequence(self):
        entries = [EventLogEntry(2, self.event("e2", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))]
        with self.assertRaises(ValueError):
            KnowledgeStateReducer().rebuild(entries)


if __name__ == "__main__":
    unittest.main()
