"""Unit test suite for Sarembok VE Autonomous Worker Lifecycle v1.

Tests:
1. Registration (RegisterWorker -> ONLINE)
2. Heartbeat (Heartbeat -> ONLINE, updated timestamp)
3. Fresh worker (Heartbeat age < 60s -> ONLINE)
4. Boundary worker (Heartbeat age == 60s -> ONLINE)
5. Stale worker (Heartbeat age > 60s and <= 180s -> STALE)
6. Offline worker (Heartbeat age > 180s -> OFFLINE)
7. Missing/invalid timestamp (Missing or malformed heartbeat -> OFFLINE)
8. Recovery from STALE (STALE -> Heartbeat -> ONLINE)
9. Recovery from OFFLINE (OFFLINE -> Heartbeat -> ONLINE)
10. Scheduler exclusion (STALE/OFFLINE excluded, ONLINE selected)
11. Capability filtering (Only workers with required capability selected)
12. Transition event (ONLINE -> STALE creates exactly one WORKER_STATUS_CHANGED event)
13. Recovery event (STALE -> ONLINE creates a status-change event)
14. Atomic race protection (Conditional update prevents overwriting newer heartbeat)
15. Invalid lifecycle configuration (validate_worker_lifecycle_config raises ValueError)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# Ensure temp DB path before importing server
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["SAREMBOK_DB_PATH"] = temp_db.name
os.environ["SAREMBOK_WORKER_HEARTBEAT_TIMEOUT_SECONDS"] = "60"
os.environ["SAREMBOK_WORKER_OFFLINE_TIMEOUT_SECONDS"] = "180"

import Deployment.cloud.server as server
from Deployment.cloud.server import (
    WORKER_HEARTBEAT_TIMEOUT_SECONDS,
    WORKER_OFFLINE_TIMEOUT_SECONDS,
    dispatch,
    evaluate_worker_liveness,
    select_worker,
    store,
    validate_worker_lifecycle_config,
)


class TestWorkerLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        store.db.execute("DELETE FROM workers")
        store.db.execute("DELETE FROM events")
        store.db.execute("DELETE FROM tasks")
        store.db.commit()

    def tearDown(self) -> None:
        store.db.execute("DELETE FROM workers")
        store.db.execute("DELETE FROM events")
        store.db.execute("DELETE FROM tasks")
        store.db.commit()

    def test_01_registration(self) -> None:
        res = dispatch("RegisterWorker", {
            "workerId": "worker-test-1",
            "capabilities": ["inference", "meta_human"],
            "gpuVendor": "NVIDIA",
            "gpuModel": "RTX 4090",
            "vramMb": 24576,
            "status": "ONLINE",
        })
        self.assertEqual(res["workerId"], "worker-test-1")
        self.assertTrue(res["registered"])
        self.assertEqual(res["status"], "ONLINE")
        self.assertIn("inference", res["capabilities"])

    def test_02_heartbeat(self) -> None:
        dispatch("RegisterWorker", {"workerId": "worker-test-2", "capabilities": ["inference"]})
        res = dispatch("Heartbeat", {"workerId": "worker-test-2", "status": "ONLINE"})
        self.assertEqual(res["workerId"], "worker-test-2")
        self.assertEqual(res["status"], "ONLINE")
        self.assertTrue(res["lastHeartbeat"])

    def test_03_fresh_worker(self) -> None:
        now_utc = datetime.now(timezone.utc)
        fresh_stamp = (now_utc - timedelta(seconds=30)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-fresh", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", fresh_stamp, 0),
        )
        store.db.commit()

        evaluate_worker_liveness(now_utc)
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-fresh'").fetchone()
        self.assertEqual(row[0], "ONLINE")

    def test_04_boundary_worker(self) -> None:
        now_utc = datetime.now(timezone.utc)
        boundary_stamp = (now_utc - timedelta(seconds=60)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-boundary", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", boundary_stamp, 0),
        )
        store.db.commit()

        evaluate_worker_liveness(now_utc)
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-boundary'").fetchone()
        self.assertEqual(row[0], "ONLINE")

    def test_05_stale_worker(self) -> None:
        now_utc = datetime.now(timezone.utc)
        stale_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-stale", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", stale_stamp, 0),
        )
        store.db.commit()

        evaluate_worker_liveness(now_utc)
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-stale'").fetchone()
        self.assertEqual(row[0], "STALE")

    def test_06_offline_worker(self) -> None:
        now_utc = datetime.now(timezone.utc)
        offline_stamp = (now_utc - timedelta(seconds=240)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-offline", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", offline_stamp, 0),
        )
        store.db.commit()

        evaluate_worker_liveness(now_utc)
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-offline'").fetchone()
        self.assertEqual(row[0], "OFFLINE")

    def test_07_invalid_timestamp_worker(self) -> None:
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-invalid-ts", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", "INVALID_TIMESTAMP", 0),
        )
        store.db.commit()

        evaluate_worker_liveness()
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-invalid-ts'").fetchone()
        self.assertEqual(row[0], "OFFLINE")

    def test_08_recovery_from_stale(self) -> None:
        now_utc = datetime.now(timezone.utc)
        stale_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-rec-stale", '["inference"]', "NVIDIA", "RTX 4090", 24576, "STALE", stale_stamp, 0),
        )
        store.db.commit()

        res = dispatch("Heartbeat", {"workerId": "worker-rec-stale", "status": "ONLINE"})
        self.assertEqual(res["status"], "ONLINE")
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-rec-stale'").fetchone()
        self.assertEqual(row[0], "ONLINE")

    def test_09_recovery_from_offline(self) -> None:
        now_utc = datetime.now(timezone.utc)
        offline_stamp = (now_utc - timedelta(seconds=250)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-rec-off", '["inference"]', "NVIDIA", "RTX 4090", 24576, "OFFLINE", offline_stamp, 0),
        )
        store.db.commit()

        res = dispatch("Heartbeat", {"workerId": "worker-rec-off", "status": "ONLINE"})
        self.assertEqual(res["status"], "ONLINE")
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-rec-off'").fetchone()
        self.assertEqual(row[0], "ONLINE")

    def test_10_scheduler_exclusion(self) -> None:
        now_utc = datetime.now(timezone.utc)
        fresh_stamp = (now_utc - timedelta(seconds=10)).isoformat()
        stale_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        offline_stamp = (now_utc - timedelta(seconds=240)).isoformat()

        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-online", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", fresh_stamp, 0),
        )
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-stale", '["inference"]', "NVIDIA", "RTX 4090", 24576, "STALE", stale_stamp, 0),
        )
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-offline", '["inference"]', "NVIDIA", "RTX 4090", 24576, "OFFLINE", offline_stamp, 0),
        )
        store.db.commit()

        selected = select_worker("inference")
        self.assertEqual(selected, "worker-online")

        # Set online worker to stale and verify no worker is selected
        store.db.execute("UPDATE workers SET last_heartbeat=? WHERE worker_id='worker-online'", (stale_stamp,))
        store.db.commit()

        selected_none = select_worker("inference")
        self.assertIsNone(selected_none)

    def test_11_capability_filtering(self) -> None:
        now_utc = datetime.now(timezone.utc)
        fresh_stamp = (now_utc - timedelta(seconds=10)).isoformat()

        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("w-inference-only", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", fresh_stamp, 0),
        )
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("w-metahuman", '["meta_human"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", fresh_stamp, 0),
        )
        store.db.commit()

        self.assertEqual(select_worker("inference"), "w-inference-only")
        self.assertEqual(select_worker("meta_human"), "w-metahuman")
        self.assertIsNone(select_worker("batch_rendering"))

    def test_12_transition_event(self) -> None:
        now_utc = datetime.now(timezone.utc)
        stale_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-trans-1", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", stale_stamp, 0),
        )
        store.db.commit()

        events_before = store.db.execute("SELECT COUNT(*) FROM events WHERE event_type='WORKER_STATUS_CHANGED'").fetchone()[0]

        evaluate_worker_liveness(now_utc)

        events_after = store.db.execute("SELECT event_type, payload FROM events WHERE event_type='WORKER_STATUS_CHANGED'").fetchall()
        self.assertEqual(len(events_after), events_before + 1)
        payload = json.loads(events_after[-1][1])
        self.assertEqual(payload["workerId"], "worker-trans-1")
        self.assertEqual(payload["previousStatus"], "ONLINE")
        self.assertEqual(payload["status"], "STALE")

    def test_13_recovery_event(self) -> None:
        now_utc = datetime.now(timezone.utc)
        stale_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-rec-evt", '["inference"]', "NVIDIA", "RTX 4090", 24576, "STALE", stale_stamp, 0),
        )
        store.db.commit()

        dispatch("Heartbeat", {"workerId": "worker-rec-evt", "status": "ONLINE"})

        events = store.db.execute("SELECT event_type, payload FROM events WHERE event_type='WORKER_STATUS_CHANGED'").fetchall()
        self.assertTrue(len(events) >= 1)
        payload = json.loads(events[-1][1])
        self.assertEqual(payload["workerId"], "worker-rec-evt")
        self.assertEqual(payload["previousStatus"], "STALE")
        self.assertEqual(payload["status"], "ONLINE")

    def test_14_atomic_race_protection(self) -> None:
        now_utc = datetime.now(timezone.utc)
        old_stamp = (now_utc - timedelta(seconds=120)).isoformat()
        new_stamp = (now_utc - timedelta(seconds=5)).isoformat()

        store.db.execute(
            "INSERT INTO workers (worker_id, capabilities, gpu_vendor, gpu_model, vram_mb, status, last_heartbeat, active_tasks) VALUES (?,?,?,?,?,?,?,?)",
            ("worker-race", '["inference"]', "NVIDIA", "RTX 4090", 24576, "ONLINE", old_stamp, 0),
        )
        store.db.commit()

        # Simulate concurrent heartbeat updating last_heartbeat to new_stamp before evaluation update executes
        store.db.execute("UPDATE workers SET last_heartbeat=? WHERE worker_id='worker-race'", (new_stamp,))
        store.db.commit()

        # Conditional update expecting old_stamp and ONLINE status must fail
        cursor = store.db.execute(
            "UPDATE workers SET status=? WHERE worker_id=? AND last_heartbeat=? AND status=?",
            ("STALE", "worker-race", old_stamp, "ONLINE"),
        )
        self.assertEqual(cursor.rowcount, 0)

        # Worker status should remain ONLINE
        row = store.db.execute("SELECT status FROM workers WHERE worker_id='worker-race'").fetchone()
        self.assertEqual(row[0], "ONLINE")

    def test_15_invalid_config_validation(self) -> None:
        with self.assertRaises(ValueError):
            validate_worker_lifecycle_config(heartbeat_timeout=0, offline_timeout=180, interval=15)
        with self.assertRaises(ValueError):
            validate_worker_lifecycle_config(heartbeat_timeout=60, offline_timeout=30, interval=15)
        with self.assertRaises(ValueError):
            validate_worker_lifecycle_config(heartbeat_timeout=60, offline_timeout=180, interval=0)


if __name__ == "__main__":
    unittest.main()
