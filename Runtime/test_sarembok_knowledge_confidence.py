import unittest

from sarembok_knowledge_confidence import KnowledgeConfidenceFeedback


class KnowledgeConfidenceTests(unittest.TestCase):
    def setUp(self):
        self.feedback = KnowledgeConfidenceFeedback({"k1": 0.5})

    def test_successful_usage_increases_confidence(self):
        update = self.feedback.apply("k1", "success", 0.8)
        self.assertEqual(update.previous_confidence, 0.5)
        self.assertAlmostEqual(update.new_confidence, 0.66)

    def test_failed_usage_decreases_confidence(self):
        update = self.feedback.apply("k1", "failure", 0.5)
        self.assertAlmostEqual(update.new_confidence, 0.4)

    def test_confidence_is_bounded(self):
        self.feedback.set_initial("high", 1.0)
        self.feedback.apply("high", "success", 1.0)
        self.assertEqual(self.feedback.get("high"), 1.0)
        self.feedback.set_initial("low", 0.0)
        self.feedback.apply("low", "failure", 1.0)
        self.assertEqual(self.feedback.get("low"), 0.0)

    def test_invalid_or_unknown_knowledge_fails_closed(self):
        with self.assertRaises(ValueError):
            self.feedback.apply("k1", "unknown", 0.5)
        with self.assertRaises(ValueError):
            self.feedback.apply("k1", "success", 1.1)
        with self.assertRaises(RuntimeError):
            self.feedback.apply("unknown", "success", 0.5)


if __name__ == "__main__":
    unittest.main()
