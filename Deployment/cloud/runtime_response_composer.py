"""Authoritative response helpers for the Sarembok VE cloud runtime."""
from __future__ import annotations

import re
from typing import Any


def _provider_entries(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    configured = (snapshot.get("provider") or {}).get("configuredProviders") or []
    entries: list[dict[str, str]] = []
    for item in configured:
        if isinstance(item, dict):
            entries.append({
                "name": str(item.get("name") or "unknown"),
                "model": str(item.get("model") or "unknown"),
                "api": str(item.get("api") or "unknown"),
            })
    return entries


def _provider_lines(snapshot: dict[str, Any]) -> list[str]:
    return [f"- {p['name']}: model={p['model']}; api={p['api']}" for p in _provider_entries(snapshot)]


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
        "Runtime: status=%s; service=%s; domain=%s; port=%s" % (runtime.get("status"), runtime.get("service"), runtime.get("domain"), runtime.get("port")),
        "Workers: registered=%s; online=%s; stale=%s; offline=%s" % (workers.get("registered", 0), workers.get("online", 0), workers.get("stale", 0), workers.get("offline", 0)),
        "Agents: registered=%s; online=%s" % (agents.get("registered", 0), agents.get("online", 0)),
        "Compute: online_gpu_workers=%s; capabilities=%s" % (compute.get("onlineGpuWorkers", 0), ",".join(compute.get("onlineWorkerCapabilities") or []) or "none"),
        "Persistent memory: backend=%s; status=%s; entries=%s; integrity=%s" % (memory.get("backend"), memory.get("status"), memory.get("entries", 0), memory.get("integrity")),
        "Scheduler: status=%s; queue_depth=%s; running=%s; completed=%s; failed=%s" % (scheduler.get("status"), scheduler.get("queueDepth", 0), scheduler.get("running", 0), scheduler.get("completed", 0), scheduler.get("failed", 0)),
        "Configured model providers and models:",
    ]
    lines.extend(_provider_lines(snapshot) or ["- none"])
    if capabilities:
        enabled = [c.get("method") for c in capabilities.get("capabilities", []) if isinstance(c, dict) and c.get("enabled")]
        lines.append("Registered runtime capabilities: " + (", ".join(enabled) if enabled else "none"))
    return "\n".join(lines)


def _normalize_prompt_intent(prompt: str) -> str:
    text = (prompt or "").strip().lower().replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\b(wht|wat|waht|wt)\b", "what", text)
    text = re.sub(r"\bwhats\b", "what is", text)
    text = re.sub(r"\bwhois\b", "who is", text)
    text = re.sub(r"\bu\b", "you", text)
    text = re.sub(r"\bur\b", "your", text)
    return " ".join(text.split())


def is_limitation_query(prompt: str) -> bool:
    norm = _normalize_prompt_intent(prompt)
    markers = (
        "what cant it do", "what cant you do", "what can it not do", "what can you not do",
        "what are the limitations", "what are your limitations", "what limitations", "limitations",
        "system limitations", "runtime limitations", "what are the constraints", "constraints",
        "what are the boundaries", "operational boundaries", "what does it not support",
        "what do you not support", "what are you not capable of", "what is it not capable of",
    )
    return any(m in norm for m in markers)


def is_capability_query(prompt: str) -> bool:
    if is_limitation_query(prompt):
        return False
    norm = _normalize_prompt_intent(prompt)
    markers = (
        "help", "commands", "features", "capabilities", "what can you do", "what can it do", "what can this do",
        "what can be done", "what can sarembok do", "what can the system do", "what does it do", "what does this do",
        "what do you do", "what are you able to do", "what is it able to do", "what is this able to do",
        "what is this capable of", "what are your capabilities", "what are its capabilities", "what capabilities",
        "what are your features", "what are its features", "what features", "how can you help", "how can it help",
        "how does it work", "how do you work", "what do you support", "what does it support", "what commands",
        "what can i ask", "show capabilities", "list capabilities",
    )
    return any(m == norm or norm.startswith(m) for m in markers)


def is_identity_query(prompt: str) -> bool:
    if is_capability_query(prompt):
        return False
    norm = _normalize_prompt_intent(prompt)
    markers = (
        "what is this", "what is this platform", "what is this system", "what is this app", "what is this software",
        "what is this site", "what is this environment", "what system is this", "what platform is this",
        "what app is this", "what system are you", "what system am i using", "what is sarembok", "who is sarembok",
        "who are you", "what are you", "what is your name", "tell me about yourself", "what is your identity",
        "identify yourself",
    )
    return any(m == norm or norm.startswith(m) for m in markers)


