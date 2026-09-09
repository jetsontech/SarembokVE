"""Authoritative Sarembok runtime capability registry.

This module is deliberately independent from the transport layer so capability
claims can be tested without starting the cloud gateway. Runtime code should
use this registry when describing what Sarembok can currently do.
"""

from __future__ import annotations

from typing import Any


SAREMBOK_CAPABILITIES: dict[str, dict[str, Any]] = {
    "memory": {
        "status": "implemented",
        "description": "Persist and retrieve Sarembok memory records.",
    },
    "agent_management": {
        "status": "implemented",
        "description": "Create and manage runtime agent records.",
    },
    "task_management": {
        "status": "implemented",
        "description": "Create and manage runtime tasks and their scheduler state.",
    },
    "agent_invocation": {
        "status": "implemented",
        "description": "Route supported agent requests through the configured language-model runtime.",
    },
    "health_monitoring": {
        "status": "implemented",
        "description": "Monitor runtime and registered worker health state.",
    },
    "conversation_context": {
        "status": "implemented",
        "description": "Persist conversation history for runtime sessions.",
    },
    "general_llm_reasoning": {
        "status": "implemented",
        "description": "Use configured language-model providers for general reasoning and generation.",
    },
    "live_research": {
        "status": "implemented",
        "description": "Perform live web/news retrieval and synthesize retrieved material when a research request is detected.",
    },
    "provider_fallback_routing": {
        "status": "implemented",
        "description": "Attempt configured providers in the runtime fallback order.",
    },
    "browser_sessions": {
        "status": "implemented",
        "description": "Issue short-lived browser sessions so the public browser does not receive the master runtime token.",
    },
    "email_delivery": {
        "status": "planned",
        "description": "Outbound email delivery is not currently an available Sarembok runtime capability.",
    },
    "slack_delivery": {
        "status": "planned",
        "description": "Slack messaging integration is not currently an available Sarembok runtime capability.",
    },
    "push_notifications": {
        "status": "planned",
        "description": "Push notification delivery is not currently an available Sarembok runtime capability.",
    },
    "automatic_self_upgrade": {
        "status": "planned",
        "description": "Autonomous production self-upgrade is not currently an available Sarembok runtime capability.",
    },
}


def get_capability(name: str) -> dict[str, Any] | None:
    """Return a copy of one capability declaration, if present."""
    capability = SAREMBOK_CAPABILITIES.get(name)
    return dict(capability) if capability is not None else None


def implemented_capabilities() -> dict[str, dict[str, Any]]:
    """Return only capabilities currently implemented by the runtime."""
    return {
        name: dict(value)
        for name, value in SAREMBOK_CAPABILITIES.items()
        if value.get("status") == "implemented"
    }


def planned_capabilities() -> dict[str, dict[str, Any]]:
    """Return capabilities explicitly planned but not currently available."""
    return {
        name: dict(value)
        for name, value in SAREMBOK_CAPABILITIES.items()
        if value.get("status") == "planned"
    }


def capability_authority_prompt() -> str:
    """Return the policy injected into LLM system context for capability claims."""
    return (
        "CAPABILITY AUTHORITY: The following registry is authoritative for "
        "claims about what Sarembok can currently do. Never claim an "
        "implemented capability unless its registry status is 'implemented'. "
        "Capabilities marked 'planned' are NOT available and must be described "
        "as planned or unavailable. Do not invent integrations, APIs, agents, "
        "workers, notifications, file operations, external services, or "
        "automation that are not represented by an implemented runtime "
        "capability. If the user asks what Sarembok can do, describe implemented "
        "capabilities first and distinguish planned capabilities explicitly."
    )


__all__ = [
    "SAREMBOK_CAPABILITIES",
    "get_capability",
    "implemented_capabilities",
    "planned_capabilities",
    "capability_authority_prompt",
]
