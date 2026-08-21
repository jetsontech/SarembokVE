"""Checkpoint selection and recovery reporting for knowledge state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from sarembok_knowledge_event_log import EventLogEntry
from sarembok_knowledge_state_reducer import KnowledgeStateReducer
from sarembok_knowledge_state_snapshot import KnowledgeStateSnapshot, KnowledgeStateSnapshotManager


@dataclass(frozen=True)
class RecoveryReport:
    status: str
    checkpoint_sequence: int
    replayed_events: int
    final_sequence: int
    reason: str


class KnowledgeRecoveryManager:
    """Selects a valid checkpoint and reconstructs state from its event delta."""

    def __init__(self, snapshots: KnowledgeStateSnapshotManager | None = None):
        self.snapshots = snapshots or KnowledgeStateSnapshotManager()

    def recover(
        self,
        checkpoints: Iterable[KnowledgeStateSnapshot],
        events: Iterable[EventLogEntry],
        target_sequence: int | None = None,
    ) -> tuple[KnowledgeStateReducer, RecoveryReport]:
        checkpoints = list(checkpoints)
        events = sorted(list(events), key=lambda entry: entry.sequence)
        if target_sequence is not None and target_sequence < 0:
            raise ValueError("target_sequence_must_not_be_negative")

        valid: List[KnowledgeStateSnapshot] = []
        for checkpoint in checkpoints:
            try:
                self.snapshots.restore(checkpoint)
            except ValueError:
                continue
            if target_sequence is None or checkpoint.last_sequence <= target_sequence:
                valid.append(checkpoint)

        if valid:
            checkpoint = max(valid, key=lambda item: item.last_sequence)
            end = target_sequence if target_sequence is not None else (events[-1].sequence if events else checkpoint.last_sequence)
            delta = [entry for entry in events if checkpoint.last_sequence < entry.sequence <= end]
            reducer = self.snapshots.restore_and_replay(checkpoint, delta)
            return reducer, RecoveryReport(
                "recovered", checkpoint.last_sequence, len(delta),
                checkpoint.last_sequence + len(delta),
                "latest_valid_checkpoint_replayed",
            )

        if not events:
            return KnowledgeStateReducer(), RecoveryReport("empty", 0, 0, 0, "no_checkpoint_or_events")

        reducer = KnowledgeStateReducer()
        expected = 1
        for entry in events:
            if entry.sequence != expected:
                raise ValueError("event_log_gap_during_full_recovery")
            reducer.apply(entry.event, entry.sequence)
            expected += 1
        final_sequence = expected - 1
        if target_sequence is not None and final_sequence < target_sequence:
            raise ValueError("event_log_ends_before_target_sequence")
        return reducer, RecoveryReport("full_replay", 0, final_sequence, final_sequence, "no_valid_checkpoint")
