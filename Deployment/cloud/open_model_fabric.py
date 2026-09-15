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


def _selected_open_model(get_open_model, get_open_models) -> str:
    requested = os.getenv("SAREMBOK_OPEN_MODEL", "openai/gpt-oss-120b").strip()
    if requested and get_open_model(requested):
        return requested
    models = get_open_models("general")
    return models[0].model_id if models else "openai/gpt-oss-120b"


def install() -> None:
    try:
        from open_model_registry import get_open_model, get_open_models, local_model_ids
        import provider_router
    except Exception:
        return

    router_cls = provider_router.ProviderRouter
    if getattr(router_cls, "_sarembok_open_model_fabric", False):
        return

    original_configured = router_cls.configured
    original_metrics = router_cls.metrics

    def configured(self, requested_model: str | None = None, dynamic_key: str | None = None):
        # A caller-supplied model always wins. A user-supplied dynamic key also
        # retains its provider-native model default; only the normal runtime
        # path receives the open-model-first default.
        selected = requested_model
        if selected is None and dynamic_key is None:
            selected = _selected_open_model(get_open_model, get_open_models)
        return original_configured(self, requested_model=selected, dynamic_key=dynamic_key)

    def metrics(self) -> dict[str, Any]:
        result = original_metrics(self)
        selected = _selected_open_model(get_open_model, get_open_models)
        spec = get_open_model(selected)
        result["openModelFabric"] = {
            "enabled": True,
            "principle": "WE DON'T BUY IT. WE BUILD IT.",
            "defaultModel": selected,
            "defaultModelRegistered": spec is not None,
            "defaultModelLocal": selected in local_model_ids(),
            "openModelCount": len(get_open_models()),
        }
        return result

    router_cls.configured = configured
    router_cls.metrics = metrics
    router_cls._sarembok_open_model_fabric = True
