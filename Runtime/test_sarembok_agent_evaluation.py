import unittest

from sarembok_agent_evaluation import AgentPerformanceEvaluator, AgentPerformanceRecord


class AgentEvaluationTests(unittest.TestCase):
    def test_evaluator_computes_fitness_from_history(self):
        evaluator = AgentPerformanceEvaluator()
        evaluator.record(AgentPerformanceRecord("a1", True, 1.0, 1.0, 1.0))
        evaluator.record(AgentPerformanceRecord("a1", False, 2.0, 1.0, 0.5))
        fitness = evaluator.evaluate("a1")
        self.assertEqual(fitness.success_rate, 0.5)
        self.assertGreater(fitness.fitness_score, 0.0)

    def test_rank_prefers_more_reliable_agent(self):
        evaluator = AgentPerformanceEvaluator([
            AgentPerformanceRecord("good", True, 1.0, 1.0, 1.0),
            AgentPerformanceRecord("weak", False, 1.0, 1.0, 0.0),
        ])
        ranking = evaluator.rank(["good", "weak"])
        self.assertEqual(ranking[0].agent_id, "good")

    def test_invalid_metrics_fail_closed(self):
        evaluator = AgentPerformanceEvaluator()
        with self.assertRaises(ValueError):
            evaluator.record(AgentPerformanceRecord("a", True, -1.0))
        with self.assertRaises(ValueError):
            evaluator.record(AgentPerformanceRecord("a", True, 1.0, 0.0, 1.1))

    def test_missing_history_fails_closed(self):
        with self.assertRaises(RuntimeError):
            AgentPerformanceEvaluator().evaluate("unknown")


if __name__ == "__main__":
    unittest.main()
