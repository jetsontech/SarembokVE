"""Unified perception bridge for Sarembok.

Normalizes computer-vision and GUI observations into one provider-neutral
perception stream. This module does not execute UI actions and does not store
raw camera/screenshot data; callers may provide references to protected data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class PerceptionKind(str, Enum):
    OBJECT = "object"
    TEXT = "text"
    FACE = "face"
    SCENE = "scene"
    UI = "ui"
    USER_INTERACTION = "user_interaction"


@dataclass(frozen=True)
class PerceptionEvent:
    kind: PerceptionKind
    source: str
    confidence: Optional[float] = None
    label: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    source_ref: Optional[str] = None


class SarembokPerceptionBridge:
    """Convert heterogeneous observations into agent-consumable events."""

    def __init__(self) -> None:
        self._events: List[PerceptionEvent] = []

    def ingest_vision_events(self, events: Iterable[Dict[str, Any]]) -> List[PerceptionEvent]:
        normalized = []
        for item in events:
            event = PerceptionEvent(
                kind=PerceptionKind(item.get("kind", PerceptionKind.SCENE.value)),
                source=str(item.get("source", "vision")),
                confidence=item.get("confidence"),
                label=item.get("label"),
                data=dict(item.get("data", {})),
                source_ref=item.get("source_ref"),
            )
            normalized.append(event)
        self._events.extend(normalized)
        return normalized

    def ingest_ui_observation(self, observation: Any) -> List[PerceptionEvent]:
        events = [
            PerceptionEvent(
                kind=PerceptionKind.UI,
                source="gui",
                label=getattr(observation, "window_title", ""),
                data={
                    "application": getattr(observation, "application", ""),
                    "elements": [self._element_dict(e) for e in getattr(observation, "elements", [])],
                },
                source_ref=getattr(observation, "screenshot_ref", None),
            )
        ]
        self._events.extend(events)
        return events

    def snapshot(self) -> List[PerceptionEvent]:
        return list(self._events)

    @staticmethod
    def _element_dict(element: Any) -> Dict[str, Any]:
        return {
            "element_id": getattr(element, "element_id", ""),
            "role": getattr(element, "role", ""),
            "name": getattr(element, "name", ""),
            "bounds": getattr(element, "bounds", None),
            "enabled": getattr(element, "enabled", True),
            "metadata": dict(getattr(element, "metadata", {}) or {}),
        }
