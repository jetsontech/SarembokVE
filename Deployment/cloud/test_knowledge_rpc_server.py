import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


class KnowledgeRPCBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "knowledge.db")
        os.environ["SAREMBOK_DB_PATH"] = cls.db_path
        cloud_dir = str(Path(__file__).resolve().parent)
        if cloud_dir not in sys.path:
            sys.path.insert(0, cloud_dir)
        cls.bridge = importlib.import_module("knowledge_rpc_server")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_knowledge_methods_are_exposed_through_cloud_dispatch(self):
        result = self.bridge.dispatch(
            "CreateKnowledge",
            {"knowledgeId": "rpc-k1", "title": "RPC Knowledge"},
        )
        self.assertEqual(result["knowledgeId"], "rpc-k1")
        self.assertEqual(result["state"], "discovered")

        transition = self.bridge.dispatch(
            "TransitionKnowledge",
            {"knowledgeId": "rpc-k1", "targetState": "verifying", "reason": "rpc test"},
        )
        self.assertEqual(transition["state"], "verifying")
        self.assertEqual(transition["sequence"], 1)
        self.assertTrue(transition["eventId"])

        current = self.bridge.dispatch("GetKnowledge", {"knowledgeId": "rpc-k1"})
        self.assertEqual(current["state"], "verifying")
        self.assertEqual(current["lastSequence"], 1)

    def test_existing_cloud_methods_still_use_original_dispatch(self):
        result = self.bridge.dispatch("RuntimeInfo", {})
        self.assertEqual(result["status"], "ONLINE")
        self.assertEqual(result["storage"], "sqlite-wal")

    def test_recovery_and_checkpoint_are_exposed(self):
        checkpoint = self.bridge.dispatch("CheckpointKnowledge", {})
        self.assertEqual(checkpoint["lastSequence"], 1)
        self.assertEqual(checkpoint["stateCount"], 1)

        recovery = self.bridge.dispatch("GetKnowledgeRecoveryStatus", {})
        self.assertIn(recovery["status"], {"recovered", "full_replay", "empty"})


if __name__ == "__main__":
    unittest.main()
