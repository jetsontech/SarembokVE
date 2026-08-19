"""Integrity-checked knowledge state snapshots with incremental replay metadata."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, Iterable

from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_state_reducer import KnowledgeState, KnowledgeStateReducer


@dataclass(frozen=True)
class KnowledgeStateSnapshot:
    last_sequence: int
    states: Dict[str, KnowledgeState]
    digest: str


class KnowledgeStateSnapshotManager:
    """Creates and restores deterministic state snapshots and replays only later events."""

    def create(self, reducer: KnowledgeStateReducer, last_sequence: int) -> KnowledgeStateSnapshot:
        if last_sequence < 0:
            raise ValueError("snapshot_sequence_must_not_be_negative")
        states = reducer.snapshot()
        digest = self._digest(last_sequence, states)
        return KnowledgeStateSnapshot(last_sequence, states, digest)

    def restore(self, snapshot: KnowledgeStateSnapshot) -> KnowledgeStateReducer:
        if snapshot.last_sequence < 0 or not snapshot.digest:
            raise ValueError("invalid_snapshot")
        if snapshot.digest != self._digest(snapshot.last_sequence, snapshot.states):
            raise ValueError("snapshot_integrity_check_failed")
        reducer = KnowledgeStateReducer()
        reducer._state = dict(snapshot.states)
        return reducer

    def restore_and_replay(
        self,
        snapshot: KnowledgeStateSnapshot,
        entries: Iterable[EventLogEntry],
    ) -> KnowledgeStateReducer:
        reducer = self.restore(snapshot)
        expected = snapshot.last_sequence + 1
        for entry in entries:
            if entry.sequence != expected:
                raise ValueError("incremental_replay_sequence_mismatch")
            reducer.apply(entry.event, entry.sequence)
            expected += 1
        return reducer

    @staticmethod
    def _digest(last_sequence: int, states: Dict[str, KnowledgeState]) -> str:
        canonical = {
            "last_sequence": last_sequence,
            "states": {
                key: asdict(value)
                for key, value in sorted(states.items())
            },
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(payload).hexdigest()
