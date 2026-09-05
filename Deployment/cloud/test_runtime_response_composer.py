from runtime_response_composer import (
    build_runtime_context,
    is_self_state_query,
    render_identity,
    render_model_inventory,
)


SNAPSHOT = {
    "runtime": {
        "status": "ONLINE",
        "service": "sarembok-ve-cloud-runtime",
        "domain": "sarembok.com",
        "port": 9000,
    },
    "workers": {
        "registered": 4,
        "online": 2,
        "stale": 1,
        "offline": 1,
    },
    "agents": {
        "registered": 3,
        "online": 2,
    },
    "compute": {
        "onlineGpuWorkers": 1,
        "onlineWorkerCapabilities": ["compute", "llm"],
    },
    "memory": {
        "backend": "sqlite-wal",
        "status": "ONLINE",
        "entries": 7,
        "integrity": "OK",
    },
    "scheduler": {
        "status": "READY",
        "queueDepth": 2,
        "running": 1,
        "completed": 9,
        "failed": 0,
    },
    "provider": {
        "configuredProviders": [
            {
                "name": "Gemini",
                "model": "gemini-3.8-flash",
                "api": "interactions",
            },
            {
                "name": "OpenRouter",
                "model": "openai/gpt-oss-120b",
                "api": "chat.completions",
            },
            {
                "name": "Groq",
                "model": "openai/gpt-oss-120b",
                "api": "chat.completions",
            },
        ],
        "lastSuccessful": {
            "provider": "OpenRouter",
            "model": "openai/gpt-oss-120b",
        },
    },
}


def test_self_state_queries():
    assert is_self_state_query("what system is this?")
    assert is_self_state_query("what model is this?")
    assert is_self_state_query("what other models are available?")
    assert is_self_state_query("what models can I use?")
    assert is_self_state_query("which models are configured?")
    assert is_self_state_query("what providers are configured?")
    assert not is_self_state_query("write a Python function")


def test_identity():
    text = render_identity(SNAPSHOT)

    assert "Sarembok VE" in text
    assert "2 online workers" in text
    assert "3 registered agents" in text
    assert "7 stored entries" in text
    assert "Gemini" in text
    assert "OpenRouter" in text


def test_runtime_context():
    text = build_runtime_context(SNAPSHOT)

    assert "registered=4; online=2; stale=1; offline=1" in text
    assert "queue_depth=2" in text
    assert "Gemini: model=gemini-3.8-flash" in text
    assert "OpenRouter: model=openai/gpt-oss-120b" in text
    assert "Groq: model=openai/gpt-oss-120b" in text
    assert "model availability" in text.lower()


def test_model_inventory():
    text = render_model_inventory(SNAPSHOT)

    assert "gemini-3.8-flash" in text
    assert "openai/gpt-oss-120b" in text
    assert "Gemini" in text
    assert "OpenRouter" in text
    assert "Groq" in text
    assert "Most recently successful model" in text
    assert "external catalog" in text
    assert "Sarembok-available" in text


if __name__ == "__main__":
    test_self_state_queries()
    test_identity()
    test_runtime_context()
    test_model_inventory()
    print("runtime_response_composer: PASS")
