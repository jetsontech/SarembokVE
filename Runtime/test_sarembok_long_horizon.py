import unittest

from sarembok_long_horizon import (
    AgenticHorizon,
    AutonomousTask,
    LongHorizonTaskEngine,
    TaskStatus,
)


class LongHorizonTests(unittest.TestCase):
    def setUp(self):
        self.engine = LongHorizonTaskEngine()
        self.horizon = AgenticHorizon(
            max_duration_seconds=3600,
            max_steps=10,
            checkpoint_every_steps=2,
            max_recovery_attempts=2,
        )

    def test_checkpoint_is_created_at_horizon_interval(self):
        task = AutonomousTask("t1", "build feature", self.horizon)
        task = self.engine.start(task)
        task = self.engine.advance(task)
        task = self.engine.advance(task, {"progress": "two steps done"})
        self.assertEqual(task.status, TaskStatus.CHECKPOINTED)
        self.assertEqual(task.checkpoint.step, 2)

    def test_recovery_restores_checkpoint_and_counts_attempt(self):
        task = AutonomousTask("t2", "long job", self.horizon)
        task = self.engine.start(task)
        task = self.engine.advance(task)
        task = self.engine.advance(task, {"safe": True})
        task = self.engine.recover(task)
        self.assertEqual(task.status, TaskStatus.RECOVERING)
        self.assertEqual(task.current_step, 2)
        self.assertEqual(task.recovery_attempts, 1)

    def test_horizon_step_limit_fails_closed(self):
        horizon = AgenticHorizon(60, 1, checkpoint_every_steps=10)
        task = self.engine.start(AutonomousTask("t3", "bounded", horizon))
        task = self.engine.advance(task)
        task = self.engine.advance(task)
        self.assertEqual(task.status, TaskStatus.FAILED)

    def test_completion_requires_active_task(self):
        task = self.engine.start(AutonomousTask("t4", "finish", self.horizon))
        task = self.engine.complete(task)
        self.assertEqual(task.status, TaskStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
