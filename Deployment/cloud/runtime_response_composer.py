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


import re


def _normalize_prompt_intent(prompt: str) -> str:
    """Normalize user prompt for robust intent matching: strip punctuation, lowercase, resolve typos/slang."""
    text = (prompt or "").strip().lower()
    # Remove apostrophes directly so "what's" -> "whats", "it's" -> "its"
    text = text.replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    # Common speech-to-text / typing shortcuts and typos:
    text = re.sub(r"\b(wht|wat|waht|wt)\b", "what", text)
    text = re.sub(r"\bwhats\b", "what is", text)
    text = re.sub(r"\bwhois\b", "who is", text)
    text = re.sub(r"\bu\b", "you", text)
    text = re.sub(r"\bur\b", "your", text)
    text = re.sub(r"\br\b", "are", text)
    text = re.sub(r"\bsys\b", "system", text)
    return " ".join(text.split())


def is_limitation_query(prompt: str) -> bool:
    """Identify questions about Sarembok's operational boundaries, constraints, and limitations."""
    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False

    limitation_exact = {
        "what cant it do",
        "what cant you do",
        "what cant this do",
        "what cant be done",
        "what can it not do",
        "what can you not do",
        "what can this not do",
        "what can not be done",
        "what is it not able to do",
        "what are you not able to do",
        "what are you unable to do",
        "what is it unable to do",
        "what are the limitations",
        "what are your limitations",
        "what are its limitations",
        "what limitations",
        "limitations",
        "system limitations",
        "runtime limitations",
        "what are the constraints",
        "what are your constraints",
        "what are its constraints",
        "constraints",
        "what are the boundaries",
        "operational boundaries",
        "what does it not support",
        "what do you not support",
        "what are you not capable of",
        "what is it not capable of",
    }
    if norm in limitation_exact:
        return True

    markers = (
        "what cant it do",
        "what cant you do",
        "what cant this do",
        "what cant be done",
        "what can it not do",
        "what can you not do",
        "what can this not do",
        "what can not be done",
        "what is it not able to do",
        "what are you not able to do",
        "what are you unable to do",
        "what is it unable to do",
        "what are the limitations",
        "what are your limitations",
        "what are its limitations",
        "system limitations",
        "runtime limitations",
        "what are the constraints",
        "what are your constraints",
        "what are its constraints",
        "operational boundaries",
        "what does it not support",
        "what do you not support",
        "what are you not capable of",
        "what is it not capable of",
    )
    return any(marker in norm for marker in markers)


def is_capability_query(prompt: str) -> bool:
    """Identify questions inquiring what Sarembok can do or its supported features."""
    if is_limitation_query(prompt):
        return False

    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False
    if norm in ("help", "commands", "features", "capabilities"):
        return True

    capability_exact = {
        "what can you do",
        "what can it do",
        "what can this do",
        "what can be done",
        "what can sarembok do",
        "what can the system do",
        "what does it do",
        "what does this do",
        "what do you do",
        "what are you able to do",
        "what is it able to do",
        "what is this able to do",
        "what is this capable of",
        "what are your capabilities",
        "what are its capabilities",
        "what capabilities",
        "what are your features",
        "what are its features",
        "what features",
        "how can you help",
        "how can it help",
        "how does it work",
        "how do you work",
        "what commands",
        "what can i ask",
        "show capabilities",
        "list capabilities",
    }
    if norm in capability_exact:
        return True

    markers = (
        "what can you do",
        "what can it do",
        "what can this do",
        "what can be done",
        "what does it do",
        "what does this do",
        "what do you do",
        "what are you able to do",
        "what is it able to do",
        "what is this able to do",
        "what is this capable of",
        "what can sarembok do",
        "what can the system do",
        "what are your capabilities",
        "what capabilities",
        "what are its capabilities",
        "what are your features",
        "what features",
        "what are its features",
        "how can you help",
        "how can it help",
        "how does it work",
        "how do you work",
        "what do you support",
        "what does it support",
        "what commands",
        "what can i ask",
        "show capabilities",
        "list capabilities",
    )
    return any(marker in norm for marker in markers)


def is_identity_query(prompt: str) -> bool:
    """Identify questions about Sarembok's identity or platform architecture."""
    # Capability queries take precedence (e.g., "what can this do" is capability, not identity)
    if is_capability_query(prompt):
        return False

    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False

    identity_exact = {
        "what is this",
        "what is this thing",
        "what is this platform",
        "what is this system",
        "what is this app",
        "what is this software",
        "what is this site",
        "what is this place",
        "what is this environment",
        "what system is this",
        "what platform is this",
        "what app is this",
        "what software is this",
        "what site is this",
        "what system are you",
        "what system am i using",
        "what is sarembok",
        "who is sarembok",
        "who are you",
        "what are you",
        "what is your name",
        "tell me about yourself",
        "what is your identity",
        "identify yourself",
    }
    if norm in identity_exact:
        return True

    markers = (
        "what system is this",
        "what is this system",
        "what system are you",
        "what system am i using",
        "what is this platform",
        "what platform is this",
        "what is this app",
        "what app is this",
        "what is this software",
        "what software is this",
        "what is this site",
        "what site is this",
        "what is this environment",
        "what is sarembok",
        "who is sarembok",
        "who are you",
        "what are you",
        "what is your name",
        "tell me about yourself",
        "what is your identity",
        "identify yourself",
        "what is this",
    )
    return any(marker in norm for marker in markers)


