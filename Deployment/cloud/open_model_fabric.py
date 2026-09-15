"""Runtime bridge for Sarembok's open-model-first provider fabric.

This module is imported by ``sitecustomize`` before the cloud runtime loads. It
keeps the existing ProviderRouter implementation intact while making the open
model registry an actual runtime decision layer rather than documentation only.

The bridge is fail-safe: if the registry cannot be loaded, the original router
behavior remains available.
"""
from __future__ import annotations

import os
from typing import Any


def install() -> None:
    try:
        from open_model_registry import get_open_model, get_open_models
        import provider_router
    except Exception:
        return

    router_cls = provider_router.ProviderRouter
    if getattr(router_cls, "_sarembok_open_model_fabric", False):
        return

    original_configured = router_cls.configured
    original_metrics = router_cls.metrics

    def configured(self, requested_model: str | None = None, dynamic_key: str | None = None):
        selected = requested_model
        if not selected:
            selected = os.getenv("SAREMBOK_OPEN_MODEL", "openai/gpt-oss-120b").strip() or None
        return original_configured(self, requested_model=selected, dynamic_key=dynamic_key)

    def metrics(self) -> dict[str, Any]:
        result = original_metrics(self)
        selected = os.getenv("SAREMBOK_OPEN_MODEL", "openai/gpt-oss-120b").strip()
        spec = get_open_model(selected)
        result["openModelFabric"] = {
            "enabled": True,
            "principle": "WE DON'T BUY IT. WE BUILD IT.",
            "defaultModel": selected,
            "defaultModelRegistered": spec is not None,
            "defaultModelLocal": selected in __import__("open_model_registry").local_model_ids(),
            "openModelCount": len(get_open_models()),
        }
        return result

    router_cls.configured = configured
    router_cls.metrics = metrics
    router_cls._sarembok_open_model_fabric = True
