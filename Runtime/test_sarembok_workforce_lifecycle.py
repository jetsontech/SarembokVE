import unittest

from sarembok_workforce_lifecycle import (
    WorkforceAgent,
    WorkforceAgentState,
    WorkforceLifecycleManager,
)


class WorkforceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.manager = WorkforceLifecycleManager()
        self.manager.add(WorkforceAgent("agent-1", objective="research"))

    def test_agent_moves_through_deploy_and_monitor(self):
        self.manager.transition("agent-1", WorkforceAgentState.DEPLOYED)
        agent = self.manager.transition("agent-1", WorkforceAgentState.MONITORING, performance_score=0.9)
        self.assertEqual(agent.state, WorkforceAgentState.MONITORING)
        self.assertEqual(agent.performance_score, 0.9)

    def test_monitoring_agent_can_be_reassigned(self):
        self.manager.transition("agent-1", WorkforceAgentState.DEPLOYED)
        self.manager.transition("agent-1", WorkforceAgentState.MONITORING)
        agent = self.manager.transition(
            "agent-1", WorkforceAgentState.REASSIGNED, assignment_id="assignment-2"
        )
        self.assertEqual(agent.assignment_id, "assignment-2")

    def test_retirement_is_terminal(self):
        self.manager.retire("agent-1")
        with self.assertRaises(RuntimeError):
            self.manager.transition("agent-1", WorkforceAgentState.DEPLOYED)

    def test_invalid_transition_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.manager.transition("agent-1", WorkforceAgentState.MONITORING)


if __name__ == "__main__":
    unittest.main()