def render_capabilities(
    snapshot: dict[str, Any] | None = None,
    capabilities: dict[str, Any] | None = None,
) -> str:
    """Produce an authoritative summary of Sarembok VE capabilities and modalities."""
    workers_cnt = 0
    gpu_cnt = 0
    mem_entries = 0
    if snapshot:
        workers = snapshot.get("workers") or {}
        workers_cnt = workers.get("online", 0)
        compute = snapshot.get("compute") or {}
        gpu_cnt = compute.get("onlineGpuWorkers", 0)
        memory = snapshot.get("memory") or {}
        mem_entries = memory.get("entries", 0)

    return "\n".join([
        "### ⚡ SAREMBOK VE · SOVEREIGN CAPABILITIES",
        "",
        "I am **Sarembok VE**, an autonomous AI computing environment and multimodal runtime. Here are the core capabilities available to you right now:",
        "",
        "1. 🎵 **Universal Media & Audio Streaming**",
        "   - Play songs, comedy sets, live news broadcasts (e.g. BBC News), podcasts, or background beats directly in the chat with dedicated pop-out window support.",
        "   - *Directives:* `play kevin hart`, `play bbc news`, `play richard pryor`, or `play synthwave`.",
        "",
        "2. 🎙️ **Duplex Live Voice & Hands-Free Conversation**",
        "   - Real-time two-way spoken conversation with natural speech synthesis, instant barge-in, and speech recognition.",
        "   - Click **Live Conversation** or the microphone icon in the input bar to talk.",
        "",
        "3. 🌐 **Real-Time Intelligence & World Clock**",
        "   - Live web search, breaking news retrieval, and authoritative system clock / calendar verifications.",
        "   - *Directives:* `what time is it`, `latest tech news`, or `current market updates`.",
        "",
        "4. 💻 **Full-Stack Autonomous Code Synthesis**",
        "   - Architectural planning, code generation, refactoring, and debugging across Python, JavaScript, CSS, SQL, Docker, and shell.",
        "",
        "5. 🧠 **Persistent Long-Term Memory Recall**",
        f"   - Continuous knowledge persistence with SQLite-WAL memory ({mem_entries} stored entries across sessions).",
        "",
        "6. 🤖 **Multi-Agent Orchestration & Cloud Tasks**",
        f"   - Distributed task dispatching across {workers_cnt} active compute workers ({gpu_cnt} GPU acceleration nodes) with background agent lifecycles.",
        "",
        "7. 🎨 **Frontier Image Generation & Visual Synthesis**",
        "   - High-fidelity 1024x1024 visual generation powered by FLUX.1 and sovereign GPU Tensor Core acceleration.",
        "   - *Directives:* `generate an image of a cybernetic neural hub in neo-tokyo` or `draw an astronaut on mars`.",
        "",
        "Type or speak any instruction to begin!"
    ])


def render_limitations(snapshot: dict[str, Any] | None = None) -> str:
    """Produce an authoritative, engineering-grade statement of Sarembok VE's architectural boundaries."""
    return "\n".join([
        "### 🛡️ SAREMBOK VE · ARCHITECTURAL BOUNDARIES & OPERATIONAL CONSTRAINTS",
        "",
        "Sarembok VE operates as an enterprise-grade sovereign multimodal runtime and autonomous agent matrix. By architectural design and safety policy, several explicit boundaries are strictly enforced:",
        "",
        "1. **Containerized Sandbox Isolation**",
        "   - Autonomous code synthesis, terminal execution, and worker pipelines execute strictly inside isolated containerized sandboxes.",
        "   - Sarembok cannot access or mutate the underlying host OS kernel, unauthorized local network subnets, or host filesystems beyond provisioned volume mounts.",
        "",
        "2. **Cryptographic Authorization & Human Guardrails**",
        "   - High-impact operations—including cloud infrastructure deletion, unverified payment/billing transactions, or destructive production database drops—require explicit cryptographic API tokens and human confirmation.",
        "   - Sarembok will not execute irreversible destructive actions autonomously.",
        "",
        "3. **Sovereign Ground Truth vs. Speculative Hallucination**",
        "   - Real-time telemetry, worker node state, GPU inventory, and persistent memory metrics are strictly read from live Runtime Authority, not inferred or invented.",
        "   - Sarembok refuses to invent false worker counts or claim non-existent hardware resources.",
        "",
        "4. **Air-Gapped & Private Intranet Boundaries**",
        "   - Sarembok cannot access private internal enterprise networks, firewalled intranets, or air-gapped systems without explicit VPN tunnels, WireGuard configurations, or pre-registered authentication bridges.",
        "",
        "5. **Physical World Actuation**",
        "   - Sarembok does not possess direct physical actuators, robotics control, or biometric interception capabilities. Operations are bounded to compute, networking, audio/visual media, and software interfaces.",
        "",
        "6. **Deterministic Capacity & Quotas**",
        "   - Multimodal generation (e.g., FLUX.1 4K visual synthesis, parallel agent clustering) is strictly governed by provisioned cluster VRAM and GPU worker nodes to guarantee deterministic system stability without resource starvation.",
    ])


def is_self_state_query(prompt: str) -> bool:
    """Identify questions whose answer should be grounded directly in runtime state."""
    if is_identity_query(prompt) or is_capability_query(prompt) or is_limitation_query(prompt):
        return True

    text = (prompt or "").strip().lower()

    markers = (
        "what is your status",
        "runtime status",
        "how many workers",
        "how many agents",
        "how much memory",
        "what providers",
        "what provider",

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
