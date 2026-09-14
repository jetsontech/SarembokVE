"""Authoritative Sarembok runtime capability registry.

The registry is deliberately independent from transport code so capability
claims can be tested without starting the cloud gateway. Runtime code should
consult this registry before presenting a capability as available.
"""

from __future__ import annotations

from typing import Any


SAREMBOK_CAPABILITIES: dict[str, dict[str, Any]] = {
    "memory": {"status": "implemented", "description": "Persist and retrieve Sarembok memory records."},
    "agent_management": {"status": "implemented", "description": "Create and manage runtime agent records."},
    "task_management": {"status": "implemented", "description": "Create and manage runtime tasks and scheduler state."},
    "agent_invocation": {"status": "implemented", "description": "Route supported agent requests through the configured language-model runtime."},
    "health_monitoring": {"status": "implemented", "description": "Monitor runtime and registered worker health state."},
    "conversation_context": {"status": "implemented", "description": "Persist conversation history for runtime sessions."},
    "general_llm_reasoning": {"status": "implemented", "description": "Use configured language-model providers for reasoning and generation."},
    "live_research": {"status": "implemented", "description": "Perform live retrieval and synthesize retrieved material for research requests."},
    "provider_fallback_routing": {"status": "implemented", "description": "Attempt configured providers in runtime fallback order."},
    "browser_sessions": {"status": "implemented", "description": "Issue short-lived browser sessions instead of exposing the master runtime token."},
    "email_delivery": {"status": "planned", "description": "Outbound email delivery is not currently available."},
    "slack_delivery": {"status": "planned", "description": "Slack messaging integration is not currently available."},
    "push_notifications": {"status": "planned", "description": "Push notification delivery is not currently available."},
    "automatic_self_upgrade": {"status": "planned", "description": "Autonomous production self-upgrade is not currently available."},
}


def get_capability(name: str) -> dict[str, Any] | None:
    capability = SAREMBOK_CAPABILITIES.get(name)
    return dict(capability) if capability is not None else None


def implemented_capabilities() -> dict[str, dict[str, Any]]:
    return {name: dict(value) for name, value in SAREMBOK_CAPABILITIES.items() if value.get("status") == "implemented"}


def planned_capabilities() -> dict[str, dict[str, Any]]:
    return {name: dict(value) for name, value in SAREMBOK_CAPABILITIES.items() if value.get("status") == "planned"}


def capability_authority_prompt() -> str:
    return (
        "CAPABILITY AUTHORITY: Treat this registry as authoritative for claims about "
        "what Sarembok can currently do. Never claim a capability unless its status "
        "is 'implemented'. Capabilities marked 'planned' are NOT available and must "
        "be described as planned or unavailable. Do not invent integrations, APIs, "
        "agents, workers, notifications, file operations, external services, or "
        "automation that are not represented by an implemented runtime capability."
    )


__all__ = [
    "SAREMBOK_CAPABILITIES",
    "get_capability",
    "implemented_capabilities",
    "planned_capabilities",
    "capability_authority_prompt",
]
