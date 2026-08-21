"""Sarembok multimodal interaction contract.

Combines text, voice, vision and UI observations into a single normalized
interaction envelope. Provider-specific speech/vision/model implementations
remain adapters outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Modality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    VISION = "vision"
    UI = "ui"


@dataclass(frozen=True)
class ModalityInput:
    modality: Modality
    content_ref: str
    transcript: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MultimodalInteraction:
    interaction_id: str
    user_id: str
    inputs: List[ModalityInput] = field(default_factory=list)
    context_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InteractionResponse:
    interaction_id: str
    text: Optional[str] = None
    speech_ref: Optional[str] = None
    avatar_state: Optional[Dict[str, Any]] = None
    action_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def modalities_present(interaction: MultimodalInteraction) -> set[Modality]:
    return {item.modality for item in interaction.inputs}


def build_response(
    interaction: MultimodalInteraction,
    *,
    text: Optional[str] = None,
    speech_ref: Optional[str] = None,
    avatar_state: Optional[Dict[str, Any]] = None,
    action_refs: Optional[List[str]] = None,
) -> InteractionResponse:
    return InteractionResponse(
        interaction_id=interaction.interaction_id,
        text=text,
        speech_ref=speech_ref,
        avatar_state=avatar_state,
        action_refs=action_refs or [],
    )
