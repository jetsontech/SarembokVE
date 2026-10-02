"""Regression tests for task capability routing and task state reporting."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["SAREMBOK_DB_PATH"] = db_file.name

import Deployment.cloud.server as server


class TestTaskRouting(unittest.TestCase):
    def setUp(self):
        server.ensure_scheduler_schema()
        server.store.db.execute("DELETE FROM tasks")
        server.store.db.execute("DELETE FROM workers")
        server.store.db.commit()

    def tearDown(self):
        server.store.db.execute("DELETE FROM tasks")
        server.store.db.execute("DELETE FROM workers")
        server.store.db.commit()

    def test_required_capability_mapping(self):
        self.assertEqual(server.required_capability_for_task("host_action"), "host_control")
        self.assertEqual(server.required_capability_for_task("desktop"), "desktop")
        self.assertEqual(server.required_capability_for_task("web_automation"), "web_automation")
        self.assertEqual(server.required_capability_for_task("inference"), "inference")
        self.assertEqual(server.required_capability_for_task("meta_human"), "meta_human")
        self.assertEqual(server.required_capability_for_task("arbitrary_task"), "compute")

    def test_get_task_returns_real_result_and_error_fields(self):
        worker = "routing-test-worker"
        server.store.db.execute(
            "INSERT INTO workers(worker_id,capabilities,status,last_heartbeat,active_tasks) VALUES(?,?,?,?,0)",
            (worker, '["compute"]', "ONLINE", server.now()),
        )
        server.store.db.commit()

        task = server.dispatch("CreateTask", {
            "taskType": "arithmetic",
            "requiredCapability": "compute",
            "assignedWorkerId": worker,
            "payload": {"operation": "add", "a": 2, "b": 3},
        })
        state = server.dispatch("GetTask", {"taskId": task["taskId"]})
        self.assertEqual(state["taskType"], "arithmetic")
        self.assertEqual(state["requiredCapability"], "compute")
        self.assertEqual(state["payload"]["a"], 2)
        self.assertEqual(state["result"], {})
        self.assertIsNone(state["error"])

    def test_pipeline_dependencies_block_later_stage(self):
        # With no eligible workers, every stage remains pending; importantly,
        # each later stage carries a predecessor dependency.
        res = server.dispatch("ExecuteAutonomousPipeline", {"goal": "test dependency chain"})
        tasks = res["tasks"]
        self.assertEqual(len(tasks), 4)
        self.assertIsNone(tasks[0]["dependsOnTaskId"])
        self.assertEqual(tasks[1]["dependsOnTaskId"], tasks[0]["taskId"])
        self.assertEqual(tasks[2]["dependsOnTaskId"], tasks[1]["taskId"])
        self.assertEqual(tasks[3]["dependsOnTaskId"], tasks[2]["taskId"])


if __name__ == "__main__":
    unittest.main()
