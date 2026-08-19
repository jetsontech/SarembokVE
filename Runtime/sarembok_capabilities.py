"""Policy-controlled capability boundary for Sarembok agents.

Capabilities are explicit operations. The runtime does not grant operating-system
or device access merely because an agent requests it; a caller must register a
capability and provide an execution policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


class CapabilityClass(str, Enum):
    OBSERVE = "observe"
    REASON = "reason"
    CREATE = "create"
    EXECUTE = "execute"
    COMMUNICATE = "communicate"
    REMEMBER = "remember"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CapabilityDescriptor:
    id: str
    version: str
    capability_class: CapabilityClass
    required_permissions: tuple[str, ...] = ()
    risk_level: RiskLevel = RiskLevel.LOW
    supports_dry_run: bool = False
    supports_rollback: bool = False
    provider: str = "sarembok"


@dataclass(frozen=True)
class CapabilityPolicy:
    allowed_capabilities: frozenset[str] = frozenset()
    approved_permissions: frozenset[str] = frozenset()
    allow_high_risk: bool = False
    allow_critical: bool = False

    def permits(self, descriptor: CapabilityDescriptor) -> bool:
        if descriptor.id not in self.allowed_capabilities:
            return False
        if not set(descriptor.required_permissions).issubset(self.approved_permissions):
            return False
        if descriptor.risk_level == RiskLevel.HIGH and not self.allow_high_risk:
            return False
        if descriptor.risk_level == RiskLevel.CRITICAL and not self.allow_critical:
            return False
        return True


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: Dict[str, tuple[CapabilityDescriptor, Callable[..., Any]]] = {}

    def register(
        self,
        descriptor: CapabilityDescriptor,
        handler: Callable[..., Any],
    ) -> None:
        if descriptor.id in self._capabilities:
            raise ValueError(f"Capability already registered: {descriptor.id}")
        self._capabilities[descriptor.id] = (descriptor, handler)

    def describe(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        item = self._capabilities.get(capability_id)
        return item[0] if item else None

    def invoke(
        self,
        capability_id: str,
        policy: CapabilityPolicy,
        **inputs: Any,
    ) -> Any:
        item = self._capabilities.get(capability_id)
        if item is None:
            raise KeyError(f"Unknown capability: {capability_id}")
        descriptor, handler = item
        if not policy.permits(descriptor):
            raise PermissionError(f"Capability denied by policy: {capability_id}")
        return handler(**inputs)
