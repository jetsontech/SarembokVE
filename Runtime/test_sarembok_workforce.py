import unittest

from sarembok_workforce import WorkforcePlanner, WorkforceRequirement


class WorkforceTests(unittest.TestCase):
    def test_planner_prefers_available_capable_agents(self):
        plan = WorkforcePlanner().plan(
            "ship feature",
            [
                WorkforceRequirement("coding", "implement"),
                WorkforceRequirement("verification", "test"),
            ],
            {"coding": ["coder-1"], "verification": ["verify-1"]},
        )
        self.assertTrue(plan.ready)
        self.assertEqual([a.agent_id for a in plan.assignments], ["coder-1", "verify-1"])

    def test_missing_required_capability_makes_plan_not_ready(self):
        plan = WorkforcePlanner().plan(
            "ship feature",
            [WorkforceRequirement("vision", "inspect", required=True)],
            {},
        )
        self.assertFalse(plan.ready)
        self.assertEqual(plan.missing_capabilities, ["vision"])

    def test_optional_requirement_does_not_block_plan(self):
        plan = WorkforcePlanner().plan(
            "ship feature",
            [WorkforceRequirement("research", "background", required=False)],
            {},
        )
        self.assertTrue(plan.ready)

    def test_capability_sets_are_composed_deterministically(self):
        result = WorkforcePlanner.merge_capabilities(["vision", "coding"], ["coding", "voice"])
        self.assertEqual(result, ["coding", "vision", "voice"])


if __name__ == "__main__":
    unittest.main()
