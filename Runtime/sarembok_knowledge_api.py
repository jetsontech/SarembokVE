"""Runtime API for creating, querying, transitioning, and recovering knowledge."""
from __future__ import annotations

import uuid
from typing import Any

from sarembok_knowledge_lifecycle import LifecycleState, KnowledgeLifecycleOrchestrator
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime


class KnowledgeRuntimeAPI:
    """Stable application-facing command/query surface over persistent knowledge runtime."""

    METHODS = frozenset({
        "CreateKnowledge",
        "GetKnowledge",
        "ListKnowledge",
        "TransitionKnowledge",
        "CanTransitionKnowledge",
        "CheckpointKnowledge",
        "RecoverKnowledge",
        "GetKnowledgeRecoveryStatus",
    })

    def __init__(self, runtime: PersistentKnowledgeRuntime):
        self.runtime = runtime
        self.lifecycle = KnowledgeLifecycleOrchestrator()

    def create_knowledge(self, knowledge_id: str, title: str, initial_state: str = "discovered") -> dict[str, Any]:
        return self.runtime.persistence.create_knowledge(knowledge_id, title, initial_state)

    def get_knowledge(self, knowledge_id: str) -> dict[str, Any]:
        entity = self.runtime.persistence.get_knowledge(knowledge_id)
        if entity is None:
            raise ValueError(f"knowledge_not_found:{knowledge_id}")
        state = self.runtime.get_state(knowledge_id)
        entity["state"] = state.state.value if state else entity["initialState"]
        if state:
            entity["lastEventId"] = state.last_event_id
            entity["lastSequence"] = state.last_sequence
        else:
            entity["lastEventId"] = None
            entity["lastSequence"] = 0
        return entity

    def list_knowledge(self) -> list[dict[str, Any]]:
        return [self.get_knowledge(item["knowledgeId"]) for item in self.runtime.persistence.list_knowledge()]

    def transition_knowledge(self, knowledge_id: str, target_state: str, reason: str) -> dict[str, Any]:
        entity = self.runtime.persistence.get_knowledge(knowledge_id)
        if entity is None:
            raise ValueError(f"knowledge_not_found:{knowledge_id}")
        current = self.runtime.get_state(knowledge_id)
        current_state = current.state if current else LifecycleState(entity["initialState"])
        try:
            target = LifecycleState(target_state)
        except ValueError as exc:
            raise ValueError(f"invalid_target_state:{target_state}") from exc
        transition = self.lifecycle.transition(knowledge_id, current_state, target, reason)
        event = self.runtime.publish(
            __import__("sarembok_knowledge_event_bus", fromlist=["KnowledgeLifecycleEvent"])
            .KnowledgeLifecycleEvent(f"evt_{uuid.uuid4().hex}", transition)
        )
        state = self.runtime.get_state(knowledge_id)
        return {
            "knowledgeId": knowledge_id,
            "state": state.state.value,
            "eventId": event.event_id,
            "sequence": event.sequence,
            "reason": reason,
        }

    def can_transition_knowledge(self, knowledge_id: str, target_state: str) -> dict[str, Any]:
        entity = self.runtime.persistence.get_knowledge(knowledge_id)
        if entity is None:
            raise ValueError(f"knowledge_not_found:{knowledge_id}")
        current = self.runtime.get_state(knowledge_id)
        current_state = current.state if current else LifecycleState(entity["initialState"])
        try:
            target = LifecycleState(target_state)
        except ValueError as exc:
            raise ValueError(f"invalid_target_state:{target_state}") from exc
        return {
            "knowledgeId": knowledge_id,
            "currentState": current_state.value,
            "targetState": target.value,
            "allowed": self.lifecycle.can_transition(current_state, target),
        }

    def checkpoint(self) -> dict[str, Any]:
        snapshot = self.runtime.checkpoint()
        return {"lastSequence": snapshot.last_sequence, "digest": snapshot.digest, "stateCount": len(snapshot.states)}

    def recover(self) -> dict[str, Any]:
        report = self.runtime.recover()
        return {
            "status": report.status,
            "checkpointSequence": report.checkpoint_sequence,
            "replayedEvents": report.replayed_events,
            "finalSequence": report.final_sequence,
            "reason": report.reason,
        }

    def recovery_status(self) -> dict[str, Any]:
        report = self.runtime.last_recovery_report
        if report is None:
            return self.recover()
        return {
            "status": report.status,
            "checkpointSequence": report.checkpoint_sequence,
            "replayedEvents": report.replayed_events,
            "finalSequence": report.final_sequence,
            "reason": report.reason,
        }

    def dispatch(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method not in self.METHODS:
            raise ValueError(f"unknown_knowledge_method:{method}")
        params = params or {}
        if method == "CreateKnowledge":
            return self.create_knowledge(str(params.get("knowledgeId", "")).strip(), str(params.get("title", "")).strip(), str(params.get("initialState", "discovered")))
        if method == "GetKnowledge":
            return self.get_knowledge(str(params.get("knowledgeId", "")))
        if method == "ListKnowledge":
            return {"items": self.list_knowledge()}
        if method == "TransitionKnowledge":
            return self.transition_knowledge(str(params.get("knowledgeId", "")), str(params.get("targetState", "")), str(params.get("reason", "")))
        if method == "CanTransitionKnowledge":
            return self.can_transition_knowledge(str(params.get("knowledgeId", "")), str(params.get("targetState", "")))
        if method == "CheckpointKnowledge":
            return self.checkpoint()
        if method == "RecoverKnowledge":
            return self.recover()
        return self.recovery_status()
