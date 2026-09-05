"""Focused tests for the runtime truth boundary."""
from __future__ import annotations

import json
import sqlite3
import time

from runtime_authority import snapshot


class FakeProvider:
    def configured(self):
        return []

    def metrics(self):
        return {"configuredProviders": [], "samples": 0, "successes": 0, "failures": 0, "cooldowns": {}, "recent": []}


class Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE workers (
                worker_id TEXT PRIMARY KEY,
                capabilities TEXT NOT NULL,
                gpu_vendor TEXT,
                gpu_model TEXT,
                vram_mb INTEGER,
                cuda_version TEXT,
                available_memory_mb INTEGER,
                supported_models TEXT,
                latency_ms REAL,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL
            );
            CREATE TABLE agents (agent_id TEXT PRIMARY KEY, display_name TEXT, status TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE memories (memory_id TEXT PRIMARY KEY, tier TEXT, key TEXT, value TEXT, agent_id TEXT, created_at TEXT);
            CREATE TABLE tasks (task_id TEXT PRIMARY KEY, task_type TEXT, required_capability TEXT, payload TEXT, assigned_worker_id TEXT, status TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, event_type TEXT, payload TEXT, created_at TEXT);
            CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, created_at TEXT);
            """
        )
        stamp = "2026-09-04T18:00:00+00:00"
        self.db.execute(
            "INSERT INTO workers VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("w1", json.dumps(["compute", "inference"]), "NVIDIA", "RTX 4090", 24576, "12.2", 20000, json.dumps(["model-a"]), 12.0, "ONLINE", stamp),
        )
        self.db.execute(
            "INSERT INTO agents VALUES (?,?,?,?,?)",
            ("a1", "Test Agent", "REGISTERED", stamp, stamp),
        )
        self.db.execute(
            "INSERT INTO memories VALUES (?,?,?,?,?,?)",
            ("m1", "SEMANTIC", "k", "v", "a1", stamp),
        )
        self.db.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)",
            ("t1", "compute", "compute", "{}", "w1", "QUEUED", stamp, stamp),
        )
        self.db.commit()


def main() -> None:
    store = Store()
    data = snapshot(store, FakeProvider(), time.time())
    assert data["type"] == "system_diagnostic"
    assert data["workers"]["registered"] == 1
    assert data["workers"]["online"] == 1
    assert data["compute"]["onlineGpuWorkers"] == 1
    assert data["memory"]["entries"] == 1
    assert data["scheduler"]["queueDepth"] == 1
    assert data["agents"]["registered"] == 1
    assert data["agents"]["online"] == 0
    print("runtime_authority: PASS")


if __name__ == "__main__":
    main()
