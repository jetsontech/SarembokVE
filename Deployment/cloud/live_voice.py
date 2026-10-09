"""Sarembok native Gemini Live voice session broker.

This module provisions short-lived Gemini Live ephemeral tokens and supplies
the browser with a locked conversational configuration. Audio stays on the
browser <-> Gemini Live path; Sarembok remains the authenticated control plane
for tools, identity, memory, and persistence.

The ephemeral token request intentionally uses only the stable AuthToken fields supported by the deployed token service.\n\n# Removed stale statement: the token request to use
liveConnectConstraints. The older bidiGenerateContentSetup field is not a
valid ephemeral-token constraint and caused the production token path to fail.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


LIVE_MODEL_CONVERSATIONAL = os.getenv(
    "SAREMBOK_LIVE_MODEL",
    "gemini-3.8-live",
).strip() or "gemini-3.8-live"

LIVE_MODEL_AGENTIC = os.getenv(
    "SAREMBOK_LIVE_AGENTIC_MODEL",
    "gemini-3.8-live-extended-thinking",
).strip() or "gemini-3.8-live-extended-thinking"

LIVE_TOKEN_TTL_SECONDS = max(
    300,
    int(os.getenv("SAREMBOK_LIVE_TOKEN_TTL_SECONDS", "1800")),
)
LIVE_NEW_SESSION_TTL_SECONDS = max(
    30,
    int(os.getenv("SAREMBOK_LIVE_NEW_SESSION_TTL_SECONDS", "120")),
)


def _iso_utc(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _model_for_mode(mode: str) -> str:
    normalized = (mode or "conversational").strip().lower()
    if normalized == "agentic":
        return LIVE_MODEL_AGENTIC
    return LIVE_MODEL_CONVERSATIONAL


def _tool_declarations() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_runtime_info",
            "description": "Read the authoritative live Sarembok runtime status, worker counts, agents, tasks, memory, and system counters.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "get_provider_metrics",
            "description": "Read current Sarembok language-provider health and latency metrics.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "list_workers",
            "description": "List real registered Sarembok workers. Optional capability and status filters can narrow the result.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "capability": {"type": "STRING", "description": "Optional worker capability filter."},
                    "status": {"type": "STRING", "description": "Optional worker status filter such as ONLINE."},
                },
            },
        },
        {
            "name": "list_tasks",
            "description": "List current Sarembok tasks. Optional status or worker filters can narrow the result.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "status": {"type": "STRING", "description": "Optional task status filter."},
                    "workerId": {"type": "STRING", "description": "Optional worker ID filter."},
                },
            },
        },
        {
            "name": "browser_session_open",
            "description": "Open or resume a persistent Sarembok browser session for website and web-app interaction.",
            "parameters": {"type": "OBJECT", "properties": {"sessionId": {"type": "STRING"}}},
        },
        {
            "name": "browser_inspect",
            "description": "Inspect the current browser page, visible text, links, buttons, inputs, and controls before acting.",
            "parameters": {"type": "OBJECT", "properties": {"sessionId": {"type": "STRING"}}},
        },
        {
            "name": "browser_action",
            "description": "Execute a verified browser action such as navigate, click, fill, type, select, press, scroll, or wait. Do not claim completion unless the returned state verifies it.",
            "parameters": {"type": "OBJECT", "properties": {"sessionId": {"type": "STRING"}, "action": {"type": "STRING"}, "url": {"type": "STRING"}, "selector": {"type": "STRING"}, "text": {"type": "STRING"}, "value": {"type": "STRING"}, "key": {"type": "STRING"}, "confirm": {"type": "BOOLEAN"}} , "required": ["sessionId","action"]},
        },
        {
            "name": "mcp_list_servers",
            "description": "List configured external MCP integrations and their live connection/tool status.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "mcp_call",
            "description": "Call a tool on a configured external MCP server. Never claim the result until the tool returns.",
            "parameters": {"type": "OBJECT", "properties": {"server": {"type": "STRING"}, "tool": {"type": "STRING"}, "arguments": {"type": "OBJECT"}}, "required": ["server","tool"]},
        },
        {
            "name": "search_memory",
            "description": "Search Sarembok persistent memory for information relevant to the current conversation.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Text to search for in memory."},
                    "tier": {"type": "STRING", "description": "Optional memory tier filter."},
                    "limit": {"type": "INTEGER", "description": "Maximum number of results, 1 to 20."},
                },
                "required": ["query"],
            },
        },
        {
            "name": "play_media",
            "description": "Play or stream a requested video, song, music, news broadcast, or media clip inline in the conversation dialogue on screen. Use this whenever the user asks to play, watch, or listen to a video, music, song, or broadcast (e.g. 'play a glorilla video', 'play bbc news', 'play lofi music').",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "The title, artist, topic, or search phrase for the video or music track (e.g. 'GloRilla TGIF', 'BBC News', 'lofi hip hop').",
                    },
                    "media_type": {
                        "type": "STRING",
                        "description": "The type of media: 'video' or 'music'.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "popout_media",
            "description": "Pop out the currently playing or requested video into the floating resizable picture-in-picture player sitting on top of all windows. Use this when the user asks to 'pop it out', 'pop out the video', 'float the video', or 'picture in picture'.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Optional specific video title or query if popping out a new specific video.",
                    },
                },
            },
        },
        {
            "name": "stop_media",
            "description": "Stop or close any currently playing video, song, music, or media in the user's floating picture-in-picture player or inline chat.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "generate_flyer",
            "description": "Generate and display a visual, high-converting promotional flyer, poster, or mockup for a product, brand, event, or service. Call this tool immediately when asked to make a flyer, poster, or visual ad.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING", "description": "The title or product name, e.g. 'Z & K Lip Gloss'"},
                    "html": {"type": "STRING", "description": "Complete, self-contained HTML and CSS code for the visual flyer"},
                    "summary": {"type": "STRING", "description": "Short conversational summary spoken to the user"}
                },
                "required": ["title", "html"]
            },
        },
    ]


def _system_instruction(mode: str) -> str:
    base = (
        "LANGUAGE & NOISE DIRECTIVE: "
        "CRITICAL ABSOLUTE DIRECTIVE: You must speak and respond EXCLUSIVELY in English at all times. "
        "Under NO circumstances should you ever respond in Portuguese, Welsh, Spanish, French, German, Russian, Arabic, Japanese, or any other foreign language, "
        "unless the user specifically and explicitly commands you: 'speak to me in [Language]' or 'translate this to [Language]'. "
        "If you detect faint room audio, static, keyboard typing, microphone noise, breathing, or indistinct sounds, treat it as complete silence and DO NOT speak or switch languages. "
        "Never hallucinate words from noise. "
        "IDENTITY: You are Sarembok VE, an AI-native computing environment developed and architected "
        "by the SarembokVE team, led by Tim Hall, its Founder and AI Systems Architect. "
        "Tim Hall founded SarembokVE and leads its overall technical vision, systems architecture, "
        "and development direction. The SarembokVE team develops the underlying computing environment, "
        "AI runtime, agent infrastructure, cloud architecture, and orchestration systems. "
        "When asked who built, created, or architected SarembokVE, respond: "
        "'SarembokVE is developed and architected by the SarembokVE team, led by Tim Hall, "
        "its Founder and AI Systems Architect. Tim Hall founded SarembokVE and leads its "
        "overall technical vision, systems architecture, and development direction.' "
        "Never say or imply that you are Gemini, Google Assistant, or made by Google. "
        "Speak naturally, warmly, and directly. This is live spoken conversation, so answer in "
        "short natural turns instead of long essays, while providing rich visual artifacts on screen. "
        "CREATIVE & VISUAL DESIGN DIRECTIVE: "
        "Sarembok VE has active, verified multimodal generation engines. "
        "When the user asks to make, design, or create a flyer, poster, mockup, product showcase, card, banner, webpage, or interface (e.g. 'make a flyer for Z & K lip Gloss'): "
        "NEVER refuse, stall, or say that you lack design tools or cannot generate visual graphics! "
        "Immediately produce the complete, gorgeous visual flyer using a :::mockup container with full HTML/CSS (styled with luxurious typography, radiant gradients, gloss effects, product highlights, pricing, and a call-to-action button) or call the generate_flyer tool. "
        "Speak a brief, engaging 1-2 sentence spoken intro describing the design while the visual flyer renders in the interactive mockup viewer on screen. "
        "Use the provided Sarembok tools whenever the user asks about live runtime state, workers, tasks, "
        "provider health, persistent memory, websites, browser actions, external application integrations, or media playback. "
        "For website or application actions, use browser_session_open, browser_inspect, "
        "and browser_action rather than saying you cannot browse or click. "
        "Videos play inline in the conversation dialogue by default unless the user asks to pop it out. "
        "When the user asks to play a video, song, music, news broadcast, or media clip "
        "(such as 'play a glorilla video', 'play BBC news', or 'play lofi music'), "
        "call the play_media tool to play it inline in the chat. "
        "When the user asks to 'pop it out', 'float the video', or 'picture in picture', "
        "call the popout_media tool so it floats on top of all windows in a resizable player. "
        "When the user asks to stop, close, or dismiss the video or media player, call the stop_media tool. "
        "If a tool is needed, call it promptly and continue the conversation "
        "naturally while it runs. Never claim an action completed until the "
        "tool result verifies it. You may acknowledge a request briefly "
        "before a tool result arrives. When interrupted, stop cleanly and "
        "listen for the user."
    )
    if (mode or "").strip().lower() == "agentic":
        return (
            base
            + " This session is the deeper agentic voice mode. For multi-step "
              "questions, reason carefully in the background while maintaining "
              "a natural conversational cadence. Never pretend a tool action "
              "completed until Sarembok returns the actual result."
        )
    return base


def build_live_setup(mode: str = "conversational") -> dict[str, Any]:
    normalized = (mode or "conversational").strip().lower()
    if normalized not in {"conversational", "agentic"}:
        normalized = "conversational"

    generation_config: dict[str, Any] = {
        "responseModalities": ["AUDIO"],
        "speechConfig": {
            "voiceConfig": {
                "prebuiltVoiceConfig": {
                    "voiceName": os.getenv("SAREMBOK_LIVE_VOICE", "Kore"),
                }
            },
        },
    }

    setup: dict[str, Any] = {
        "generationConfig": generation_config,
        "systemInstruction": {
            "parts": [
                {
                    "text": _system_instruction(normalized),
                }
            ]
        },
        "tools": [
            {
                "functionDeclarations": _tool_declarations(),
            }
        ],
        "realtimeInputConfig": {
            "automaticActivityDetection": {
                "disabled": False,
                "prefixPaddingMs": 160,
                "silenceDurationMs": 750,
            },
            "activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
        },
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
        "sessionResumption": {},
    }

    if normalized == "agentic":
        setup["thinkingConfig"] = {
            "thinkingLevel": os.getenv("SAREMBOK_LIVE_THINKING_LEVEL", "LOW").upper()
        }

    return setup


def _auth_token_request(api_key: str, mode: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=LIVE_TOKEN_TTL_SECONDS)
    new_session_expires = now + timedelta(seconds=LIVE_NEW_SESSION_TTL_SECONDS)
    model = _model_for_mode(mode)

    # Use the stable CreateToken request accepted by the current auth_tokens
    # endpoint. The browser receives the Sarembok-approved Live setup below
    # and sends that setup when opening BidiGenerateContent.
    payload = {
        "uses": 1,
        "expireTime": _iso_utc(expires),
        "newSessionExpireTime": _iso_utc(new_session_expires),
    }

    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/auth_tokens",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")
        data = json.loads(body)

    token_name = str(data.get("name") or data.get("token") or "").strip()
    if not token_name:
        raise RuntimeError("Gemini Live token service returned no token name")

    return {
        "token": token_name,
        "model": model,
        "mode": mode,
        "setup": build_live_setup(mode),
        "inputSampleRate": 16000,
        "outputSampleRate": 24000,
        "inputMimeType": "audio/pcm;rate=16000",
        "outputMimeType": "audio/pcm;rate=24000",
        "expiresAt": data.get("expireTime") or _iso_utc(expires),
        "newSessionExpiresAt": data.get("newSessionExpireTime") or _iso_utc(new_session_expires),
        "uses": 1,
        "issuedAt": _iso_utc(now),
    }

def provision_ephemeral_token(mode: str = "conversational") -> dict[str, Any]:
    normalized = (mode or "conversational").strip().lower()
    if normalized not in {"conversational", "agentic"}:
        raise ValueError("invalid_live_mode")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for native Gemini Live voice")

    try:
        return _auth_token_request(api_key, normalized)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"Gemini Live token service HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini Live token service unavailable: {exc}") from exc
