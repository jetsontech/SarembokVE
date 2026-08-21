import unittest

from sarembok_knowledge_impact import KnowledgeImpactTracker, KnowledgeUsage


class KnowledgeImpactTests(unittest.TestCase):
    def setUp(self):
        self.tracker = KnowledgeImpactTracker()

    def test_usage_updates_impact_metrics(self):
        self.tracker.record(KnowledgeUsage("u1", "k1", "agent-a", "task-1", "success", 0.9))
        self.tracker.record(KnowledgeUsage("u2", "k1", "agent-b", "task-2", "failure", 0.2))
        impact = self.tracker.impact("k1")
        self.assertEqual(impact.usage_count, 2)
        self.assertEqual(impact.success_count, 1)
        self.assertEqual(impact.failure_count, 1)
        self.assertEqual(impact.success_rate, 0.5)
        self.assertAlmostEqual(impact.average_impact, 0.55)

    def test_duplicate_and_invalid_usage_fail_closed(self):
        usage = KnowledgeUsage("u1", "k1", "agent-a", "task-1", "success", 0.9)
        self.tracker.record(usage)
        with self.assertRaises(RuntimeError):
            self.tracker.record(usage)
        with self.assertRaises(ValueError):
            self.tracker.record(KnowledgeUsage("u2", "k1", "agent-a", "task-2", "unknown", 0.5))
        with self.assertRaises(ValueError):
            self.tracker.record(KnowledgeUsage("u3", "k1", "agent-a", "task-3", "success", 1.2))

    def test_missing_history_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.tracker.impact("unknown")


if __name__ == "__main__":
    unittest.main()
