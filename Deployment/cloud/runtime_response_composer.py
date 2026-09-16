"""Compose dialogue context from authoritative Sarembok runtime state.

The language model remains responsible for conversational wording, but live
platform facts are supplied by Runtime Authority rather than inferred from a
static prompt or UI labels.
"""
from __future__ import annotations

from typing import Any
import re


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
    return [f"- {item['name']}: model={item['model']}; api={item['api']}" for item in _provider_entries(snapshot)]


def build_runtime_context(snapshot: dict[str, Any], capabilities: dict[str, Any] | None = None) -> str:
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
    lines.append("Configured model providers and models:")
    lines.extend(providers or ["- none"])
    if capabilities:
        enabled = [item.get("method") for item in capabilities.get("capabilities", []) if isinstance(item, dict) and item.get("enabled")]
        lines.append(f"Registered runtime capabilities: {', '.join(enabled) if enabled else 'none'}")
    return "\n".join(lines)


def _normalize_prompt_intent(prompt: str) -> str:
    text = (prompt or "").strip().lower().replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\b(wht|wat|waht|wt)\b", "what", text)
    text = re.sub(r"\bwhats\b", "what is", text)
    text = re.sub(r"\bwhois\b", "who is", text)
    text = re.sub(r"\bu\b", "you", text)
    text = re.sub(r"\bur\b", "your", text)
    text = re.sub(r"\br\b", "are", text)
    text = re.sub(r"\bsys\b", "system", text)
    return " ".join(text.split())


def is_limitation_query(prompt: str) -> bool:
    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False
    markers = (
        "what cant it do", "what cant you do", "what can it not do", "what can you not do",
        "what are the limitations", "what are your limitations", "what limitations", "limitations",
        "system limitations", "runtime limitations", "what are the constraints", "constraints",
        "what are the boundaries", "operational boundaries", "what does it not support",
        "what do you not support", "what are you not capable of", "what is it not capable of",
    )
    return norm in set(markers) or any(marker in norm for marker in markers)


def is_capability_query(prompt: str) -> bool:
    if is_limitation_query(prompt):
        return False
    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False
    markers = (
        "what can you do", "what can it do", "what can this do", "what can be done", "what can sarembok do",
        "what does it do", "what does this do", "what do you do", "what are you able to do",
        "what is it able to do", "what is this able to do", "what is this capable of", "what are your capabilities",
        "what are its capabilities", "what capabilities", "what are your features", "what are its features",
        "what features", "how can you help", "how can it help", "how does it work", "how do you work",
        "what do you support", "what does it support", "what commands", "what can i ask", "show capabilities",
        "list capabilities", "help", "commands", "features", "capabilities",
    )
    return norm in set(markers) or any(marker in norm for marker in markers)


def is_identity_query(prompt: str) -> bool:
    if is_capability_query(prompt):
        return False
    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False
    markers = (
        "what is this", "what is this thing", "what is this platform", "what is this system", "what is this app",
        "what is this software", "what is this site", "what is this environment", "what system is this",
        "what platform is this", "what app is this", "what software is this", "what site is this",
        "what system are you", "what system am i using", "what is sarembok", "who is sarembok", "who are you",
        "what are you", "what is your name", "tell me about yourself", "what is your identity", "identify yourself",
    )
    return norm in set(markers) or any(marker in norm for marker in markers)


def render_capabilities(snapshot: dict[str, Any] | None = None, capabilities: dict[str, Any] | None = None) -> str:
    """Return a concise capability summary grounded in runtime state and avoid unsupported UI/hardware claims."""
    workers_cnt = 0
    gpu_cnt = 0
    mem_entries = 0
    if snapshot:
        workers = snapshot.get("workers") or {}
        workers_cnt = int(workers.get("online", 0) or 0)
        compute = snapshot.get("compute") or {}
        gpu_cnt = int(compute.get("onlineGpuWorkers", 0) or 0)
        memory = snapshot.get("memory") or {}
        mem_entries = int(memory.get("entries", 0) or 0)

    lines = [
        "### SAREMBOK VE · CAPABILITIES",
        "",
        "Sarembok VE is an AI-native computing environment with a live runtime, persistent state, model/provider routing, workers, tasks, memory, research, and extensible tools.",
        "",
        "**Available through the runtime**",
        "- **Dialogue & reasoning:** natural-language interaction through the configured model/provider fabric.",
        "- **Runtime operations:** inspect runtime health, worker state, task state, projects, events, and provider metrics.",
        f"- **Distributed compute:** {workers_cnt} online worker(s), including {gpu_cnt} currently recognized GPU worker(s) by Runtime Authority.",
        f"- **Persistent memory:** SQLite-WAL persistence with {mem_entries} current stored entr{'y' if mem_entries == 1 else 'ies'}.",
        "- **Agents & orchestration:** create agents, create/schedule tasks, delegate work, and track execution state.",
        "- **Browser/research surfaces:** public-page navigation, DOM rendering, screenshots, and runtime-supported web intelligence.",
        "- **MCP & skills:** registered runtime capabilities can be discovered through the MCP/skills surfaces; execution depends on the installed/configured handler and live service state.",
        "- **Visual generation:** image generation is available through the runtime's configured generation path when a live provider or eligible worker is operational.",
        "",
        "**Try a directive**",
        "- `show the current runtime status`
- `what models are available`
- `create an agent named Research`
- `schedule a compute task`
- `remember that ...`
- `generate an image of ...`",
        "",
        "Sarembok reports live operational state separately from capabilities that are implemented but not currently connected or provisioned.",
    ]
    return "\n".join(lines)


def render_limitations(snapshot: dict[str, Any] | None = None) -> str:
    return "\n".join([
        "### SAREMBOK VE · ARCHITECTURAL BOUNDARIES",
        "",
        "- Runtime state is reported from Runtime Authority rather than invented by the assistant.",
        "- High-impact administrative operations remain subject to authentication and runtime policy controls.",
        "- Worker/GPU capacity depends on live registered workers and fresh heartbeats.",
        "- External providers, MCP servers, browser integrations, and generation services are only operational when configured and reachable.",
        "- Local/private networks and host resources are not implicitly available through the public runtime.",
    ])


def is_self_state_query(prompt: str) -> bool:
    if is_identity_query(prompt) or is_capability_query(prompt) or is_limitation_query(prompt):
        return True
    text = (prompt or "").strip().lower()
    markers = (
        "what is your status", "runtime status", "how many workers", "how many agents", "how much memory",
        "what providers", "what provider", "what model is this", "what model are you", "what model do you use",
        "what model is running", "what model is active", "what models are available", "what other models",
        "which models are available", "which models can i use", "what llms are available", "available models",
        "configured models", "model availability",
    )
    return any(marker in text for marker in markers)


def render_model_inventory(snapshot: dict[str, Any] | None = None) -> str:
    entries = _provider_entries(snapshot or {})
    lines = ["### SAREMBOK VE · CONFIGURED MODEL PROVIDERS", ""]
    if not entries:
        lines.append("No model providers are currently exposed by Runtime Authority.")
    else:
        for item in entries:
            lines.append(f"- **{item['name']}** — `{item['model']}`")
    lines.append("")
    lines.append("Configuration is not the same as provider health or model availability at this exact moment.")
    return "\n".join(lines)
