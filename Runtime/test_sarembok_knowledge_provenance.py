import unittest

from sarembok_knowledge_provenance import KnowledgeProvenanceLedger


class KnowledgeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.ledger = KnowledgeProvenanceLedger()

    def test_records_and_explains_knowledge_history(self):
        self.ledger.record("e1", "k1", "discovered", "agent-a", "observed result", ["obs-1"], "2026-01-01T00:00:00+00:00")
        self.ledger.record("e2", "k1", "verified", "verifier-b", "reproduced result", ["test-1"], "2026-01-01T00:01:00+00:00")
        history = self.ledger.history("k1")
        self.assertEqual([event.event_type for event in history], ["discovered", "verified"])
        explanation = self.ledger.explain("k1")
        self.assertEqual(explanation["event_count"], 2)
        self.assertEqual(explanation["latest_event"].event_id, "e2")

    def test_duplicate_event_fails_closed(self):
        self.ledger.record("e1", "k1", "discovered", "agent-a", "observed")
        with self.assertRaises(RuntimeError):
            self.ledger.record("e1", "k1", "verified", "agent-b", "reproduced")

    def test_required_provenance_fields_are_validated(self):
        with self.assertRaises(ValueError):
            self.ledger.record("e1", "", "discovered", "agent-a", "observed")

    def test_history_requires_knowledge_id(self):
        with self.assertRaises(ValueError):
            self.ledger.history("")


if __name__ == "__main__":
    unittest.main()
