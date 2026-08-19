import unittest

from sarembok_knowledge_lifecycle import KnowledgeLifecycleOrchestrator, LifecycleState


class KnowledgeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.lifecycle = KnowledgeLifecycleOrchestrator()

    def test_discovered_can_enter_verification(self):
        transition = self.lifecycle.transition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "new evidence")
        self.assertEqual(transition.new_state, LifecycleState.VERIFYING)

    def test_verification_can_produce_trusted_pending_or_quarantine(self):
        for target in (LifecycleState.TRUSTED, LifecycleState.PENDING, LifecycleState.QUARANTINED):
            self.assertTrue(self.lifecycle.can_transition(LifecycleState.VERIFYING, target))

    def test_trusted_knowledge_can_decay_or_retire(self):
        self.assertTrue(self.lifecycle.can_transition(LifecycleState.TRUSTED, LifecycleState.PENDING))
        self.assertTrue(self.lifecycle.can_transition(LifecycleState.TRUSTED, LifecycleState.QUARANTINED))
        self.assertTrue(self.lifecycle.can_transition(LifecycleState.TRUSTED, LifecycleState.RETIRED))

    def test_invalid_transition_fails_closed(self):
        with self.assertRaises(ValueError):
            self.lifecycle.transition("k1", LifecycleState.DISCOVERED, LifecycleState.TRUSTED, "skip verification")
        with self.assertRaises(ValueError):
            self.lifecycle.transition("k1", LifecycleState.RETIRED, LifecycleState.TRUSTED, "invalid restoration")

    def test_missing_identity_or_reason_fails_closed(self):
        with self.assertRaises(ValueError):
            self.lifecycle.transition("", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "reason")
        with self.assertRaises(ValueError):
            self.lifecycle.transition("k1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING, "")


if __name__ == "__main__":
    unittest.main()
