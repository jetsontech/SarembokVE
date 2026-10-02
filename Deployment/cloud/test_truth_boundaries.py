"""Truth-boundary regression tests for runtime APIs."""
from __future__ import annotations

import os
import tempfile
import unittest

db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["SAREMBOK_DB_PATH"] = db_file.name

import Deployment.cloud.server as server


class TestTruthBoundaries(unittest.TestCase):
    def setUp(self):
        server.ensure_scheduler_schema()
        for table in ("tasks", "workers", "events", "agents", "checkpoints", "digital_human_sessions", "memories"):
            server.store.db.execute(f"DELETE FROM {table}")
        server.store.db.commit()

    def test_digital_human_requires_real_worker(self):
        agent_id = "truth-agent"
        server.store.create_agent(agent_id, "Truth Test Agent")
        result = server.dispatch("CreateDigitalHumanSession", {"agentId": agent_id})
        self.assertEqual(result["status"], "PENDING_WORKER")
        self.assertIsNone(result["assignedWorkerId"])

    def test_audit_trail_runs_sqlite_integrity_check(self):
        agent_id = "audit-agent"
        server.store.create_agent(agent_id, "Audit Test Agent")
        result = server.dispatch("GetAuditTrail", {"agentId": agent_id})
        self.assertTrue(result["verified"])
        self.assertEqual(str(result["integrityCheck"]).lower(), "ok")
        self.assertEqual(result["status"], "integrity_verified")

    def test_checkpoint_restore_does_not_claim_replay(self):
        created = server.dispatch("CreateCheckpoint", {
            "label": "truth-test",
            "payload": {"marker": "test"},
        })
        self.assertEqual(created["status"], "CREATED")
        self.assertFalse(created["verified"])

        restored = server.dispatch("RestoreCheckpoint", {
            "checkpointId": created["checkpointId"],
        })
        self.assertEqual(restored["status"], "UNAVAILABLE")
        self.assertFalse(restored["restored"])

    def test_memory_graph_sync_does_not_claim_unimplemented_index(self):
        result = server.dispatch("ExecuteSystemAction", {"action": "sync_memory_graph"})
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertFalse(result["verified"])

    def test_cognitive_scorecard_has_no_synthetic_scores(self):
        agent_id = "score-agent"
        server.store.create_agent(agent_id, "Score Test Agent")
        result = server.dispatch("GetCognitiveScorecard", {"agentId": agent_id})
        self.assertEqual(result["status"], "MEASURED")
        self.assertIsNone(result["overallReliability"])
        self.assertIn("perception", result["unmeasuredDimensions"])

    def test_vision_capabilities_match_yunet_evidence(self):
        result = server.dispatch("GetVisionStatus", {})
        self.assertNotIn("Motion Analysis", result["capabilities"])
        self.assertNotIn("Gaze Tracking", result["capabilities"])
        self.assertIn("Face Detection", result["capabilities"])
        self.assertIn("Face-Center Gaze Proxy", result["capabilities"])


if __name__ == "__main__":
    unittest.main()