def is_self_state_query(prompt: str) -> bool:
    if is_identity_query(prompt) or is_capability_query(prompt) or is_limitation_query(prompt):
        return True
    text = (prompt or "").strip().lower()
    markers = (
        "what is your status", "runtime status", "how many workers", "how many agents", "how much memory",
        "what providers", "what provider", "what model is this", "what model are you", "what model do you use",
        "what model is running", "what model is active", "what models are available", "what other models",
        "other models", "which models are available", "which models can i use", "what models can i use",
        "what llms are available", "what llms can i use", "what models are configured", "which models are configured",
        "model availability", "available models", "configured models",
    )
    return any(m in text for m in markers)


def is_worker_prune_query(prompt: str) -> bool:
    norm = _normalize_prompt_intent(prompt)
    return any(m in norm for m in (
        "prune workers", "prune worker", "cleanup workers", "clean workers", "clear offline workers",
        "prune offline workers", "purge offline workers", "reset workers", "reset worker registry",
    ))


def render_capabilities(snapshot: dict[str, Any] | None = None, capabilities: dict[str, Any] | None = None) -> str:
    workers = (snapshot or {}).get("workers") or {}
    compute = (snapshot or {}).get("compute") or {}
    memory = (snapshot or {}).get("memory") or {}
    workers_online = int(workers.get("online", 0) or 0)
    gpu_online = int(compute.get("onlineGpuWorkers", 0) or 0)
    memory_entries = int(memory.get("entries", 0) or 0)
    return "\n".join([
        "### SAREMBOK VE · CAPABILITIES",
        "",
        "Sarembok VE is an AI-native computing environment with a live runtime, persistent state, model/provider routing, workers, tasks, memory, research, and extensible tools.",
        "",
        "**Available through the runtime**",
        "- **Dialogue & reasoning:** interact through the configured model/provider fabric.",
        "- **Runtime operations:** inspect health, workers, tasks, projects, events, and provider metrics.",
        f"- **Distributed compute:** {workers_online} online worker(s); {gpu_online} currently recognized GPU worker(s) in Runtime Authority.",
        f"- **Persistent memory:** SQLite-WAL persistence with {memory_entries} current stored {('entry' if memory_entries == 1 else 'entries')}.",
        "- **Agents & orchestration:** create agents, create/schedule tasks, delegate work, and track execution state.",
        "- **Browser/research:** runtime-supported public-page navigation, DOM rendering, screenshots, and web intelligence.",
        "- **MCP & skills:** discover registered capabilities; execution depends on installed/configured handlers and live service state.",
        "- **Visual generation:** available when a live configured generation provider or eligible worker is operational.",
        "",
        "**Try:** `show the current runtime status`, `what models are available`, `create an agent named Research`, `schedule a compute task`, `remember that ...`, or `generate an image of ...`.",
    ])


def render_limitations(snapshot: dict[str, Any] | None = None) -> str:
    return "\n".join([
        "### SAREMBOK VE · ARCHITECTURAL BOUNDARIES",
        "",
        "- Runtime state is reported from Runtime Authority rather than invented.",
        "- High-impact administrative operations remain subject to authentication and runtime policy controls.",
        "- Worker/GPU capacity depends on live registered workers and fresh heartbeats.",
        "- External providers, MCP servers, browser integrations, and generation services are operational only when configured and reachable.",
        "- Local/private networks and host resources are not implicitly available through the public runtime.",
    ])


def render_identity(snapshot: dict[str, Any]) -> str:
    runtime = snapshot.get("runtime") or {}
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    memory = snapshot.get("memory") or {}
    compute = snapshot.get("compute") or {}
    providers = ", ".join(p["name"] for p in _provider_entries(snapshot)) or "none"
    return "\n".join([
        "### SAREMBOK VE · AI-NATIVE COMPUTING RUNTIME",
        "",
        "I am **Sarembok VE**, an AI-native computing environment and sovereign runtime.",
        "",
        "**Live runtime state**",
        f"- **Status:** `{runtime.get('status', 'UNKNOWN')}`",
        f"- **Service:** `{runtime.get('service', 'sarembok-ve-cloud-runtime')}`",
        f"- **Workers:** {workers.get('online', 0)} online / {workers.get('registered', 0)} registered",
        f"- **Agents:** {agents.get('online', 0)} online / {agents.get('registered', 0)} registered",
        f"- **GPU workers:** {compute.get('onlineGpuWorkers', 0)} recognized online",
        f"- **Persistent memory:** {memory.get('entries', 0)} stored entries via `{memory.get('backend', 'sqlite-wal')}`",
        f"- **Configured providers:** {providers}",
    ])


def render_model_inventory(snapshot: dict[str, Any]) -> str:
    entries = _provider_entries(snapshot)
    lines = ["### SAREMBOK VE · CONFIGURED MODEL PROVIDERS", ""]
    if entries:
        lines.extend(f"- **{p['name']}** — `{p['model']}`" for p in entries)
    else:
        lines.append("No model providers are currently exposed by Runtime Authority.")
    lines.extend(["", "Configured does not necessarily mean healthy or available at this exact moment."])
    return "\n".join(lines)
