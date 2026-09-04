"""Compose dialogue context from authoritative Sarembok runtime state.

The language model remains responsible for conversational wording, but live
platform facts are supplied by Runtime Authority rather than inferred from a
static prompt or UI labels.
"""
from __future__ import annotations

from typing import Any


def _provider_lines(snapshot: dict[str, Any]) -> list[str]:
    provider = snapshot.get("provider") or {}
    configured = provider.get("configuredProviders") or []
    lines = []
    for item in configured:
        if isinstance(item, dict):
            name = item.get("name", "unknown")
            model = item.get("model", "unknown")
            api = item.get("api", "unknown")
            lines.append(f"- {name}: model={model}; api={api}")
    return lines


def build_runtime_context(snapshot: dict[str, Any], capabilities: dict[str, Any] | None = None) -> str:
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
        "Never invent workers, agents, memory entries, tools, integrations, GPU capacity, or provider state.",
        f"Runtime: status={runtime.get('status')}; service={runtime.get('service')}; domain={runtime.get('domain')}; port={runtime.get('port')}",
        f"Workers: registered={workers.get('registered', 0)}; online={workers.get('online', 0)}; stale={workers.get('stale', 0)}; offline={workers.get('offline', 0)}",
        f"Agents: registered={agents.get('registered', 0)}; online={agents.get('online', 0)}",
        f"Compute: online_gpu_workers={compute.get('onlineGpuWorkers', 0)}; capabilities={','.join(compute.get('onlineWorkerCapabilities') or []) or 'none'}",
        f"Persistent memory: backend={memory.get('backend')}; status={memory.get('status')}; entries={memory.get('entries', 0)}; integrity={memory.get('integrity')}",
        f"Scheduler: status={scheduler.get('status')}; queue_depth={scheduler.get('queueDepth', 0)}; running={scheduler.get('running', 0)}; completed={scheduler.get('completed', 0)}; failed={scheduler.get('failed', 0)}",
    ]

    providers = _provider_lines(snapshot)
    if providers:
        lines.append("Configured model providers:")
        lines.extend(providers)
    else:
        lines.append("Configured model providers: none")

    if capabilities:
        enabled = [
            item.get("method")
            for item in capabilities.get("capabilities", [])
            if isinstance(item, dict) and item.get("enabled")
        ]
        lines.append(f"Registered runtime capabilities: {', '.join(enabled) if enabled else 'none'}")

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
        "what capabilities",
    )
    return any(marker in text for marker in markers)


def render_identity(snapshot: dict[str, Any]) -> str:
    """Produce a concise, deterministic self-description from observed state."""
    runtime = snapshot.get("runtime") or {}
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    memory = snapshot.get("memory") or {}
    compute = snapshot.get("compute") or {}
    provider = snapshot.get("provider") or {}

    provider_names = [
        str(item.get("name"))
        for item in provider.get("configuredProviders", [])
        if isinstance(item, dict) and item.get("name")
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
