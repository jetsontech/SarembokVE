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

    def test_blocked_queued_task_is_repaired_and_hidden_from_worker(self):
        worker = "routing-compute-worker"
        server.store.db.execute(
            "INSERT INTO workers(worker_id,capabilities,status,last_heartbeat,active_tasks) VALUES(?,?,?,?,0)",
            (worker, '["compute"]', "ONLINE", server.now()),
        )
        dependency = server.store.create_task(
            "architecture_synthesis",
            None,
            {"pipelineId": "pipe-test", "stage": 1},
            "inference",
        )
        blocked = server.store.create_task(
            "verification_suite",
            None,
            {
                "pipelineId": "pipe-test",
                "stage": 3,
                "dependsOnTaskId": dependency["taskId"],
            },
            "compute",
        )
        server.store.db.execute(
            "UPDATE tasks SET status='QUEUED', assigned_worker_id=? WHERE task_id=?",
            (worker, blocked["taskId"]),
        )
        server.store.db.commit()

        listed = server.dispatch(
            "ListTasks",
            {"status": "PENDING_WORKER", "workerId": worker},
        )
        self.assertNotIn(blocked["taskId"], {row["taskId"] for row in listed["tasks"]})

        row = server.store.db.execute(
            "SELECT status, assigned_worker_id FROM tasks WHERE task_id=?",
            (blocked["taskId"],),
        ).fetchone()
        self.assertEqual(row[0], "PENDING_WORKER")
        self.assertIsNone(row[1])

    def test_fail_task_persists_error(self):
        worker = "routing-failure-worker"
        server.store.db.execute(
            "INSERT INTO workers(worker_id,capabilities,status,last_heartbeat,active_tasks) VALUES(?,?,?,?,0)",
            (worker, '["compute"]', "ONLINE", server.now()),
        )
        task = server.store.create_task(
            "web_automation",
            worker,
            {"url": "https://example.com"},
            "web_automation",
        )
        server.store.db.execute(
            "UPDATE tasks SET status='RUNNING' WHERE task_id=?",
            (task["taskId"],),
        )
        server.store.db.commit()
        result = server.dispatch("FailTask", {
            "taskId": task["taskId"],
            "workerId": worker,
            "error": "web_automation_failed: browser launch failed",
            "retryable": False,
        })
        self.assertEqual(result["status"], "FAILED")
        row = server.store.db.execute(
            "SELECT status, error FROM tasks WHERE task_id=?",
            (task["taskId"],),
        ).fetchone()
        self.assertEqual(row[0], "FAILED")
        self.assertEqual(row[1], "web_automation_failed: browser launch failed")

    def test_pipeline_state_finalizes_from_real_task_statuses(self):
        res = server.dispatch("ExecuteAutonomousPipeline", {"goal": "test pipeline finalization"})
        pipeline_id = res["pipelineId"]

        rows = server.store.db.execute(
            "SELECT task_id FROM tasks WHERE payload LIKE ? ORDER BY created_at ASC",
            (f'%"pipelineId": "{pipeline_id}"%',),
        ).fetchall()
        self.assertEqual(len(rows), 4)

        for task_row in rows:
            server.store.db.execute(
                "UPDATE tasks SET status='COMPLETED', result='{}' WHERE task_id=?",
                (task_row[0],),
            )
        server.store.db.commit()

        state = server.refresh_pipeline_status(pipeline_id)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["completedStages"], 4)
        self.assertEqual(state["failedStages"], 0)

        fetched = server.dispatch(
            "GetAutonomousPipeline",
            {"pipelineId": pipeline_id},
        )
        self.assertEqual(fetched["status"], "COMPLETED")
        self.assertEqual(len(fetched["tasks"]), 4)


if __name__ == "__main__":
    unittest.main()
