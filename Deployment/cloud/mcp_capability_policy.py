"""Sarembok external MCP capability policy and risk gate.

MCP tool metadata is untrusted input. This module keeps external capabilities
behind a deterministic policy boundary before SkillsEngine can execute them.
Read-only operations are allowed by default; mutating or unclassified
operations require explicit approval in the execution context.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("sarembok.mcp_policy")

# Conservative vocabulary. Tool annotations are preferred when supplied, but
# names/descriptions remain useful for older MCP servers that omit annotations.
_MUTATING_RE = re.compile(
    r"(?:^|[_:\-])(delete|remove|destroy|drop|write|edit|update|create|insert|upsert|merge|push|commit|deploy|upload|move|rename|install|configure|set|execute|exec|run|shell|command|send|publish|grant|revoke)(?:$|[_:\-])",
    re.IGNORECASE,
)
_READ_RE = re.compile(
    r"(?:^|[_:\-])(get|list|search|find|fetch|read|query|status|health|info|inspect|describe|view|show|lookup|history|check|discover)(?:$|[_:\-])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class McpPolicyDecision:
    allowed: bool
    risk: str
    reason: str
    audit_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk": self.risk,
            "reason": self.reason,
            "auditId": self.audit_id,
        }


def _annotation_value(tool: dict[str, Any], key: str) -> Any:
    annotations = tool.get("annotations") or tool.get("_meta", {}).get("annotations") or {}
    if isinstance(annotations, dict):
        return annotations.get(key)
    return None


def classify_tool(tool: dict[str, Any]) -> str:
    """Classify an MCP tool as read, write, or unknown using MCP hints first."""
    read_only = _annotation_value(tool, "readOnlyHint")
    destructive = _annotation_value(tool, "destructiveHint")
    if read_only is True and destructive is not True:
        return "read"
    if destructive is True or read_only is False:
        return "write"

    name = str(tool.get("name", ""))
    description = str(tool.get("description", ""))
    combined = f"{name} {description}"
    if _MUTATING_RE.search(combined):
        return "write"
    if _READ_RE.search(name):
        return "read"
    return "unknown"


class McpCapabilityPolicy:
    """Deterministic policy gate for calls to external MCP capabilities."""

    def __init__(self, *, allow_unclassified: bool = False) -> None:
        self.allow_unclassified = allow_unclassified

    def authorize(
        self,
        server_name: str,
        tool: dict[str, Any],
        arguments: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> McpPolicyDecision:
        context = context or {}
        arguments = arguments or {}
        risk = classify_tool(tool)
        audit_id = uuid.uuid4().hex

        # Explicit approval is deliberately scoped to the current invocation.
        approved = context.get("mcp_approval") == "approved"
        caller = str(context.get("caller", "unknown"))[:128]

        if risk == "read":
            allowed = True
            reason = "Read-only MCP capability allowed by default."
        elif risk == "write":
            allowed = approved
            reason = (
                "Mutating MCP capability explicitly approved for this invocation."
                if approved
                else "Mutating MCP capability requires explicit mcp_approval=approved."
            )
        else:
            allowed = approved or self.allow_unclassified
            reason = (
                "Unclassified MCP capability explicitly approved for this invocation."
                if approved
                else "Unclassified MCP capability is denied by default."
            )

        event = {
            "event": "mcp_capability_decision",
            "auditId": audit_id,
            "timestamp": time.time(),
            "server": server_name,
            "tool": tool.get("name", ""),
            "risk": risk,
            "allowed": allowed,
            "caller": caller,
            "argumentKeys": sorted(str(k) for k in arguments.keys()),
            "reason": reason,
        }
        logger.info("%s", json.dumps(event, separators=(",", ":"), sort_keys=True))
        return McpPolicyDecision(allowed=allowed, risk=risk, reason=reason, audit_id=audit_id)


_GLOBAL_POLICY = McpCapabilityPolicy()


def get_mcp_capability_policy() -> McpCapabilityPolicy:
    return _GLOBAL_POLICY
