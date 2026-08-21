"""Provider-neutral runtime bridge contract for Sarembok -> Unreal/MetaHuman.

The bridge translates avatar commands into transport-neutral messages. The
actual Unreal WebSocket/IPC implementation remains a replaceable adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Protocol
import json

from sarembok_avatar import AvatarCommand


@dataclass(frozen=True)
class UnrealAvatarMessage:
    message_type: str
    command_id: str
    session_id: str
    signal: str
    expression: str | None = None
    expression_intensity: float | None = None
    animation_ref: str | None = None
    viseme_ref: str | None = None
    speech_stream_ref: str | None = None
    gaze_target: Dict[str, float] | None = None

    def to_json(self) -> str:
        return json.dumps({k: v for k, v in asdict(self).items() if v is not None}, separators=(",", ":"))


class UnrealTransport(Protocol):
    def send(self, message: str) -> Dict[str, Any]: ...


class SarembokUnrealAvatarBridge:
    """Translate Sarembok avatar state into Unreal-facing messages."""

    def __init__(self, transport: UnrealTransport):
        self.transport = transport

    def apply(self, command: AvatarCommand) -> Dict[str, Any]:
        expression = command.state.expression
        message = UnrealAvatarMessage(
            message_type="sarembok.avatar.state",
            command_id=command.command_id,
            session_id=command.state.session_id,
            signal=command.state.signal.value,
            expression=expression.name if expression else None,
            expression_intensity=expression.intensity if expression else None,
            animation_ref=command.animation_ref,
            viseme_ref=command.viseme_ref,
            speech_stream_ref=command.state.speech_stream_ref,
            gaze_target=command.state.gaze_target,
        )
        return self.transport.send(message.to_json())
