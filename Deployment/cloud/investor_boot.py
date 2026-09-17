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
    real_ready = bool(tier1.get("status") == "ONLINE") or any(
        bool((tier2.get(name) or {}).get("configured")) for name in ("fal", "together", "openai")
    )
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
FINAL SAREMBOK TRUTH BOUNDARY — HIGHEST PRIORITY
Only make claims supported by the runtime context, explicit tool observations, or retrieved evidence in this request.
Never invent or imply platform features, infrastructure, hardware, models, integrations, research, URLs, videos, documents, pricing, compliance, APIs, SDKs, or product roadmap items.
A configured provider is not proof of a feature being operational. A registered/recognized worker is not proof that it is usable for a requested task.
For a website URL or research request, do not describe the target from memory or inference. Use returned retrieval evidence; if none exists, explicitly say live evidence was not retrieved.
Never create fake citations, fake papers, fake download links, fake media IDs, or fabricated benchmark numbers.
When the user asks what Sarembok can do, describe only capabilities present in the authoritative runtime context and registered capability inventory. Do not use aspirational language as if it were current functionality.
""".strip()
    guarded_system = f"{system_prompt}\n\n{guard}"
    return _ORIGINAL_PROVIDER_GENERATE(guarded_system, user_prompt, messages, **kwargs)


server.ensure_sovereign_worker = ensure_real_workers_only
server.resolve_image_generation = _strict_image_generation
server.resolve_youtube_search = _strict_youtube
server.PROVIDER_ROUTER.generate = _truth_guard_generate
server.GPU_MARKETPLACE_TIERS = []

_original_dispatch = server.dispatch


def _truthful_dispatch(method, params):
    if method == "GetGpuMarketplace":
        stats = server.get_worker_status_counts()
        return {
            "tiers": [], "activeRentals": 0,
            "onlineWorkers": stats["onlineWorkers"],
            "registeredWorkers": stats["registeredWorkers"],
            "status": "NO_MARKETPLACE_CONFIGURED",
            "message": "No GPU rental inventory is currently configured. Runtime reports only real registered workers.",
        }
    if method == "RentGpuNode":
        raise ValueError("gpu_rental_not_configured")
    if method == "ExecuteComputeTask" and not server.select_worker("gpu"):
        raise RuntimeError("compute_worker_not_available: no verified online GPU worker is registered")
    return _original_dispatch(method, params)


server.dispatch = _truthful_dispatch
_remove_synthetic_workers()


if __name__ == "__main__":
    asyncio.run(server.main())
