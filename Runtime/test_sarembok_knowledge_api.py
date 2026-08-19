import tempfile
import unittest
from pathlib import Path

from sarembok_knowledge_api import KnowledgeRuntimeAPI
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime


class KnowledgeRuntimeAPITests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.runtime = PersistentKnowledgeRuntime(Path(self.tempdir.name) / "knowledge.db")
        self.api = KnowledgeRuntimeAPI(self.runtime)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_create_and_query_knowledge(self):
        created = self.api.dispatch("CreateKnowledge", {"knowledgeId": "k1", "title": "First fact"})
        self.assertEqual(created["state"], "discovered")
        item = self.api.dispatch("GetKnowledge", {"knowledgeId": "k1"})
        self.assertEqual(item["state"], "discovered")
        self.assertEqual(item["lastSequence"], 0)

    def test_transition_is_persisted_and_queryable(self):
        self.api.create_knowledge("k1", "First fact")
        result = self.api.transition_knowledge("k1", "verifying", "needs verification")
        self.assertEqual(result["sequence"], 1)
        self.assertEqual(self.api.get_knowledge("k1")["state"], "verifying")

        restarted = PersistentKnowledgeRuntime(self.runtime.backend.path)
        restarted_api = KnowledgeRuntimeAPI(restarted)
        self.assertEqual(restarted_api.get_knowledge("k1")["state"], "verifying")

    def test_invalid_transition_is_rejected(self):
        self.api.create_knowledge("k1", "First fact")
        with self.assertRaises(ValueError):
            self.api.transition_knowledge("k1", "trusted", "skip verification")

    def test_can_transition_reports_authority(self):
        self.api.create_knowledge("k1", "First fact")
        result = self.api.can_transition_knowledge("k1", "verifying")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["currentState"], "discovered")

    def test_recovery_and_checkpoint_are_exposed(self):
        self.api.create_knowledge("k1", "First fact")
        self.api.transition_knowledge("k1", "verifying", "verify")
        checkpoint = self.api.checkpoint()
        self.assertEqual(checkpoint["lastSequence"], 1)
        recovery = self.api.recover()
        self.assertIn(recovery["status"], {"recovered", "full_replay", "empty"})

    def test_unknown_method_fails_closed(self):
        with self.assertRaises(ValueError):
            self.api.dispatch("UnknownKnowledgeMethod", {})


if __name__ == "__main__":
    unittest.main()
