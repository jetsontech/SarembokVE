"""Static security/truth-boundary gates for the production runtime.

These tests intentionally fail while known unsafe lineage remains in server.py.
They prevent a future merge from silently reintroducing fake infrastructure,
embedded credentials, or in-process code execution.
"""

from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
SOURCE = SERVER.read_text(encoding="utf-8")


class RuntimeSecurityContractTests(unittest.TestCase):
    def test_no_embedded_admin_passcode_defaults(self) -> None:
        self.assertNotRegex(
            SOURCE,
            r'ADMIN_PASSCODE\s*=\s*os\.getenv\([^\n]+\)\s*or\s*["\'][^"\']+["\']',
            "Admin authentication must fail closed when the configured secret is absent.",
        )
        self.assertNotIn('"sarembok2026"', SOURCE)
        self.assertNotIn('"joc"', SOURCE)

    def test_no_synthetic_sovereign_worker(self) -> None:
        self.assertNotIn(
            "SOVEREIGN_WORKER_ID = \"sarembok-edge-frontier-01\"",
            SOURCE,
            "Worker inventory must come from real registration/heartbeat, not synthetic startup state.",
        )
        self.assertNotIn("NVIDIA RTX 4090 Sovereign Tensor Core", SOURCE)
        self.assertNotRegex(SOURCE, r"def\s+ensure_sovereign_worker\s*\(")

    def test_compute_execution_must_use_real_scheduler(self) -> None:
        block = re.search(
            r'if method == "ExecuteComputeTask":(?P<body>.*?)(?=\n\s*if method == "Health":)',
            SOURCE,
            re.DOTALL,
        )
        self.assertIsNotNone(block, "ExecuteComputeTask handler must remain explicit and testable.")
        body = block.group("body")
        self.assertNotIn("ensure_sovereign_worker()", body)
        self.assertNotIn("SOVEREIGN_WORKER_ID", body)
        self.assertNotIn("'RUNNING'", body)
        self.assertNotIn('"RUNNING"', body)

    def test_no_in_process_python_sandbox(self) -> None:
        self.assertNotRegex(
            SOURCE,
            r'exec\s*\(\s*code_str\s*,\s*\{\s*["\']__builtins__["\']\s*:\s*__builtins__',
            "User code must not execute with the runtime process's Python builtins.",
        )
        self.assertNotRegex(
            SOURCE,
            r'exec\s*\(\s*code_snippet\s*,\s*\{\s*["\']__builtins__["\']\s*:\s*__builtins__',
            "Admin Python execution must not share the runtime process.",
        )

    def test_fleet_status_uses_registered_worker_count(self) -> None:
        fleet = re.search(
            r'def\s+fleet_status\(cls\).*?(?=\n\s*@classmethod\n\s*def\s+git_info)',
            SOURCE,
            re.DOTALL,
        )
        self.assertIsNotNone(fleet)
        body = fleet.group(0)
        self.assertNotIn('w_stats.get("totalWorkers", 0)', body)
        self.assertIn('w_stats.get("registeredWorkers", 0)', body)

    def test_no_duplicate_list_tasks_dispatch(self) -> None:
        self.assertEqual(
            SOURCE.count('if method == "ListTasks":'),
            1,
            "JSON-RPC dispatch must have one authoritative ListTasks implementation.",
        )


if __name__ == "__main__":
    unittest.main()
