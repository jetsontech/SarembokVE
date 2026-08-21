import unittest

from sarembok_knowledge_state import KnowledgeTrustStateMachine, TrustState


class KnowledgeTrustStateTests(unittest.TestCase):
    def setUp(self):
        self.machine = KnowledgeTrustStateMachine()

    def test_high_verified_confidence_becomes_trusted(self):
        decision = self.machine.evaluate("k1", TrustState.PENDING, 0.9, True)
        self.assertEqual(decision.new_state, TrustState.TRUSTED)

    def test_low_confidence_becomes_quarantined(self):
        decision = self.machine.evaluate("k1", TrustState.TRUSTED, 0.2, True)
        self.assertEqual(decision.new_state, TrustState.QUARANTINED)

    def test_middle_confidence_remains_pending(self):
        decision = self.machine.evaluate("k1", TrustState.PENDING, 0.5, True)
        self.assertEqual(decision.new_state, TrustState.PENDING)

    def test_unverified_knowledge_is_quarantined(self):
        decision = self.machine.evaluate("k1", TrustState.PENDING, 0.99, False)
        self.assertEqual(decision.new_state, TrustState.QUARANTINED)
        self.assertEqual(decision.reason, "verification_required")

    def test_invalid_thresholds_and_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            KnowledgeTrustStateMachine(0.2, 0.3)
        with self.assertRaises(ValueError):
            self.machine.evaluate("", TrustState.PENDING, 0.5, True)
        with self.assertRaises(ValueError):
            self.machine.evaluate("k1", TrustState.PENDING, 1.2, True)


if __name__ == "__main__":
    unittest.main()
