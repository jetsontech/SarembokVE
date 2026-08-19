import unittest

from sarembok_governance_audit import GovernanceAuditLedger


class GovernanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.ledger = GovernanceAuditLedger()

    def test_records_and_reads_governance_history(self):
        record = self.ledger.record(
            "e1", "k1", "pending", "trusted", 0.9, True,
            "governance-engine", "confidence_meets_trust_threshold",
            timestamp="2026-08-19T00:00:00+00:00",
        )
        self.assertEqual(record.new_state, "trusted")
        self.assertEqual(self.ledger.history("k1")[0].event_id, "e1")

    def test_conflict_fields_are_recorded(self):
        record = self.ledger.record(
            "e2", "k2", "pending", "trusted", 0.85, True,
            "resolver", "selected_by_supported_conflict_resolution",
            "prefer_supported", "k2",
        )
        self.assertEqual(record.conflict_resolution, "prefer_supported")
        self.assertEqual(record.selected_knowledge_id, "k2")

    def test_duplicate_and_invalid_records_fail_closed(self):
        self.ledger.record("e1", "k1", "pending", "quarantined", 0.2, True, "engine", "low confidence")
        with self.assertRaises(RuntimeError):
            self.ledger.record("e1", "k1", "pending", "trusted", 0.9, True, "engine", "duplicate")
        with self.assertRaises(ValueError):
            self.ledger.record("e2", "k1", "pending", "trusted", 1.2, True, "engine", "bad confidence")
        with self.assertRaises(ValueError):
            self.ledger.record("e3", "k1", "pending", "pending", 0.5, True, "engine", "bad conflict", "escalate", "k1")


if __name__ == "__main__":
    unittest.main()
