"""Verification suite for SarembokVE production diagnosis acceptance criteria."""
import pytest
from Deployment.cloud.server import (
    sarembok_process_dialogue,
    _enrich_multimodal_reply,
    record_media_playback_event,
    SESSION_PLAYBACK_STATE,
)

def test_simultaneous_video_question():
    """Verify that asking if two videos can play simultaneously answers capability without video embedding."""
    query = "Can you play two videos at the same time?"
    res = sarembok_process_dialogue(query, session_id="test_sim_sess")
    assert res is not None
    assert "response" in res
    assert "taskCategory" in res
    assert res["taskCategory"] == "CAPABILITY"
    assert "SarembokVE supports" in res["response"]
    assert ":::video" not in res["response"]
    assert ":::music" not in res["response"]

import uuid

def test_playback_history_inquiry():
    """Verify that asking what was played references recorded history instead of searching."""
    session_id = f"test_hist_sess_{uuid.uuid4().hex[:8]}"
    # 1. Before any playback
    res1 = sarembok_process_dialogue("What video did you just play?", session_id=session_id)
    assert "No media playback has been initiated" in res1["response"]
    assert ":::video" not in res1["response"]

    # 2. Record a verified playback event
    record_media_playback_event(session_id, "GloRilla TGIF", "GloRilla - TGIF (Official Music Video)", "https://www.youtube.com/watch?v=mock123")

    # 3. Inquire again
    res2 = sarembok_process_dialogue("What video did you just play?", session_id=session_id)
    assert "GloRilla - TGIF (Official Music Video)" in res2["response"]
    assert "https://www.youtube.com/watch?v=mock123" in res2["response"]
    assert ":::video" not in res2["response"]

def test_p0_provider_failure_does_not_unbound_provider_task(monkeypatch):
    """Verify that when the LLM provider fails, provider_task is safely initialized and does not crash."""
    from Deployment.cloud.server import PROVIDER_ROUTER
    def mock_fail(*args, **kwargs):
        raise TimeoutError("Simulated LLM provider timeout")
    monkeypatch.setattr(PROVIDER_ROUTER, "generate", mock_fail)
    
    # Prompt with "play" that triggers provider failure & media fallback branch
    res = sarembok_process_dialogue("play some upbeat jazz", session_id="test_provider_fail_sess")
    assert res is not None
    assert "response" in res
    assert "metadata" in res
    assert res["metadata"].get("provider") is not None

def test_interactive_mockup_enrichment():
    """Verify that asking for an interactive mockup produces a :::mockup block, not a 2D image."""
    prompt = "Create an interactive HTML mockup of a modern fitness dashboard"
    html_code = "```html\n<!DOCTYPE html><html><head><title>Fitness</title></head><body><h1>Dashboard</h1></body></html>\n```"
    enriched = _enrich_multimodal_reply(prompt, html_code)
    assert ":::mockup" in enriched
    assert ":::image" not in enriched

def test_enrich_multimodal_reply_on_questions():
    """Verify that questions with the word 'play' do not trigger media card injection."""
    prompt = "Can you play two videos at the same time?"
    enriched = _enrich_multimodal_reply(prompt, "")
    assert ":::video" not in enriched
    assert ":::music" not in enriched
