"""Append-only audit trail for unified knowledge governance decisions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass(frozen=True)
class GovernanceAuditRecord:
    event_id: str
    knowledge_id: str
    previous_state: str
    new_state: str
    confidence: float
    verified: bool
    conflict_resolution: str | None
    selected_knowledge_id: str | None
    actor_id: str
    reason: str
    timestamp: str


class GovernanceAuditLedger:
    """Append-only, duplicate-protected governance decision history."""

    def __init__(self):
        self._events: Dict[str, GovernanceAuditRecord] = {}

    def record(
        self,
        event_id: str,
        knowledge_id: str,
        previous_state: str,
        new_state: str,
        confidence: float,
        verified: bool,
        actor_id: str,
        reason: str,
        conflict_resolution: str | None = None,
        selected_knowledge_id: str | None = None,
        timestamp: str | None = None,
    ) -> GovernanceAuditRecord:
        if event_id in self._events:
            raise RuntimeError(f"audit_event_exists:{event_id}")
        if not event_id or not knowledge_id or not actor_id or not reason:
            raise ValueError("audit_identity_and_reason_required")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence_must_be_between_zero_and_one")
        if conflict_resolution not in (None, "prefer_supported", "escalate", "consistent"):
            raise ValueError("invalid_conflict_resolution")
        if conflict_resolution == "escalate" and selected_knowledge_id is not None:
            raise ValueError("escalated_audit_cannot_select_knowledge")
        if selected_knowledge_id is not None and conflict_resolution != "prefer_supported":
            raise ValueError("selected_knowledge_requires_preferred_resolution")

        record = GovernanceAuditRecord(
            event_id=event_id,
            knowledge_id=knowledge_id,
            previous_state=previous_state,
            new_state=new_state,
            confidence=confidence,
            verified=verified,
            conflict_resolution=conflict_resolution,
            selected_knowledge_id=selected_knowledge_id,
            actor_id=actor_id,
            reason=reason,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        )
        self._events[event_id] = record
        return record

    def history(self, knowledge_id: str) -> List[GovernanceAuditRecord]:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        return sorted(
            (event for event in self._events.values() if event.knowledge_id == knowledge_id),
            key=lambda event: (event.timestamp, event.event_id),
        )
