"""Knowledge provenance and audit trail primitives for Sarembok."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass(frozen=True)
class ProvenanceEvent:
    event_id: str
    knowledge_id: str
    event_type: str
    actor_id: str
    reason: str
    timestamp: str
    evidence_refs: List[str]


class KnowledgeProvenanceLedger:
    """Append-only in-memory provenance ledger for knowledge lifecycle decisions."""

    def __init__(self):
        self._events: Dict[str, ProvenanceEvent] = {}

    def record(
        self,
        event_id: str,
        knowledge_id: str,
        event_type: str,
        actor_id: str,
        reason: str,
        evidence_refs: List[str] | None = None,
        timestamp: str | None = None,
    ) -> ProvenanceEvent:
        if event_id in self._events:
            raise RuntimeError(f"provenance_event_exists:{event_id}")
        if not knowledge_id or not event_type or not actor_id or not reason:
            raise ValueError("provenance_requires_identity_type_actor_and_reason")
        event = ProvenanceEvent(
            event_id=event_id,
            knowledge_id=knowledge_id,
            event_type=event_type,
            actor_id=actor_id,
            reason=reason,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            evidence_refs=list(evidence_refs or []),
        )
        self._events[event_id] = event
        return event

    def history(self, knowledge_id: str) -> List[ProvenanceEvent]:
        if not knowledge_id:
            raise ValueError("knowledge_id_required")
        return sorted(
            (event for event in self._events.values() if event.knowledge_id == knowledge_id),
            key=lambda event: (event.timestamp, event.event_id),
        )

    def explain(self, knowledge_id: str) -> Dict[str, object]:
        events = self.history(knowledge_id)
        return {
            "knowledge_id": knowledge_id,
            "event_count": len(events),
            "events": events,
            "latest_event": events[-1] if events else None,
        }
