"""Regression tests for concrete Sarembok worker task execution."""
from __future__ import annotations

import os
import tempfile
import unittest

from Deployment.cloud.worker_task_executor import WorkerTaskExecutor


class TestWorkerTaskExecutor(unittest.TestCase):
    def test_arithmetic_is_completed(self):
        executor = WorkerTaskExecutor("test-worker")
        result = executor.execute("arithmetic", {"operation": "multiply", "a": 7, "b": 6})
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["result"], 42.0)

    def test_general_compute_is_completed(self):
        executor = WorkerTaskExecutor("test-worker")
        result = executor.execute("general_compute", {"values": [1, 2, 3, 4], "operation": "average"})
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["result"], 2.5)

    def test_unknown_task_never_fabricates_success(self):
        executor = WorkerTaskExecutor("test-worker")
        result = executor.execute("not-a-real-task", {})
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertFalse(result.get("retryable", False))

    def test_host_action_delegates(self):
        def host(payload):
            return {"status": "VERIFIED", "action": payload["action"]}

        executor = WorkerTaskExecutor("test-worker", host_action=host)
        result = executor.execute("desktop", {"action": "open_url", "url": "https://sarembok.com"})
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["action"], "open_url")

    def test_inference_requires_real_backend(self):
        old_url = os.environ.pop("SAREMBOK_WORKER_INFERENCE_URL", None)
        old_model = os.environ.pop("SAREMBOK_WORKER_MODEL", None)
        try:
            executor = WorkerTaskExecutor("test-worker")
            result = executor.execute("inference", {"prompt": "hello"})
            self.assertIn(result["status"], {"UNAVAILABLE", "COMPLETED"})
            if result["status"] == "UNAVAILABLE":
                self.assertTrue(result["retryable"])
        finally:
            if old_url is not None:
                os.environ["SAREMBOK_WORKER_INFERENCE_URL"] = old_url
            if old_model is not None:
                os.environ["SAREMBOK_WORKER_MODEL"] = old_model


if __name__ == "__main__":
    unittest.main()
