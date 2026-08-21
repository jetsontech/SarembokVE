import unittest

from agent import SarembokAgent
from memory import SarembokMemory
from sarembok_agent_runtime import SarembokAgentRuntime


class SarembokAgentRuntimeTests(unittest.TestCase):
    def test_event_is_executed_and_persisted(self):
        memory = SarembokMemory(":memory:")
        runtime = SarembokAgentRuntime(SarembokAgent(memory))
        result = runtime.handle_event({"event": "user_detected"}, "exec-1")

        self.assertEqual(result.state.value, "COMPLETED")
        self.assertEqual(memory.recall("last_execution_id"), "exec-1")
        persisted = memory.recall("execution:exec-1")
        self.assertIn('"state": "COMPLETED"', persisted)


if __name__ == "__main__":
    unittest.main()
