import unittest

from sarembok_adaptive_workforce import (
    AdaptiveWorkforceOptimizer,
    CandidateAgent,
)


class AdaptiveWorkforceTests(unittest.TestCase):
    def setUp(self):
        self.optimizer = AdaptiveWorkforceOptimizer()
        self.candidates = [
            CandidateAgent("coder-weak", ["coding"], 0.61),
            CandidateAgent("coder-strong", ["coding"], 0.94),
            CandidateAgent("vision-1", ["vision"], 0.83),
        ]

    def test_selects_highest_fitness_for_capability(self):
        result = self.optimizer.select(["coding"], self.candidates)
        self.assertEqual(result[0].agent_id, "coder-strong")
        self.assertEqual(result[0].fitness_score, 0.94)

    def test_selects_best_agent_for_each_capability(self):
        result = self.optimizer.select(["coding", "vision"], self.candidates)
        self.assertEqual([item.agent_id for item in result], ["coder-strong", "vision-1"])

    def test_missing_capability_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.optimizer.select(["research"], self.candidates)


if __name__ == "__main__":
    unittest.main()
