import tempfile
import unittest
from pathlib import Path

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime


class PersistentKnowledgeRuntimeTests(unittest.TestCase):
    def event(self, event_id, previous, new):
        return KnowledgeLifecycleEvent(
            event_id,
            LifecycleTransition("k1", previous, new, "runtime test"),
        )

    def test_publish_checkpoint_and_restart_recover_state(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "knowledge.db"
            runtime = PersistentKnowledgeRuntime(db)
            runtime.publish(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))
            runtime.checkpoint()
            runtime.publish(self.event("e2", LifecycleState.VERIFYING, LifecycleState.TRUSTED))

            restarted = PersistentKnowledgeRuntime(db)

            self.assertEqual(restarted.last_recovery_report.status, "recovered")
            self.assertEqual(restarted.get_state("k1").state, LifecycleState.TRUSTED)

    def test_restart_continues_event_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "knowledge.db"
            first = PersistentKnowledgeRuntime(db)
            first.publish(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))
            restarted = PersistentKnowledgeRuntime(db)
            entry = restarted.publish(self.event("e2", LifecycleState.VERIFYING, LifecycleState.TRUSTED))
            self.assertEqual(entry.sequence, 2)
            self.assertEqual(restarted.get_state("k1").state, LifecycleState.TRUSTED)

    def test_publish_persists_before_runtime_state_is_advanced(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = PersistentKnowledgeRuntime(Path(directory) / "knowledge.db")
            entry = runtime.publish(self.event("e1", LifecycleState.DISCOVERED, LifecycleState.VERIFYING))
            self.assertEqual(entry.sequence, 1)
            self.assertEqual(runtime.get_state("k1").last_sequence, 1)

    def test_empty_restart_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = PersistentKnowledgeRuntime(Path(directory) / "knowledge.db")
            report = runtime.recover()
            self.assertEqual(report.status, "empty")


if __name__ == "__main__":
    unittest.main()
