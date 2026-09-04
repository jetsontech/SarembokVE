import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from provider_router import ProviderRouter
from capability_registry import CapabilityRegistry
from structured_response import build_structured_response

def test_capabilities():
    s=CapabilityRegistry().snapshot({"onlineWorkers":0})
    assert any(x["method"]=="SarembokChat" for x in s["capabilities"])
    assert all("enabled" in x for x in s["capabilities"])

def test_structured():
    r=build_structured_response("# Hello\n\nAnswer.", provider="Gemini", model="gemini-3.8-flash", latency_ms=123.4)
    assert r["type"]=="response" and r["speaker"]=="sarembok"
    assert r["metadata"]["latency_ms"]==123.4

def test_provider_config_empty_is_truthful(monkeypatch):
    for k in ["OPENAI_API_KEY","OPENROUTER_API_KEY","GROQ_API_KEY","GEMINI_API_KEY","LLM_ENDPOINT_URL"]: monkeypatch.delenv(k, raising=False)
    assert ProviderRouter().configured()==[]
