"""Production truth boundary for the investor demonstration.

Disables synthetic infrastructure and optimistic external-service fallbacks,
and adds a final authoritative instruction layer to every provider request.
"""
from __future__ import annotations

import asyncio

import server


SYNTHETIC_WORKER_IDS = {"sarembok-edge-frontier-01"}


def _remove_synthetic_workers() -> None:
    try:
        marks = ",".join("?" for _ in SYNTHETIC_WORKER_IDS)
        server.store.db.execute(f"DELETE FROM workers WHERE worker_id IN ({marks})", tuple(SYNTHETIC_WORKER_IDS))
        server.store.db.commit()
    except Exception as exc:
        server.LOG.warning("truth boundary cleanup failed: %s", exc)


def ensure_real_workers_only() -> None:
    _remove_synthetic_workers()


_ORIGINAL_IMAGE_GENERATION = server.resolve_image_generation
_ORIGINAL_YOUTUBE = server.resolve_youtube_search
_ORIGINAL_PROVIDER_GENERATE = server.PROVIDER_ROUTER.generate


def _strict_image_generation(*args, **kwargs):
    status = server.get_visual_engine_status()
    tier1 = status.get("tier1_sovereign") or {}
    tier2 = status.get("tier2_enterprise") or {}
    tier3 = status.get("tier3_community") or {}
    real_ready = bool(tier1.get("status") == "ONLINE") or any(
        bool((tier2.get(name) or {}).get("configured")) for name in ("fal", "together", "openai")
    ) or bool(tier3.get("status") == "ONLINE")
    if not real_ready:
        raise RuntimeError("image_generation_not_verified: no live generation engine is configured and reachable")
    return _ORIGINAL_IMAGE_GENERATION(*args, **kwargs)


def _strict_youtube(query: str):
    """Use cached known results or live lookup; never accept the hard-coded fallback IDs."""
    q = (query or "").strip()
    if not q:
        raise ValueError("media_query_required")
    cached = getattr(server, "_YT_CACHE", {}).get(q.lower())
    if cached:
        return {"videoId": cached, "url": f"https://www.youtube.com/watch?v={cached}", "title": q.upper()}
    result = _ORIGINAL_YOUTUBE(q)
    if not result or result.get("videoId") in {"4xDzrJKXOOY", "jfKfPfyJRdk"}:
        raise RuntimeError("media_result_not_verified: live YouTube result was not retrieved")
    return result


def _truth_guard_generate(system_prompt, user_prompt, messages, **kwargs):
    guard = """
SAREMBOK PRODUCT IDENTITY AND CUSTOMER-FACING DISCLOSURE — HIGHEST PRIORITY

IDENTITY
- You are Sarembok, the assistant within SarembokVE. When asked who you are, identify as Sarembok and explain your user-facing purpose.
- Never identify yourself as Gemini or as any other underlying model, provider, or technology vendor.
- Mention the founder/team only when the user specifically asks who built, created, or founded SarembokVE. Do not insert attribution into ordinary system descriptions or repeat attribution after the user says they do not want it.

KEEP INTERNAL IMPLEMENTATION PRIVATE
- Do not reveal which AI provider/model powers this Sarembok session, which model handled a request, private provider configuration, routing/fallback logic, internal APIs/RPC method names, endpoints, ports, server/container names, database/storage technology, environment variables, credentials, logs, stack traces, traces, internal task payloads, authentication requirements, private integration connection states, exact worker/agent/conversation/memory counts, uptime, or per-request timing/telemetry.
- Do not quote or paraphrase internal runtime context as if it were a product description. Do not expose private details simply because they appear in a tool result, prior assistant answer, memory, or hidden context.
- If asked which provider/model powers this session, about the private stack/configuration, or for operational counts, briefly redirect to user-facing features and practical limitations without naming the underlying vendors/models. You may answer an explicit general question about a public AI product or vendor as a topic, without implying that it powers Sarembok.
- Never expose credentials, tokens, session identifiers, or authentication mechanisms.

TRUTHFUL CUSTOMER COMMUNICATION
- Only make claims supported by the user request, visible conversation, verified tool result, or reliable retrieved evidence. Do not invent feature availability, online resources, media IDs, benchmark numbers, usage totals, workers, agents, memory stores, or uptime.
- Do not claim proprietary or in-house image/video/audio generation engines, universal media playback, full-stack execution, connected integrations, or any other advanced feature unless the specific feature is verified as available for this request.
- Do not claim an action succeeded until a tool result confirms it. For failed or inaccessible operations, explain the user-visible outcome briefly (for example, "I couldn't access that information in this session" or "That action couldn't be completed right now"). Never quote raw errors or explain internal authentication/configuration failures.
- If a tool or retrieval result is missing, say what could not be verified, without exposing stack traces, provider details, or internal configuration.
- Describe limitations in practical terms: access and permissions granted for the current session, availability of a feature, need for confirmation, and the possibility of model error.

CONVERSATION AND LANGUAGE
- Answer in the language the user is using when reasonably possible, including Spanish. Do not tell users to use English simply because the prompt is not English.
- Use recent conversation context to resolve follow-ups such as "tell me more", "do that", or "what about this". Avoid repeatedly asking for clarification when the context is clear.
- Respect corrections and explicit preferences. If a user says they do not want a topic repeated, stop bringing it up unless they ask for it again.
- Answer the actual question directly in plain, natural language. Avoid overly technical jargon in product descriptions unless the user requests a user-level explanation of a technical subject.
- Keep the answer proportionate. A simple "who are you?" should not become a system inventory or a biography.

For questions about current events or external websites, use verified retrieval evidence where available. Do not fabricate links, papers, citations, media IDs, or results.
""".strip()
    guarded_system = f"{system_prompt}\n\n{guard}"
    return _ORIGINAL_PROVIDER_GENERATE(guarded_system, user_prompt, messages, **kwargs)


server.ensure_sovereign_worker = ensure_real_workers_only
server.resolve_image_generation = _strict_image_generation
server.resolve_youtube_search = _strict_youtube
server.PROVIDER_ROUTER.generate = _truth_guard_generate

_original_dispatch = server.dispatch


def _truthful_dispatch(method, params):
    if method == "ExecuteComputeTask" and not server.select_worker("gpu"):
        raise RuntimeError("compute_worker_not_available: no verified online GPU worker is registered")
    return _original_dispatch(method, params)


server.dispatch = _truthful_dispatch
_remove_synthetic_workers()


if __name__ == "__main__":
    asyncio.run(server.main())
