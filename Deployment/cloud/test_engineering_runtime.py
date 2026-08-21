import tempfile
import unittest
from pathlib import Path

try:
    from Deployment.cloud.engineering_runtime import EngineeringRuntime
except ImportError:
    from engineering_runtime import EngineeringRuntime


class EngineeringRuntimeTests(unittest.TestCase):
    def test_executes_and_recovers_state_through_runtime_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Sarembok", encoding="utf-8")
            runtime = EngineeringRuntime(root=root, data_root=root / "data")
            result = runtime.execute({
                "taskId": "runtime-test",
                "agentId": "engineering-agent",
                "steps": [{"id": "read", "toolId": "repository.read", "input": {"path": "README.md"}}],
            })
            self.assertEqual(result["state"], "COMPLETED")
            recovered = EngineeringRuntime(root=root, data_root=root / "data").get(result["execution_id"])
            self.assertEqual(recovered["state"], "COMPLETED")

    def test_unknown_tool_is_failed_and_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = EngineeringRuntime(root=root, data_root=root / "data")
            result = runtime.execute({"taskId": "denied", "steps": [{"toolId": "unknown", "input": {}}]})
            self.assertEqual(result["state"], "FAILED")
            self.assertTrue((root / "data" / "engineering_audit.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

