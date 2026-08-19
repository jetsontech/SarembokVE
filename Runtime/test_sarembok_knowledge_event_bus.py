import unittest

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent, KnowledgeLifecycleEventBus
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition


class KnowledgeLifecycleEventBusTests(unittest.TestCase):
    def setUp(self):
        self.bus = KnowledgeLifecycleEventBus()
        self.transition = LifecycleTransition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "new evidence")

    def test_subscriber_receives_lifecycle_event(self):
        received = []
        self.bus.subscribe("knowledge.lifecycle", received.append)
        event = KnowledgeLifecycleEvent("e1", self.transition)
        self.bus.publish(event)
        self.assertEqual(received, [event])

    def test_history_is_recorded(self):
        event = KnowledgeLifecycleEvent("e1", self.transition)
        self.bus.publish(event)
        self.assertEqual(self.bus.history(), [event])

    def test_duplicate_event_ids_fail_closed(self):
        event = KnowledgeLifecycleEvent("e1", self.transition)
        self.bus.publish(event)
        with self.assertRaises(RuntimeError):
            self.bus.publish(event)

    def test_invalid_events_fail_closed(self):
        with self.assertRaises(ValueError):
            self.bus.publish(KnowledgeLifecycleEvent("", self.transition))
        same = LifecycleTransition("k1", LifecycleState.TRUSTED, LifecycleState.TRUSTED, "noop")
        with self.assertRaises(ValueError):
            self.bus.publish(KnowledgeLifecycleEvent("e2", same))


if __name__ == "__main__":
    unittest.main()
