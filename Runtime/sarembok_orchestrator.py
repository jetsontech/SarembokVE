"""Sarembok multimodal system orchestration boundary.

Coordinates perception, interaction, planning, execution and embodiment while
keeping provider-specific implementations behind explicit interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Protocol


class SystemPhase(str, Enum):
    OBSERVE = "observe"
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    RESPOND = "respond"


@dataclass(frozen=True)
class SystemEvent:
    event_type: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrchestrationContext:
    session_id: str
    user_id: str
    phase: SystemPhase = SystemPhase.OBSERVE
    event_refs: List[str] = field(default_factory=list)


class OrchestrationComponent(Protocol):
    def handle(self, context: OrchestrationContext, event: SystemEvent) -> List[SystemEvent]: ...


class SarembokSystemOrchestrator:
    """Provider-neutral control loop for the Sarembok system."""

    def __init__(self, components: Dict[SystemPhase, OrchestrationComponent]):
        self.components = components

    def process(self, context: OrchestrationContext, event: SystemEvent) -> List[SystemEvent]:
        phase = context.phase
        component = self.components.get(phase)
        if component is None:
            raise RuntimeError(f"orchestration_component_missing:{phase.value}")
        return component.handle(context, event)

    @staticmethod
    def advance(context: OrchestrationContext, phase: SystemPhase) -> OrchestrationContext:
        return OrchestrationContext(
            session_id=context.session_id,
            user_id=context.user_id,
            phase=phase,
            event_refs=list(context.event_refs),
        )
