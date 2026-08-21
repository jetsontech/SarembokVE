"""Provider-neutral GUI/application control contract for Sarembok.

This layer describes GUI observations and explicitly requested interactions.
Platform-specific automation (Windows UI Automation, macOS Accessibility,
Android/iOS accessibility, Unreal UI, etc.) belongs in adapters implementing
this contract. No OS automation is executed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class UIActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    OPEN = "open"
    CLOSE = "close"


@dataclass(frozen=True)
class UIElement:
    element_id: str
    role: str
    name: str = ""
    bounds: Optional[Dict[str, float]] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UIObservation:
    application: str
    window_title: str
    elements: List[UIElement] = field(default_factory=list)
    screenshot_ref: Optional[str] = None


@dataclass(frozen=True)
class UIAction:
    action_type: UIActionType
    target_id: Optional[str] = None
    value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GUIControlPolicy:
    allow_click: bool = False
    allow_type: bool = False
    allow_key: bool = False
    allow_scroll: bool = False
    allow_open: bool = False
    allow_close: bool = False


class GUIAutomationBackend(Protocol):
    """Platform adapter implemented by Windows/macOS/mobile/etc."""

    def observe(self) -> UIObservation: ...

    def execute(self, action: UIAction) -> Dict[str, Any]: ...


class SarembokGUIController:
    """Policy gate between Sarembok agents and GUI automation backends."""

    def __init__(self, backend: GUIAutomationBackend, policy: Optional[GUIControlPolicy] = None):
        self.backend = backend
        self.policy = policy or GUIControlPolicy()

    def observe(self) -> UIObservation:
        return self.backend.observe()

    def execute(self, action: UIAction) -> Dict[str, Any]:
        self._authorize(action)
        return self.backend.execute(action)

    def _authorize(self, action: UIAction) -> None:
        allowed = {
            UIActionType.CLICK: self.policy.allow_click,
            UIActionType.TYPE: self.policy.allow_type,
            UIActionType.KEY: self.policy.allow_key,
            UIActionType.SCROLL: self.policy.allow_scroll,
            UIActionType.OPEN: self.policy.allow_open,
            UIActionType.CLOSE: self.policy.allow_close,
        }[action.action_type]
        if not allowed:
            raise PermissionError(f"gui_action_not_permitted:{action.action_type.value}")
