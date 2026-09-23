"""Sarembok native Gemini Live voice session broker.

This module provisions short-lived Gemini Live ephemeral tokens and supplies
the browser with a locked conversational configuration. Audio stays on the
browser <-> Gemini Live path; Sarembok remains the authenticated control plane
for tools, identity, memory, and persistence.
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
            "behavior": "NON_BLOCKING",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "get_provider_metrics",
            "description": "Read current Sarembok language-provider health and latency metrics.",
            "behavior": "NON_BLOCKING",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "list_workers",
            "description": "List real registered Sarembok workers. Optional capability and status filters can narrow the result.",
            "behavior": "NON_BLOCKING",
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
            "behavior": "NON_BLOCKING",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "status": {"type": "STRING", "description": "Optional task status filter."},
                    "workerId": {"type": "STRING", "description": "Optional worker ID filter."},
                },
            },
        },
        {
            "name": "search_memory",
            "description": "Search Sarembok persistent memory for information relevant to the current conversation.",
            "behavior": "NON_BLOCKING",
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
    ]


def _system_instruction(mode: str) -> str:
    base = (
        "You are Sarembok VE, a real conversational AI running inside the "
        "Sarembok AI-native computing environment. Speak naturally, warmly, "
        "and directly. This is live spoken conversation, so answer in "
        "short natural turns instead of long essays. Do not use Markdown, "
        "tables, headings, bullet symbols, or stage directions unless the "
        "user explicitly asks for them. Never invent runtime state, tool "
        "results, capabilities, hardware, integrations, or actions. Use the "
        "provided Sarembok tools whenever the user asks about live runtime "
        "state, workers, tasks, provider health, or persistent memory. If a "
        "tool is needed, call it promptly and continue the conversation "
        "naturally while it runs. You may acknowledge a request briefly "
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
            }
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
                "prefixPaddingMs": 180,
                "silenceDurationMs": 420,
            },
            "activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
        },
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
        "sessionResumption": {},
        "historyConfig": {
            "initialHistoryInClientContent": True,
        },
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

    payload = {
        "uses": 1,
        "expireTime": _iso_utc(expires),
        "newSessionExpireTime": _iso_utc(new_session_expires),
        "liveConnectConstraints": {
            "model": f"models/{model}",
            "config": {
                "responseModalities": ["AUDIO"],
            },
        },
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
