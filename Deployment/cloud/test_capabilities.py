from capabilities import (
    SAREMBOK_CAPABILITIES,
    capability_authority_prompt,
    implemented_capabilities,
    planned_capabilities,
)


def test_registry_has_no_unknown_statuses():
    allowed = {"implemented", "planned", "experimental"}
    assert SAREMBOK_CAPABILITIES
    assert all(item["status"] in allowed for item in SAREMBOK_CAPABILITIES.values())


def test_implemented_capabilities_exclude_planned_integrations():
    implemented = implemented_capabilities()
    planned = planned_capabilities()

    assert "memory" in implemented
    assert "live_research" in implemented
    assert "provider_fallback_routing" in implemented
    assert "email_delivery" not in implemented
    assert "slack_delivery" not in implemented
    assert "push_notifications" not in implemented
    assert "email_delivery" in planned
    assert "slack_delivery" in planned
    assert "push_notifications" in planned


def test_capability_authority_prompt_has_fail_closed_rules():
    prompt = capability_authority_prompt()
    assert "authoritative" in prompt.lower()
    assert "planned" in prompt.lower()
    assert "do not invent" in prompt.lower()
