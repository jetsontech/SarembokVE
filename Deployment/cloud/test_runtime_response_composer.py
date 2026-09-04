"""Unit tests for authoritative runtime response composition."""
from __future__ import annotations

from runtime_response_composer import build_runtime_context, is_self_state_query, render_identity


SNAPSHOT = {
    "runtime": {"status": "ONLINE", "service": "sarembok-ve-cloud-runtime", "domain": "sarembok.com", "port": 9000},
    "workers": {"registered": 4, "online": 2, "stale": 1, "offline": 1},
    "agents": {"registered": 3, "online": 2},
    "compute": {"onlineGpuWorkers": 1, "onlineWorkerCapabilities": ["compute", "llm"]},
    "memory": {"backend": "sqlite-wal", "status": "ONLINE", "entries": 7, "integrity": "OK"},
    "scheduler": {"status": "READY", "queueDepth": 2, "running": 1, "completed": 9, "failed": 0},
    "provider": {"configuredProviders": [{"name": "OpenRouter", "model": "openai/gpt-oss-120b", "api": "chat.completions"}]},
}


def test_self_state_queries_are_detected() -> None:
    assert is_self_state_query("what system is this?")
    assert is_self_state_query("how many workers are online?")
    assert is_self_state_query("what providers are configured?")
    assert not is_self_state_query("write a Python function")


def test_identity_uses_observed_state() -> None:
    text = render_identity(SNAPSHOT)
    assert "Sarembok VE" in text
    assert "2 online workers" in text
    assert "3 registered agents" in text
    assert "7 stored entries" in text
    assert "OpenRouter" in text


def test_runtime_context_contains_authoritative_facts() -> None:
    text = build_runtime_context(SNAPSHOT)
    assert "registered=4; online=2; stale=1; offline=1" in text
    assert "queue_depth=2" in text
    assert "OpenRouter: model=openai/gpt-oss-120b" in text
    assert "Never invent workers" in text


if __name__ == "__main__":
    test_self_state_queries_are_detected()
    test_identity_uses_observed_state()
    test_runtime_context_contains_authoritative_facts()
    print("runtime_response_composer: PASS")
