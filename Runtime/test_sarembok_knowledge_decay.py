import unittest
from datetime import datetime, timezone, timedelta

from sarembok_knowledge_decay import AdaptiveKnowledgeDecay


class KnowledgeDecayTests(unittest.TestCase):
    def setUp(self):
        self.decay = AdaptiveKnowledgeDecay(half_life_days=30, max_decay=0.20)
        self.now = datetime(2026, 8, 19, tzinfo=timezone.utc)

    def test_old_knowledge_loses_confidence(self):
        self.decay.set_confidence("k1", 0.9)
        result = self.decay.apply_decay("k1", self.now - timedelta(days=30), self.now)
        self.assertLess(result.new_confidence, result.previous_confidence)
        self.assertEqual(result.age_days, 30.0)

    def test_recent_successes_reinforce_knowledge(self):
        self.decay.set_confidence("k1", 0.5)
        result = self.decay.apply_decay("k1", self.now - timedelta(days=1), self.now, recent_successes=5)
        self.assertGreater(result.new_confidence, result.previous_confidence)

    def test_confidence_remains_bounded(self):
        self.decay.set_confidence("k1", 1.0)
        result = self.decay.apply_decay("k1", self.now - timedelta(days=365), self.now, recent_successes=100)
        self.assertGreaterEqual(result.new_confidence, 0.0)
        self.assertLessEqual(result.new_confidence, 1.0)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            AdaptiveKnowledgeDecay(half_life_days=0)
        self.decay.set_confidence("k1", 0.5)
        with self.assertRaises(ValueError):
            self.decay.apply_decay("k1", self.now, self.now, recent_successes=-1)
        with self.assertRaises(ValueError):
            self.decay.apply_decay("k1", datetime(2026, 8, 18), self.now)
        with self.assertRaises(RuntimeError):
            self.decay.apply_decay("unknown", self.now, self.now)


if __name__ == "__main__":
    unittest.main()
