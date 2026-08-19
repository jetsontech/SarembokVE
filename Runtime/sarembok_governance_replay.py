"""Deterministic replay and explainability for governance audit records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sarembok_governance_audit import GovernanceAuditRecord


@dataclass(frozen=True)
class ReplayResult:
    event_id: str
    original_state: str
    replayed_state: str
    matches: bool
    explanation: str


class GovernanceReplayEngine:
    """Replays recorded governance inputs and identifies decision drift."""

    def replay(
        self,
        record: GovernanceAuditRecord,
        decision_fn: Callable[..., str],
    ) -> ReplayResult:
        replayed_state = decision_fn(
            record.knowledge_id,
            record.confidence,
            record.verified,
            record.conflict_resolution,
            record.selected_knowledge_id,
        )
        matches = replayed_state == record.new_state
        explanation = (
            "replay_matches_recorded_decision"
            if matches
            else f"governance_drift:recorded={record.new_state};replayed={replayed_state}"
        )
        return ReplayResult(record.event_id, record.new_state, replayed_state, matches, explanation)

    @staticmethod
    def explain(record: GovernanceAuditRecord) -> str:
        conflict = record.conflict_resolution or "none"
        selected = record.selected_knowledge_id or "none"
        return (
            f"knowledge={record.knowledge_id};previous={record.previous_state};"
            f"new={record.new_state};confidence={record.confidence:.3f};"
            f"verified={record.verified};conflict={conflict};selected={selected};"
            f"actor={record.actor_id};reason={record.reason};timestamp={record.timestamp}"
        )
