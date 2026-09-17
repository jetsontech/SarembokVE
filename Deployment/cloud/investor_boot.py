"""Production safety shim for the investor demonstration.

The runtime historically contained synthetic demo hardware and optimistic
fallbacks. This wrapper disables those paths without changing the public RPC
contract. Real workers/providers continue to operate normally.
"""
from __future__ import annotations

import asyncio

import server


SYNTHETIC_WORKER_IDS = {"sarembok-edge-frontier-01"}


def _remove_synthetic_workers() -> None:
    try:
        marks = ",".join("?" for _ in SYNTHETIC_WORKER_IDS)
        server.store.db.execute(
            f"DELETE FROM workers WHERE worker_id IN ({marks})",
            tuple(SYNTHETIC_WORKER_IDS),
        )
        server.store.db.commit()
    except Exception as exc:
        server.LOG.warning("truth boundary cleanup failed: %s", exc)


def ensure_real_workers_only() -> None:
    _remove_synthetic_workers()


def _strict_image_generation(*args, **kwargs):
    status = server.get_visual_engine_status()
    tier1 = status.get("tier1_sovereign") or {}
    tier2 = status.get("tier2_enterprise") or {}
    real_ready = bool(tier1.get("status") == "ONLINE") or any(
        bool((tier2.get(name) or {}).get("configured"))
        for name in ("fal", "together", "openai")
    )
    if not real_ready:
        raise RuntimeError("image_generation_not_verified: no live generation engine is configured and reachable")
    return _ORIGINAL_IMAGE_GENERATION(*args, **kwargs)


def _strict_youtube(query: str):
    """Use cached known results or live lookup; never fabricate a fallback ID."""
    q = (query or "").strip()
    if not q:
        raise ValueError("media_query_required")
    low = q.lower()
    cached = getattr(server, "_YT_CACHE", {}).get(low)
    if cached:
        return {"videoId": cached, "url": f"https://www.youtube.com/watch?v={cached}", "title": q.upper()}

    # Reuse the existing live scraper, but reject its hard-coded fallback IDs.
    result = _ORIGINAL_YOUTUBE(q)
    fallback_ids = {"4xDzrJKXOOY", "jfKfPfyJRdk"}
    if not result or result.get("videoId") in fallback_ids:
        raise RuntimeError("media_result_not_verified: live YouTube result was not retrieved")
    return result


_ORIGINAL_IMAGE_GENERATION = server.resolve_image_generation
_ORIGINAL_YOUTUBE = server.resolve_youtube_search

# Disable synthetic infrastructure and optimistic media fallbacks.
server.ensure_sovereign_worker = ensure_real_workers_only
server.resolve_image_generation = _strict_image_generation
server.resolve_youtube_search = _strict_youtube
server.GPU_MARKETPLACE_TIERS = []

_original_dispatch = server.dispatch


def _truthful_dispatch(method, params):
    if method == "GetGpuMarketplace":
        stats = server.get_worker_status_counts()
        return {
            "tiers": [],
            "activeRentals": 0,
            "onlineWorkers": stats["onlineWorkers"],
            "registeredWorkers": stats["registeredWorkers"],
            "status": "NO_MARKETPLACE_CONFIGURED",
            "message": "No GPU rental inventory is currently configured. Runtime reports only real registered workers.",
        }
    if method == "RentGpuNode":
        raise ValueError("gpu_rental_not_configured")
    if method == "ExecuteComputeTask":
        worker = server.select_worker("gpu")
        if not worker:
            raise RuntimeError("compute_worker_not_available: no verified online GPU worker is registered")
    return _original_dispatch(method, params)


server.dispatch = _truthful_dispatch
_remove_synthetic_workers()


if __name__ == "__main__":
    asyncio.run(server.main())
