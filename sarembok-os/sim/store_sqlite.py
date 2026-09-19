"""
Sarembok OS — SQLite-WAL persistence layer.
Replaces the flat-file WAL. Concurrent-safe, queryable, survives restart.
Same records the kernel replay expects.
"""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ns INTEGER NOT NULL,
    op TEXT NOT NULL,
    owner INTEGER,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_owner ON events(owner);
CREATE INDEX IF NOT EXISTS idx_events_op ON events(op);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    owner INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    tier TEXT NOT NULL,
    created_ns INTEGER NOT NULL,
    last_access_ns INTEGER NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_mem_owner ON memories(owner);
CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key);

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    capabilities TEXT NOT NULL,
    created_ns INTEGER NOT NULL,
    last_active_ns INTEGER NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, path: str = "sarembok.db"):
        self.path = path
        self._lock = threading.RLock()
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- event log (append-only) ----
    def append(self, record: dict) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "INSERT INTO events (ts_ns, op, owner, payload) VALUES (?, ?, ?, ?)",
                    (time.time_ns(), record.get("op", "?"), record.get("owner"), json.dumps(record)),
                )

    def replay_events(self) -> list:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    "SELECT payload FROM events ORDER BY seq ASC"
                )
                return [json.loads(row[0]) for row in cur.fetchall()]

    # ---- direct memory table (queryable) ----
    def upsert_memory(self, entry: dict) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """INSERT INTO memories (id, owner, key, value, tier, created_ns, last_access_ns, access_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                       last_access_ns=excluded.last_access_ns,
                       access_count=excluded.access_count""",
                    (entry["id"], entry["owner"], entry["key"], json.dumps(entry["value"]),
                     entry["tier"], entry["created_ns"], entry["last_access_ns"],
                     entry.get("access_count", 0)),
                )

    def delete_memory(self, mem_id: int) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute("DELETE FROM memories WHERE id=?", (mem_id,))

    def all_memories(self) -> list:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    "SELECT id, owner, key, value, tier, created_ns, "
                    "last_access_ns, access_count FROM memories"
                )
                rows = cur.fetchall()
                return [
                    {"id": r[0], "owner": r[1], "key": r[2], "value": json.loads(r[3]),
                     "tier": r[4], "created_ns": r[5], "last_access_ns": r[6], "access_count": r[7]}
                    for r in rows
                ]

    # ---- agents ----
    def upsert_agent(self, agent: dict) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """INSERT INTO agents (id, name, state, capabilities, created_ns, last_active_ns)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                       state=excluded.state,
                       last_active_ns=excluded.last_active_ns""",
                    (agent["id"], agent["name"], agent["state"],
                     json.dumps(agent.get("capabilities", {})),
                     agent["created_ns"], agent["last_active_ns"]),
                )

    def all_agents(self) -> list:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    "SELECT id, name, state, capabilities, created_ns, last_active_ns FROM agents"
                )
                rows = cur.fetchall()
                return [
                    {"id": r[0], "name": r[1], "state": r[2], "capabilities": json.loads(r[3]),
                     "created_ns": r[4], "last_active_ns": r[5]}
                    for r in rows
                ]

    def reset(self) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute("DELETE FROM events")
                conn.execute("DELETE FROM memories")
                conn.execute("DELETE FROM agents")

    def close(self) -> None:
        pass
