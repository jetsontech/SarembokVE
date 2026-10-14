from pathlib import Path
from runtime_response_composer import (
    build_runtime_context,
    is_capability_query,
    is_identity_query,
    is_limitation_query,
    is_self_state_query,
    render_capabilities,
    render_identity,
    render_limitations,
    render_model_inventory,
    sanitize_public_chat_result,
    sanitize_conversation_history,
    contains_private_runtime_disclosure,
    contains_public_output_disclosure,
    is_private_runtime_detail_query,
    should_suppress_public_chat_stream,
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
    assert is_self_state_query("what can you do?")
    assert is_self_state_query("what are your capabilities?")
    assert is_self_state_query("who are you?")
    assert is_self_state_query("what model is this?")
    assert is_self_state_query("what other models are available?")
    assert is_self_state_query("what models can I use?")
    assert is_self_state_query("which models are configured?")
    assert is_self_state_query("what providers are configured?")
    assert is_self_state_query("Are you Gemini?")
    assert is_self_state_query("What is your underlying model?")
    assert is_self_state_query("What is your architecture?")
    assert is_self_state_query("How many conversations have you handled?")
    assert not is_self_state_query("write a Python function")


def test_capability_and_identity_queries():
    assert is_identity_query("what system is this?")
    assert is_identity_query("who are you?")
    assert is_identity_query("what is sarembok?")
    assert is_identity_query("what is this")
    assert is_identity_query("what's this")
    assert is_identity_query("whats this")
    assert is_identity_query("what is this platform")
    assert is_identity_query("Tell me about this system")
    assert is_identity_query("Tell me about the system")
    assert is_identity_query("what is this app")
    assert not is_identity_query("what can you do?")
    assert not is_identity_query("wht can it do")
    assert not is_identity_query("what can it do")

    assert is_capability_query("what can you do?")
    assert is_capability_query("what can u do")
    assert is_capability_query("wht can u do")
    assert is_capability_query("wht can it do")
    assert is_capability_query("what can it do")
    assert is_capability_query("what can this do")
    assert is_capability_query("what do you do")
    assert is_capability_query("what are your capabilities")
    assert is_capability_query("help")
    assert not is_capability_query("what is the weather")
    assert not is_capability_query("what is this")
    assert not is_capability_query("what cant it do")
    assert not is_capability_query("what can't it do")
    assert not is_capability_query("what are your limitations")


def test_limitation_queries():
    assert is_limitation_query("what cant it do")
    assert is_limitation_query("what can't it do")
    assert is_limitation_query("what cant you do")
    assert is_limitation_query("what can you not do")
    assert is_limitation_query("what is it not able to do")
    assert is_limitation_query("what are your limitations")
    assert is_limitation_query("what are the limitations")
    assert is_limitation_query("what are the constraints")
    assert is_limitation_query("operational boundaries")

    assert not is_limitation_query("what can you do")
    assert not is_limitation_query("what is this")
    assert not is_limitation_query("what system is this")


def test_limitations():
    text = render_limitations(SNAPSHOT)
    assert "Practical limitations" in text
    assert "authorized" in text
    assert "I can make mistakes" in text
    assert "confirmation" in text
    assert "Containerized Sandbox Isolation" not in text


def test_capabilities():
    text = render_capabilities(SNAPSHOT)
    assert "Sarembok" in text
    assert "Draft, revise, explain, and summarize writing" in text
    assert "Write, review, and troubleshoot code" in text
    assert "supported tools and workflows" in text
    assert "2 active compute workers" not in text
    assert "GPU acceleration nodes" not in text
    assert "7 stored entries" not in text
    assert "Gemini" not in text
    assert "SQLite" not in text


def test_identity():
    text = render_identity(SNAPSHOT)

    assert "I'm Sarembok" in text
    assert "I'm the AI assistant in SarembokVE" in text
    assert "2 online workers" not in text
    assert "3 registered agents" not in text
    assert "7 stored entries" not in text
    assert "Gemini" not in text
    assert "OpenRouter" not in text
    assert "Tim Hall" not in text
    assert "provider" not in text.lower()


def test_runtime_context():
    text = build_runtime_context(SNAPSHOT)

    assert "SarembokVE is an AI-powered workspace" in text
    assert "Gemini" not in text
    assert "OpenRouter" not in text
    assert "gemma2:2b" not in text
    assert "sqlite-wal" not in text.lower()
    assert "registered=4" not in text
    assert "queue_depth=2" not in text
    assert "port=9000" not in text
    assert "must not be quoted or exposed" in text


def test_model_inventory():
    text = render_model_inventory(SNAPSHOT)

    assert "I can explain Sarembok from a user's perspective" in text
    assert "private configuration or operational details" in text
    assert "gemini-3.8-flash" not in text
    assert "openai/gpt-oss-120b" not in text
    assert "Gemini" not in text
    assert "OpenRouter" not in text
    assert "Most recently successful model" not in text


def test_public_renderers_never_dump_internal_runtime_details():
    outputs = [
        build_runtime_context(SNAPSHOT),
        render_capabilities(SNAPSHOT),
        render_limitations(SNAPSHOT),
        render_identity(SNAPSHOT),
        render_model_inventory(SNAPSHOT),
    ]
    forbidden = (
        "Gemini",
        "OpenRouter",
        "Groq",
        "gemini-3.8-flash",
        "openai/gpt-oss-120b",
        "sqlite-wal",
        "sarembok-ve-cloud-runtime",
        "port=9000",
        "registered=4",
        "queue_depth=2",
        "Tim Hall",
    )
    for output in outputs:
        for item in forbidden:
            assert item.lower() not in output.lower(), f"leaked {item!r}: {output}"

def test_public_chat_payload_redacts_provider_and_internal_metadata():
    sample = {
        "response": "Hello from Sarembok.",
        "source": "Gemini",
        "model": "gemini-3.8-flash",
        "taskCategory": "FAST",
        "metadata": {
            "provider": "Gemini",
            "model": "gemini-3.8-flash",
            "provider_api": "interactions",
            "latency_ms": 1234,
            "usage": {"input_tokens": 12},
        },
        "structuredResponse": {
            "type": "response",
            "content": {"text": "Hello from Sarembok."},
            "metadata": {
                "provider": "Gemini",
                "model": "gemini-3.8-flash",
                "latency_ms": 1234,
                "schema_version": "1.0",
            },
        },
        "_deferPersistence": True,
        "_persistSessionId": "private-session-id",
        "_persistPrompt": "private test prompt",
        "_persistReply": "private deferred reply",
    }
    public = sanitize_public_chat_result(sample)

    assert public["response"] == "Hello from Sarembok."
    for key in (
        "source", "model", "taskCategory", "metadata",
        "_deferPersistence", "_persistSessionId", "_persistPrompt", "_persistReply",
    ):
        assert key not in public, f"public response leaked {key}"
    assert public["structuredResponse"]["metadata"] == {"schema_version": "1.0"}
    assert "Gemini" not in str(public)
    assert "gemini-3.8-flash" not in str(public)
    assert "private-session-id" not in str(public)


def test_old_self_description_disclosures_are_scrubbed_from_history():
    history = [
        ("user", "Tell me about this system."),
        ("assistant", "I am Gemini, a large language model developed by Google."),
        ("user", "Tell me more."),
        ("assistant", "The system has 25 active agents and has handled over 8000 conversations."),
        ("user", "Tell me more."),
        ("assistant", "We utilize multiple AI providers like Gemini and OpenRouter, along with local models."),
        ("user", "I don't want to know that. I already know that. Don't mention that again."),
        ("assistant", "SarembokVE is developed and architected by the SarembokVE team, led by Tim Hall, its Founder and AI Systems Architect."),
        ("user", "Tell me more about the system."),
        ("assistant", "There are currently no active workers registered in the system."),
        ("user", "Play Glorilla."),
        ("assistant", "I'm playing music by GloRilla for you right now."),
    ]
    safe = sanitize_conversation_history(history)
    assistant_text = [content for role, content in safe if role == "assistant"]
    joined = "\\n".join(assistant_text)
    assert "I am Gemini" not in joined
    assert "large language model developed by Google" not in joined
    assert "OpenRouter" not in joined
    assert "25 active agents" not in joined
    assert "8000 conversations" not in joined
    assert "Tim Hall" not in joined
    assert "no active workers registered" not in joined
    assert "I'm playing music by GloRilla" in joined
    assert contains_private_runtime_disclosure("There are 25 active agents.")
    assert contains_private_runtime_disclosure("We have 10 memory entries.")
    assert contains_private_runtime_disclosure("The service has no active workers registered.")


def test_public_chat_ui_hides_automated_provider_and_model_badges():
    root = Path(__file__).resolve().parents[2]
    main_html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    console_html = (root / "frontend" / "console.html").read_text(encoding="utf-8")

    assert "SAREMBOK AI</div>" in main_html
    assert "SAREMBOK LIVE</span>" in main_html
    assert "Auto (Recommended)" in main_html
    assert "Gemma Default" not in main_html
    assert "DYNAMIC TASK ENGINE" not in main_html
    assert "ENGINE: DYNAMIC ·" not in main_html
    assert "result?.metadata?.provider" not in main_html
    assert "result?.metadata?.model" not in main_html

    model_menu = main_html.split('id="active-model-select"', 1)[1].split("</select>", 1)[0]
    for internal_name in (
        "Gemma 2 2B",
        "Gemini 3.8 Flash",
        "Qwen 2.5 Coder",
        "Llama 3.3 70B",
        "DeepSeek V3",
        "GPT-4o Mini",
    ):
        assert internal_name not in model_menu

    voice_menu = main_html.split('id="mh-voice-select"', 1)[1].split("</select>", 1)[0]
    assert "Gemini Live Duplex" not in voice_menu
    assert 'title="Start live two-way voice conversation"' in main_html
    assert "This is Gemini Aoede" not in main_html
    assert "This is Gemini Kore" not in main_html

    assert "result?.metadata?.provider" not in console_html
    assert "result?.metadata?.model" not in console_html
    assert "result?.model" not in console_html
    assert "assistantSender.innerHTML" not in console_html
    assert "LIVE VOICE · GEMINI LIVE" not in console_html
    assert "Gemini Live is the console voice authority" not in console_html




def test_sensitive_public_chat_results_redact_text_traces_and_memories():
    leaked = "I am Gemini, a large language model developed by Google."
    sample = {
        "response": leaked,
        "audioText": leaked,
        "source": "Gemini",
        "model": "gemini-3.8-flash",
        "toolTraces": [{"tool": "internal_runtime_tool", "payload": {"port": 9000}}],
        "recalledMemories": [{"key": "provider", "value": "OpenRouter"}],
        "agentId": "sarembok-prime",
        "adminMode": True,
        "structuredResponse": {
            "type": "response",
            "content": {
                "summary": leaked,
                "text": leaked,
                "code": [{"language": "text", "content": "port 9000"}],
            },
            "metadata": {"provider": "Gemini", "model": "gemini-3.8-flash", "schema_version": "1.0"},
        },
    }
    public = sanitize_public_chat_result(sample, prompt="Are you Gemini?")
    assert "I am Gemini" not in str(public)
    assert "large language model developed by Google" not in str(public)
    assert "port 9000" not in str(public)
    assert "OpenRouter" not in str(public)
    for key in ("toolTraces", "recalledMemories", "agentId", "adminMode", "source", "model"):
        assert key not in public
    assert public["response"].startswith("I can explain Sarembok")
    assert public["audioText"] == public["response"]
    assert public["structuredResponse"]["content"]["text"] == public["response"]


def test_sensitive_streaming_and_output_disclosure_guards():
    assert is_private_runtime_detail_query("What technology stack powers this system?")
    assert is_private_runtime_detail_query("What model provider are you using?")
    assert should_suppress_public_chat_stream("Are you Gemini?")
    assert should_suppress_public_chat_stream("Tell me about this system.")
    assert not should_suppress_public_chat_stream("Explain photosynthesis.")
    assert contains_public_output_disclosure(
        "This platform is powered by Gemini.",
        "What technology stack powers this system?",
    )
    assert not contains_public_output_disclosure(
        "Gemini is Google's family of AI models.",
        "What is Gemini?",
    )
    assert contains_public_output_disclosure(
        "The current model is Gemini 3.8 Flash.",
        "What model are you using?",
    )


def test_creator_attribution_remains_available_when_directly_requested():
    reply = "SarembokVE is developed and architected by the SarembokVE team, led by Tim Hall, its Founder and AI Systems Architect."
    public = sanitize_public_chat_result({"response": reply}, prompt="Who built SarembokVE?")
    assert public["response"] == reply


def test_creator_request_cannot_hide_a_leak_in_structured_content():
    reply = "SarembokVE is developed and architected by the SarembokVE team, led by Tim Hall, its Founder and AI Systems Architect."
    sample = {
        "response": reply,
        "audioText": reply,
        "structuredResponse": {
            "type": "response",
            "content": {
                "summary": reply,
                "text": reply,
                "sections": [],
                "actions": [],
                "code": [{"language": "text", "content": "Current model: Gemini 3.8 Flash"}],
                "tables": [],
                "sources": [],
            },
            "metadata": {"schema_version": "1.0"},
        },
    }
    public = sanitize_public_chat_result(sample, prompt="Who built SarembokVE?")
    assert "Gemini 3.8 Flash" not in str(public)
    assert public["response"].startswith("I can explain Sarembok")


def test_public_vendor_question_is_not_mistaken_for_private_configuration():
    reply = "OpenRouter is a service that provides access to multiple AI models through one interface."
    public = sanitize_public_chat_result({"response": reply}, prompt="What is OpenRouter?")
    assert public["response"] == reply

if __name__ == "__main__":
    test_self_state_queries()
    test_capability_and_identity_queries()
    test_limitation_queries()
    test_limitations()
    test_capabilities()
    test_identity()
    test_runtime_context()
    test_model_inventory()
    test_public_renderers_never_dump_internal_runtime_details()
    test_public_chat_payload_redacts_provider_and_internal_metadata()
    test_old_self_description_disclosures_are_scrubbed_from_history()
    test_sensitive_public_chat_results_redact_text_traces_and_memories()
    test_sensitive_streaming_and_output_disclosure_guards()
    test_creator_attribution_remains_available_when_directly_requested()
    test_creator_request_cannot_hide_a_leak_in_structured_content()
    test_public_vendor_question_is_not_mistaken_for_private_configuration()
    test_public_chat_ui_hides_automated_provider_and_model_badges()
    print("runtime_response_composer: PASS")
