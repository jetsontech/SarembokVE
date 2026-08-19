"""SQLite/WAL implementation of the knowledge persistence backend."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from sarembok_knowledge_event_bus import KnowledgeLifecycleEvent
from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_lifecycle import LifecycleState, LifecycleTransition
from sarembok_knowledge_persistence import KnowledgePersistenceBackend
from sarembok_knowledge_state_reducer import KnowledgeState
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshot


class SQLiteKnowledgePersistenceBackend:
    """Transactional SQLite backend using WAL mode and deterministic serialization."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_events (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    knowledge_id TEXT NOT NULL,
                    previous_state TEXT NOT NULL,
                    new_state TEXT NOT NULL,
                    reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_snapshots (
                    last_sequence INTEGER PRIMARY KEY,
                    payload TEXT NOT NULL,
                    digest TEXT NOT NULL
                );
                """
            )

    def append_event(self, entry: EventLogEntry) -> None:
        transition = entry.event.transition
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO knowledge_events
                   (sequence, event_id, knowledge_id, previous_state, new_state, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.sequence,
                    entry.event.event_id,
                    transition.knowledge_id,
                    transition.previous_state.value,
                    transition.new_state.value,
                    transition.reason,
                ),
            )

    def load_events(self, after_sequence: int = 0) -> Iterable[EventLogEntry]:
        if after_sequence < 0:
            raise ValueError("sequence_must_not_be_negative")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT sequence, event_id, knowledge_id, previous_state, new_state, reason
                   FROM knowledge_events WHERE sequence > ? ORDER BY sequence""",
                (after_sequence,),
            ).fetchall()
        return [
            EventLogEntry(
                sequence,
                KnowledgeLifecycleEvent(
                    event_id,
                    LifecycleTransition(
                        knowledge_id,
                        LifecycleState(previous_state),
                        LifecycleState(new_state),
                        reason,
                    ),
                ),
            )
            for sequence, event_id, knowledge_id, previous_state, new_state, reason in rows
        ]

    def save_snapshot(self, snapshot: KnowledgeStateSnapshot) -> None:
        payload = json.dumps(
            {key: asdict(value) for key, value in sorted(snapshot.states.items())},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO knowledge_snapshots
                   (last_sequence, payload, digest) VALUES (?, ?, ?)""",
                (snapshot.last_sequence, payload, snapshot.digest),
            )

    def load_snapshots(self) -> Iterable[KnowledgeStateSnapshot]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT last_sequence, payload, digest FROM knowledge_snapshots ORDER BY last_sequence"
            ).fetchall()
        snapshots = []
        for last_sequence, payload, digest in rows:
            raw_states = json.loads(payload)
            states = {
                key: KnowledgeState(
                    value["knowledge_id"],
                    LifecycleState(value["state"]),
                    value["last_event_id"],
                    value["last_sequence"],
                )
                for key, value in raw_states.items()
            }
            snapshots.append(KnowledgeStateSnapshot(last_sequence, states, digest))
        return snapshots


assert isinstance(SQLiteKnowledgePersistenceBackend(":memory:"), KnowledgePersistenceBackend)
