"""Conflict-resolution provenance records for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass(frozen=True)
class ConflictProvenance:
    event_id: str
    claim_key: str
    conflicting_knowledge_ids: List[str]
    resolution: str
    selected_knowledge_id: str | None
    actor_id: str
    reason: str
    timestamp: str


class ConflictProvenanceLedger:
    """Append-only audit ledger for knowledge conflict decisions."""

    def __init__(self):
        self._events: Dict[str, ConflictProvenance] = {}

    def record(
        self,
        event_id: str,
        claim_key: str,
        conflicting_knowledge_ids: List[str],
        resolution: str,
        selected_knowledge_id: str | None,
        actor_id: str,
        reason: str,
        timestamp: str | None = None,
    ) -> ConflictProvenance:
        if event_id in self._events:
            raise RuntimeError(f"conflict_event_exists:{event_id}")
        if not event_id or not claim_key or not actor_id or not reason:
            raise ValueError("conflict_provenance_requires_identity_key_actor_and_reason")
        if len(conflicting_knowledge_ids) < 2 or any(not item for item in conflicting_knowledge_ids):
            raise ValueError("at_least_two_knowledge_ids_required")
        if resolution not in ("prefer_supported", "escalate", "consistent"):
            raise ValueError("invalid_conflict_resolution")
        if resolution == "escalate" and selected_knowledge_id is not None:
            raise ValueError("escalated_conflict_cannot_select_knowledge")
        if selected_knowledge_id is not None and selected_knowledge_id not in conflicting_knowledge_ids:
            raise ValueError("selected_knowledge_must_be_in_conflict")

        event = ConflictProvenance(
            event_id,
            claim_key,
            list(conflicting_knowledge_ids),
            resolution,
            selected_knowledge_id,
            actor_id,
            reason,
            timestamp or datetime.now(timezone.utc).isoformat(),
        )
        self._events[event_id] = event
        return event

    def history(self, claim_key: str) -> List[ConflictProvenance]:
        if not claim_key:
            raise ValueError("claim_key_required")
        return sorted(
            (event for event in self._events.values() if event.claim_key == claim_key),
            key=lambda event: (event.timestamp, event.event_id),
        )
