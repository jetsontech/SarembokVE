"""Unit tests for Sarembok Multimodal Vision Payload Construction."""
import pytest
from provider_router import ProviderRouter, ProviderSpec


def test_openai_multimodal_payload():
    router = ProviderRouter()
    spec = ProviderSpec(name="OpenAI", model="gpt-4o", kind="openai", endpoint="https://api.openai.com/v1/chat/completions", key="sk-test")
    fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    payload = router._openai_payload(
        spec=spec,
        messages=[],
        prompt="What is in this frame?",
        image_frame=fake_b64,
    )
    
    messages = payload.get("messages", [])
    assert len(messages) == 1
    user_msg = messages[0]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)
    assert len(user_msg["content"]) == 2
    assert user_msg["content"][0]["type"] == "text"
    assert user_msg["content"][0]["text"] == "What is in this frame?"
    assert user_msg["content"][1]["type"] == "image_url"
    assert "base64" in user_msg["content"][1]["image_url"]["url"]


def test_openai_standard_text_payload():
    router = ProviderRouter()
    spec = ProviderSpec(name="OpenAI", model="gpt-4o", kind="openai", endpoint="https://api.openai.com/v1/chat/completions", key="sk-test")
    
    payload = router._openai_payload(
        spec=spec,
        messages=[],
        prompt="Hello world",
        image_frame=None,
    )
    
    messages = payload.get("messages", [])
    assert len(messages) == 1
    user_msg = messages[0]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "Hello world"
