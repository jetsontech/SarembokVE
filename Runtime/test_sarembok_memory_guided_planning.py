import unittest

from sarembok_memory_guided_planning import MemoryGuidedPlanner, PlanningMemory


class MemoryGuidedPlanningTests(unittest.TestCase):
    def test_successful_memory_influences_strategy_selection(self):
        plan = MemoryGuidedPlanner().plan(
            "ship feature",
            [
                PlanningMemory("tests reduce regressions", "test-first", "success", 0.95),
                PlanningMemory("guessing failed", "guess-first", "failure", 1.0),
                PlanningMemory("validate interfaces", "contract-first", "success", 0.8),
            ],
        )
        self.assertEqual(plan.preferred_strategies, ["test-first", "contract-first"])

    def test_limit_is_respected(self):
        plan = MemoryGuidedPlanner().plan(
            "ship",
            [PlanningMemory("a", "one", "success", 1.0), PlanningMemory("b", "two", "success", 0.9)],
            limit=1,
        )
        self.assertEqual(plan.preferred_strategies, ["one"])

    def test_invalid_inputs_fail_closed(self):
        planner = MemoryGuidedPlanner()
        with self.assertRaises(ValueError):
            planner.plan("", [])
        with self.assertRaises(ValueError):
            planner.plan("goal", [], limit=0)


if __name__ == "__main__":
    unittest.main()
