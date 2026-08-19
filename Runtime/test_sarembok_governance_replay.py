import unittest

from sarembok_governance_audit import GovernanceAuditRecord
from sarembok_governance_replay import GovernanceReplayEngine


class GovernanceReplayTests(unittest.TestCase):
    def setUp(self):
        self.engine = GovernanceReplayEngine()
        self.record = GovernanceAuditRecord(
            "e1", "k1", "pending", "trusted", 0.9, True,
            None, None, "engine", "confidence_meets_trust_threshold",
            "2026-08-19T00:00:00+00:00",
        )

    def test_matching_replay(self):
        result = self.engine.replay(self.record, lambda kid, confidence, verified, conflict, selected: "trusted")
        self.assertTrue(result.matches)
        self.assertEqual(result.replayed_state, "trusted")

    def test_drift_is_detected(self):
        result = self.engine.replay(self.record, lambda kid, confidence, verified, conflict, selected: "pending")
        self.assertFalse(result.matches)
        self.assertIn("governance_drift", result.explanation)

    def test_explain_contains_decision_context(self):
        explanation = self.engine.explain(self.record)
        self.assertIn("knowledge=k1", explanation)
        self.assertIn("confidence=0.900", explanation)
        self.assertIn("reason=confidence_meets_trust_threshold", explanation)


if __name__ == "__main__":
    unittest.main()
