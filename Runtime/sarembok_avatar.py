"""Sarembok avatar embodiment contract.

The avatar is an embodiment of Sarembok intelligence, not the intelligence
itself. MetaHuman/Unreal, mobile, web, and future Sarembok OS renderers can
implement the same provider-neutral state contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class AvatarSignal(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ATTENTION = "attention"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class AvatarExpression:
    name: str
    intensity: float = 1.0
    duration_ms: Optional[int] = None


@dataclass(frozen=True)
class AvatarState:
    session_id: str
    signal: AvatarSignal = AvatarSignal.IDLE
    expression: Optional[AvatarExpression] = None
    gaze_target: Optional[Dict[str, float]] = None
    speech_stream_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AvatarCommand:
    command_id: str
    state: AvatarState
    animation_ref: Optional[str] = None
    viseme_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AvatarRenderer(Protocol):
    def apply(self, command: AvatarCommand) -> Dict[str, Any]: ...


class AvatarController:
    """Converts Sarembok interaction state into renderer-neutral commands."""

    def __init__(self, renderer: AvatarRenderer):
        self.renderer = renderer

    def set_state(
        self,
        session_id: str,
        signal: AvatarSignal,
        *,
        expression: Optional[AvatarExpression] = None,
        gaze_target: Optional[Dict[str, float]] = None,
        speech_stream_ref: Optional[str] = None,
        animation_ref: Optional[str] = None,
        viseme_ref: Optional[str] = None,
        command_id: str = "avatar-command",
    ) -> Dict[str, Any]:
        state = AvatarState(
            session_id=session_id,
            signal=signal,
            expression=expression,
            gaze_target=gaze_target,
            speech_stream_ref=speech_stream_ref,
        )
        return self.renderer.apply(
            AvatarCommand(
                command_id=command_id,
                state=state,
                animation_ref=animation_ref,
                viseme_ref=viseme_ref,
            )
        )
