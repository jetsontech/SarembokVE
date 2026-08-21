import unittest

from sarembok_conflict_provenance import ConflictProvenanceLedger


class ConflictProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.ledger = ConflictProvenanceLedger()

    def test_records_conflict_decision_and_history(self):
        event = self.ledger.record(
            "e1", "timeout", ["k1", "k2"], "prefer_supported", "k2",
            "resolver", "k2 had stronger evidence", "2026-01-01T00:00:00+00:00"
        )
        self.assertEqual(event.selected_knowledge_id, "k2")
        self.assertEqual(self.ledger.history("timeout")[0].event_id, "e1")

    def test_escalation_cannot_select_a_winner(self):
        with self.assertRaises(ValueError):
            self.ledger.record("e1", "timeout", ["k1", "k2"], "escalate", "k1", "resolver", "equal support")

    def test_selected_knowledge_must_be_in_conflict(self):
        with self.assertRaises(ValueError):
            self.ledger.record("e1", "timeout", ["k1", "k2"], "prefer_supported", "k3", "resolver", "winner")

    def test_duplicate_and_invalid_records_fail_closed(self):
        self.ledger.record("e1", "timeout", ["k1", "k2"], "escalate", None, "resolver", "equal support")
        with self.assertRaises(RuntimeError):
            self.ledger.record("e1", "timeout", ["k1", "k2"], "escalate", None, "resolver", "duplicate")
        with self.assertRaises(ValueError):
            self.ledger.record("e2", "timeout", ["k1"], "escalate", None, "resolver", "not enough claims")


if __name__ == "__main__":
    unittest.main()
