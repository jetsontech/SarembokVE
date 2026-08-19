import unittest

from sarembok_multi_agent import (
    AgentAssignment,
    AgentDescriptor,
    AgentRole,
    AgentStatus,
    AgentResult,
    MultiAgentCoordinator,
)


class FakeExecutor:
    def execute(self, agent, assignment):
        return AgentResult(assignment.assignment_id, agent.agent_id, True, "result://1")


class MultiAgentTests(unittest.TestCase):
    def test_specialized_agent_receives_assignment(self):
        agent = AgentDescriptor("coding-1", AgentRole.CODING, ["python"])
        coordinator = MultiAgentCoordinator([agent], FakeExecutor())
        result = coordinator.assign(
            AgentAssignment("a1", "coding-1", "task-1", "implement feature")
        )
        self.assertTrue(result.success)
        self.assertEqual(result.agent_id, "coding-1")

    def test_unavailable_agent_fails_closed(self):
        agent = AgentDescriptor("vision-1", AgentRole.VISION, status=AgentStatus.RUNNING)
        coordinator = MultiAgentCoordinator([agent], FakeExecutor())
        with self.assertRaises(RuntimeError):
            coordinator.assign(AgentAssignment("a2", "vision-1", "task-2", "inspect screen"))

    def test_all_results_must_succeed(self):
        results = [
            AgentResult("a1", "r1", True),
            AgentResult("a2", "r2", True),
        ]
        self.assertTrue(MultiAgentCoordinator.successful(results))


if __name__ == "__main__":
    unittest.main()
