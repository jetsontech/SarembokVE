import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import KnowledgeEventLog
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition


class KnowledgeEventLogTests(unittest.TestCase):
    def setUp(self):
        transition = LifecycleTransition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "new evidence")
        self.event = KnowledgeLifecycleEvent("e1", transition)
        self.log = KnowledgeEventLog()

    def test_append_assigns_monotonic_sequence(self):
        first = self.log.append(self.event)
        second = self.log.append(KnowledgeLifecycleEvent("e2", self.event.transition))
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(self.log.last_sequence(), 2)

    def test_duplicate_events_are_rejected(self):
        self.log.append(self.event)
        with self.assertRaises(RuntimeError):
            self.log.append(self.event)

    def test_replay_from_sequence(self):
        self.log.append(self.event)
        event2 = KnowledgeLifecycleEvent("e2", self.event.transition)
        self.log.append(event2)
        received = []
        count = self.log.replay(received.append, from_sequence=2)
        self.assertEqual(count, 1)
        self.assertEqual(received, [event2])

    def test_invalid_replay_requests_fail_closed(self):
        with self.assertRaises(ValueError):
            self.log.replay(None)
        with self.assertRaises(ValueError):
            self.log.replay(lambda event: None, 0)


if __name__ == "__main__":
    unittest.main()
