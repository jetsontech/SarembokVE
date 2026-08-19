import unittest

from sarembok_knowledge_governance import GovernanceInput, GovernanceState, KnowledgeGovernanceEngine


class KnowledgeGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.engine = KnowledgeGovernanceEngine()

    def test_verified_high_confidence_is_trusted(self):
        result = self.engine.decide(
            GovernanceState.PENDING,
            GovernanceInput("k1", 0.9, True),
        )
        self.assertEqual(result.new_state, GovernanceState.TRUSTED)

    def test_unverified_knowledge_is_quarantined(self):
        result = self.engine.decide(
            GovernanceState.TRUSTED,
            GovernanceInput("k1", 0.99, False),
        )
        self.assertEqual(result.new_state, GovernanceState.QUARANTINED)

    def test_conflict_escalation_is_pending(self):
        result = self.engine.decide(
            GovernanceState.TRUSTED,
            GovernanceInput("k1", 0.9, True, "escalate"),
        )
        self.assertEqual(result.new_state, GovernanceState.PENDING)

    def test_non_selected_conflict_claim_is_pending(self):
        result = self.engine.decide(
            GovernanceState.TRUSTED,
            GovernanceInput("k1", 0.9, True, "prefer_supported", "k2"),
        )
        self.assertEqual(result.new_state, GovernanceState.PENDING)

    def test_low_confidence_is_quarantined(self):
        result = self.engine.decide(
            GovernanceState.PENDING,
            GovernanceInput("k1", 0.2, True),
        )
        self.assertEqual(result.new_state, GovernanceState.QUARANTINED)

    def test_middle_confidence_remains_pending(self):
        result = self.engine.decide(
            GovernanceState.PENDING,
            GovernanceInput("k1", 0.5, True),
        )
        self.assertEqual(result.new_state, GovernanceState.PENDING)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            self.engine.decide(GovernanceState.PENDING, GovernanceInput("", 0.5, True))
        with self.assertRaises(ValueError):
            self.engine.decide(GovernanceState.PENDING, GovernanceInput("k1", 1.1, True))
        with self.assertRaises(ValueError):
            self.engine.decide(GovernanceState.PENDING, GovernanceInput("k1", 0.9, True, "prefer_supported"))


if __name__ == "__main__":
    unittest.main()
