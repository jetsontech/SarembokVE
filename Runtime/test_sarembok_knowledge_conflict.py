import unittest

from sarembok_knowledge_conflict import KnowledgeClaim, KnowledgeConflictResolver


class KnowledgeConflictTests(unittest.TestCase):
    def setUp(self):
        self.resolver = KnowledgeConflictResolver()

    def test_higher_evidence_claim_wins(self):
        decision = self.resolver.resolve([
            KnowledgeClaim("k1", "agent-a", "timeout", "30s", 0.7, 2),
            KnowledgeClaim("k2", "agent-b", "timeout", "60s", 0.8, 4),
        ])
        self.assertEqual(decision.resolution, "prefer_supported")
        self.assertEqual(decision.selected_knowledge_id, "k2")

    def test_equal_support_escalates(self):
        decision = self.resolver.resolve([
            KnowledgeClaim("k1", "agent-a", "timeout", "30s", 0.8, 3),
            KnowledgeClaim("k2", "agent-b", "timeout", "60s", 0.8, 3),
        ])
        self.assertEqual(decision.resolution, "escalate")
        self.assertIsNone(decision.selected_knowledge_id)

    def test_agreeing_claims_are_consistent(self):
        decision = self.resolver.resolve([
            KnowledgeClaim("k1", "agent-a", "timeout", "30s", 0.7, 1),
            KnowledgeClaim("k2", "agent-b", "timeout", "30s", 0.9, 2),
        ])
        self.assertEqual(decision.resolution, "consistent")

    def test_invalid_claims_fail_closed(self):
        with self.assertRaises(ValueError):
            self.resolver.resolve([KnowledgeClaim("k1", "a", "x", "1", 0.5, 1)])
        with self.assertRaises(ValueError):
            self.resolver.resolve([
                KnowledgeClaim("k1", "a", "x", "1", 0.5, 1),
                KnowledgeClaim("k2", "b", "y", "2", 0.5, 1),
            ])


if __name__ == "__main__":
    unittest.main()
