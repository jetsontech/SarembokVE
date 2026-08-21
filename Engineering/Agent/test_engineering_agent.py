import tempfile
import unittest
from pathlib import Path

from engineering_agent import (
    AgentPolicy,
    AgentState,
    EngineeringAgent,
    ExecutionPlan,
    JsonlStore,
    PlanStep,
    RepositoryReadTool,
    ToolDescriptor,
)


class ResultTool:
    descriptor = ToolDescriptor("test.result", "1", "observe", frozenset({"test.result"}), "read_only")

    def invoke(self, input, *, dry_run=False):
        return {"valid": True, "value": input["value"]}


class FailingTool:
    descriptor = ToolDescriptor("test.flaky", "1", "execute", frozenset({"test.flaky"}), "read_only")

    def __init__(self):
        self.calls = 0

    def invoke(self, input, *, dry_run=False):
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("transient")
        return {"ok": True}


class EngineeringAgentTests(unittest.TestCase):
    def test_authorized_execution_checkpoints_and_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Sarembok", encoding="utf-8")
            agent = EngineeringAgent(
                [RepositoryReadTool(root), ResultTool()],
                policy=AgentPolicy(permissions=frozenset({"repository.read", "test.result"}), maximum_risk=frozenset({"read_only"})),
                checkpoint_store=JsonlStore(root / "checkpoints.jsonl"),
                audit_store=JsonlStore(root / "audit.jsonl"),
            )
            plan = ExecutionPlan("task-1", "engineering-agent", (PlanStep("step-1", "repository.read", {"path": "README.md"}),))
            record = agent.execute(plan, execution_id="exec-1")
            self.assertEqual(record.state, AgentState.COMPLETED)
            self.assertEqual(len(JsonlStore(root / "checkpoints.jsonl").read_all()), 1)
            self.assertTrue(JsonlStore(root / "audit.jsonl").read_all())

    def test_denied_capability_never_invokes_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flaky = FailingTool()
            agent = EngineeringAgent([flaky], policy=AgentPolicy(), checkpoint_store=JsonlStore(root / "c"), audit_store=JsonlStore(root / "a"))
            record = agent.execute(ExecutionPlan("task", "agent", (PlanStep("s", "test.flaky", {}),)))
            self.assertEqual(record.state, AgentState.FAILED)
            self.assertEqual(flaky.calls, 0)

    def test_transient_failure_recovers_with_bounded_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flaky = FailingTool()
            agent = EngineeringAgent([flaky], policy=AgentPolicy(permissions=frozenset({"test.flaky"}), max_retries=1), checkpoint_store=JsonlStore(root / "c"), audit_store=JsonlStore(root / "a"))
            record = agent.execute(ExecutionPlan("task", "agent", (PlanStep("s", "test.flaky", {}),)))
            self.assertEqual(record.state, AgentState.COMPLETED)
            self.assertEqual(flaky.calls, 2)


if __name__ == "__main__":
    unittest.main()

