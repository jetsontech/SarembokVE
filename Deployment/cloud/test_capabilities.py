from capabilities import (
    SAREMBOK_CAPABILITIES,
    capability_authority_prompt,
    implemented_capabilities,
    planned_capabilities,
)


def test_registry_has_only_known_statuses():
    allowed = {"implemented", "planned", "experimental"}
    assert SAREMBOK_CAPABILITIES
    assert all(item.get("status") in allowed for item in SAREMBOK_CAPABILITIES.values())


def test_planned_capabilities_are_fail_closed():
    implemented = implemented_capabilities()
    planned = planned_capabilities()
    assert "memory" in implemented
    assert "live_research" in implemented
    assert "email_delivery" not in implemented
    assert "slack_delivery" not in implemented
    assert "push_notifications" not in implemented
    assert "email_delivery" in planned
    assert "slack_delivery" in planned
    assert "push_notifications" in planned


def test_capability_authority_prompt_is_explicit():
    prompt = capability_authority_prompt().lower()
    assert "authoritative" in prompt
    assert "planned" in prompt
    assert "do not invent" in prompt
