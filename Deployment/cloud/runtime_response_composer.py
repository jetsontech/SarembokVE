"""Compose dialogue context from authoritative Sarembok runtime state.

The language model remains responsible for conversational wording, but live
platform facts are supplied by Runtime Authority rather than inferred from a
static prompt or UI labels.
"""
from __future__ import annotations

from typing import Any


def _provider_entries(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    provider = snapshot.get("provider") or {}
    configured = provider.get("configuredProviders") or []

    entries: list[dict[str, str]] = []

    for item in configured:
        if not isinstance(item, dict):
            continue

        entries.append({
            "name": str(item.get("name") or "unknown"),
            "model": str(item.get("model") or "unknown"),
            "api": str(item.get("api") or "unknown"),
        })

    return entries


def _provider_lines(snapshot: dict[str, Any]) -> list[str]:
    return [
        f"- {item['name']}: model={item['model']}; api={item['api']}"
        for item in _provider_entries(snapshot)
    ]


def build_runtime_context(
    snapshot: dict[str, Any],
    capabilities: dict[str, Any] | None = None,
) -> str:
    """Return a compact, model-facing representation of observed runtime facts."""
    runtime = snapshot.get("runtime") or {}
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    compute = snapshot.get("compute") or {}
    memory = snapshot.get("memory") or {}
    scheduler = snapshot.get("scheduler") or {}

    lines = [
        "AUTHORITATIVE SAREMBOK RUNTIME CONTEXT",
        "Use these facts as the source of truth for statements about Sarembok itself.",
        "Never invent workers, agents, memory entries, tools, integrations, GPU capacity, model availability, or provider state.",
        "Distinguish models configured on this Sarembok runtime from models merely offered by an upstream provider catalog.",
        f"Runtime: status={runtime.get('status')}; service={runtime.get('service')}; domain={runtime.get('domain')}; port={runtime.get('port')}",
        f"Workers: registered={workers.get('registered', 0)}; online={workers.get('online', 0)}; stale={workers.get('stale', 0)}; offline={workers.get('offline', 0)}",
        f"Agents: registered={agents.get('registered', 0)}; online={agents.get('online', 0)}",
        f"Compute: online_gpu_workers={compute.get('onlineGpuWorkers', 0)}; capabilities={','.join(compute.get('onlineWorkerCapabilities') or []) or 'none'}",
        f"Persistent memory: backend={memory.get('backend')}; status={memory.get('status')}; entries={memory.get('entries', 0)}; integrity={memory.get('integrity')}",
        f"Scheduler: status={scheduler.get('status')}; queue_depth={scheduler.get('queueDepth', 0)}; running={scheduler.get('running', 0)}; completed={scheduler.get('completed', 0)}; failed={scheduler.get('failed', 0)}",
    ]

    providers = _provider_lines(snapshot)

    if providers:
        lines.append("Configured model providers and models:")
        lines.extend(providers)
    else:
        lines.append("Configured model providers and models: none")

    if capabilities:
        enabled = [
            item.get("method")
            for item in capabilities.get("capabilities", [])
            if isinstance(item, dict) and item.get("enabled")
        ]

        lines.append(
            f"Registered runtime capabilities: "
            f"{', '.join(enabled) if enabled else 'none'}"
        )

    return "\n".join(lines)


def is_self_state_query(prompt: str) -> bool:
    """Identify questions whose answer should be grounded directly in runtime state."""
    text = (prompt or "").strip().lower()

    markers = (
        "what system is this",
        "what is this system",
        "what is sarembok",
        "who are you",
        "what are you",
        "what is your status",
        "runtime status",
        "how many workers",
        "how many agents",
        "how much memory",
        "what providers",
        "what provider",
        "what capabilities",

        # Model/provider state queries must never fall through to
        # general model knowledge.
        "what model is this",
        "what model are you",
        "what model do you use",
        "what model is running",
        "what model is active",
        "what model are you running",
        "what models are available",
        "what other models",
        "other models",
        "which models are available",
        "which models can i use",
        "what models can i use",
        "what llms are available",
        "what llms can i use",
        "what language models are available",
        "what language models can i use",
        "what models are configured",
        "which models are configured",
        "model availability",
        "available models",
        "configured models",
    )

    return any(marker in text for marker in markers)


def render_identity(snapshot: dict[str, Any]) -> str:
    """Produce a concise, deterministic self-description from observed state."""
    runtime = snapshot.get("runtime") or {}
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    memory = snapshot.get("memory") or {}
    compute = snapshot.get("compute") or {}

    provider_names = [
        item["name"]
        for item in _provider_entries(snapshot)
    ]

    provider_text = ", ".join(provider_names) if provider_names else "none"

    return "\n".join([
        "I am Sarembok VE, the Sarembok computing environment and AI runtime.",
        "",
        f"The live runtime is **{runtime.get('status', 'UNKNOWN')}** on `{runtime.get('service', 'unknown')}`.",
        f"It currently has **{workers.get('online', 0)} online workers** out of {workers.get('registered', 0)} registered, and **{agents.get('registered', 0)} registered agents**.",
        f"Persistent memory is **{memory.get('status', 'UNKNOWN')}** using `{memory.get('backend', 'unknown')}`, with **{memory.get('entries', 0)} stored entries**.",
        f"Online GPU workers: **{compute.get('onlineGpuWorkers', 0)}**. Runtime capabilities: `{', '.join(compute.get('onlineWorkerCapabilities') or []) or 'none'}`.",
        f"Configured model providers: **{provider_text}**.",
        "",
        "Those values come from the live Runtime Authority, not from a static UI label or a model assumption.",
    ])


def render_model_inventory(snapshot: dict[str, Any]) -> str:
    """Describe only models actually configured on the current Sarembok runtime."""
    entries = _provider_entries(snapshot)
    provider = snapshot.get("provider") or {}
    last_successful = provider.get("lastSuccessful") or {}

    lines = [
        "These are the language models currently configured on this Sarembok runtime:",
    ]

    if not entries:
        lines.append(
            "- None. No language-model provider is currently configured."
        )
    else:
        seen: set[tuple[str, str]] = set()

        for item in entries:
            key = (item["name"], item["model"])

            if key in seen:
                continue

            seen.add(key)

            lines.append(
                f"- **{item['model']}** via **{item['name']}** "
                f"({item['api']})"
            )

    active_provider = last_successful.get("provider")
    active_model = last_successful.get("model")

    if active_provider and active_model:
        lines.append("")
        lines.append(
            f"Most recently successful model: **{active_model}** "
            f"via **{active_provider}**."
        )

    lines.extend([
        "",
        "This inventory reflects Sarembok's configured runtime state. "
        "A provider may expose many additional models in its external catalog, "
        "but those are not claimed as Sarembok-available until Sarembok "
        "configures and validates them.",
    ])

    return "\n".join(lines)
