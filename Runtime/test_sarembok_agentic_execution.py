import unittest

from sarembok_agentic_execution import (
    AgenticExecutionEngine,
    ExecutionLimits,
    ExecutionRecord,
    ExecutionState,
)


class AgenticExecutionTests(unittest.TestCase):
    def test_bounded_success_and_checkpoint(self):
        record = ExecutionRecord("e1", "t1", "a1")
        engine = AgenticExecutionEngine(ExecutionLimits(max_steps=3, checkpoint_interval=1))
        result = engine.run(record, [lambda r: "ok"], lambda value, r: value == "ok")
        self.assertEqual(result.state, ExecutionState.COMPLETED)
        self.assertTrue(result.checkpoints)

    def test_step_horizon_escalates(self):
        record = ExecutionRecord("e2", "t2", "a1")
        engine = AgenticExecutionEngine(ExecutionLimits(max_steps=0))
        result = engine.run(record, [lambda r: "never"], lambda value, r: True)
        self.assertEqual(result.state, ExecutionState.ESCALATED)
        self.assertEqual(result.error, "max_steps_exceeded")

    def test_failed_action_is_bounded(self):
        record = ExecutionRecord("e3", "t3", "a1")
        engine = AgenticExecutionEngine(ExecutionLimits(max_retries=1))

        def fail(_):
            raise RuntimeError("boom")

        result = engine.run(record, [fail], lambda value, r: True)
        self.assertEqual(result.state, ExecutionState.FAILED)
        self.assertEqual(result.retries, 2)


if __name__ == "__main__":
    unittest.main()
