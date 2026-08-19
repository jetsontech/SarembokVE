import unittest

from sarembok_conflict_trust import ConflictTrustIntegrator, TrustState


class ConflictTrustIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.integrator = ConflictTrustIntegrator()

    def test_selected_claim_is_trusted(self):
        decision = self.integrator.evaluate("k1", TrustState.PENDING, "prefer_supported", "k1")
        self.assertEqual(decision.new_state, TrustState.TRUSTED)

    def test_non_selected_claim_is_pending(self):
        decision = self.integrator.evaluate("k1", TrustState.TRUSTED, "prefer_supported", "k2")
        self.assertEqual(decision.new_state, TrustState.PENDING)

    def test_escalated_conflict_requires_review(self):
        decision = self.integrator.evaluate("k1", TrustState.TRUSTED, "escalate", None)
        self.assertEqual(decision.new_state, TrustState.PENDING)

    def test_consistent_claim_is_trusted(self):
        decision = self.integrator.evaluate("k1", TrustState.PENDING, "consistent", "k1")
        self.assertEqual(decision.new_state, TrustState.TRUSTED)

    def test_invalid_preferred_resolution_fails_closed(self):
        with self.assertRaises(ValueError):
            self.integrator.evaluate("k1", TrustState.PENDING, "prefer_supported", None)
        with self.assertRaises(ValueError):
            self.integrator.evaluate("k1", TrustState.PENDING, "invalid", "k1")


if __name__ == "__main__":
    unittest.main()
