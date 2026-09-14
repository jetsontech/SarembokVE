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


def spoken_text(text: str, max_chars: int = 1200) -> str:
    """Convert a rendered SarembokVE response into natural speech text.

    The visual response is deliberately left unchanged. This function removes
    presentation-only Markdown, rich directives, URLs, table syntax, and emoji
    so TTS receives readable prose rather than formatting tokens.
    """
    import unicodedata

    if not text:
        return ""

    s = str(text)

    # Remove rich-content blocks from spoken output.
    s = re.sub(
        r":::"
        r"(?:card|video|audio|doc|pdf|music|tasks)"
        r"[^\n]*\n?"
        r"[\s\S]*?"
        r":::",
        " ",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r":::reveal[^\n]*\n?([\s\S]*?):::",
        r" Solution: \1 ",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r":::[^\n]*", " ", s)

    # Remove fenced code blocks from speech.
    s = re.sub(r"```[\s\S]*?```", " Code block omitted. ", s)

    # Remove Markdown table separator rows.
    s = re.sub(
        r"(?m)^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$",
        " ",
        s,
    )

    # Convert table rows to readable sentences.
    table_lines = []
    for line in s.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [
                re.sub(r"[*_`~]", "", cell.strip())
                for cell in stripped.strip("|").split("|")
            ]
            cells = [c for c in cells if c]
            if cells:
                table_lines.append("; ".join(cells) + ".")
        else:
            table_lines.append(line)

    s = "\n".join(table_lines)

    # Remove Markdown links while preserving visible text.
    s = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", s)

    # Drop raw URLs. They are not useful for normal TTS.
    s = re.sub(r"https?://\S+", " ", s)

    # Remove LaTeX delimiters but retain the expression text.
    s = re.sub(r"\\\[([\s\S]*?)\\\]", r" \1 ", s)
    s = re.sub(r"\\\(([\s\S]*?)\\\)", r" \1 ", s)
    s = re.sub(r"\$\$([\s\S]*?)\$\$", r" \1 ", s)
    s = re.sub(r"\$([^$]+)\$", r" \1 ", s)

    # Markdown headings, emphasis, inline code, blockquotes.
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"__(.*?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.*?)(?<!\*)\*(?!\*)", r"\1", s)
    s = re.sub(r"(?<!_)_(?!\s)(.*?)(?<!_)_(?!_)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"(?m)^\s*>\s?", "", s)

    # Turn list markers into natural pauses.
    s = re.sub(r"(?m)^\s*[-*+]\s+", " ", s)
    s = re.sub(r"(?m)^\s*\d+[.)]\s+", " ", s)

    # Remove remaining Markdown/table punctuation that should never be spoken.
    s = s.replace("|", " ")
    s = s.replace("```", " ")
    s = s.replace(":::", " ")
    s = s.replace("\\", " ")

    # Remove emoji and symbol glyphs while retaining normal letters, numbers,
    # punctuation, whitespace, and useful mathematical text.
    s = "".join(
        ch
        for ch in s
        if not unicodedata.category(ch).startswith("S")
    )

    # Normalize whitespace and line boundaries.
    s = re.sub(r"\s+", " ", s).strip()

    # Avoid ending mid-word.
    if len(s) > max_chars:
        s = s[:max_chars]
        cut = s.rfind(" ")
        if cut > max_chars - 120:
            s = s[:cut]

    return s

def is_platform_purpose_query(prompt: str) -> bool:
    """Identify questions asking what SarembokVE is, why it exists, or its platform purpose."""
    norm = _normalize_prompt_intent(prompt)
    if not norm:
        return False

    markers = (
        "what is sarembokve",
        "what is sarembok ve",
        "what is the purpose of sarembok",
        "what is the purpose of sarembok ve",
        "what is the purpose of sarembokve",
        "what is saremboks purpose",
        "what is sarembokve for",
        "why does sarembok exist",
        "why was sarembok built",
        "what is sarembok built for",
        "what is the platform purpose",
        "explain the platform purpose",
        "explain saremboks platform purpose",
        "explain sarembokves platform purpose",
        "explain sarembokve platform purpose",
        "tell me about sarembokve",
        "tell me about sarembok ve",
        "describe sarembokve",
        "describe sarembok ve",
    )
    return any(marker in norm for marker in markers)


def render_platform_purpose(snapshot: dict[str, Any]) -> str:
    """Deterministic platform-purpose response grounded in observed runtime architecture."""
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    compute = snapshot.get("compute") or {}
    memory = snapshot.get("memory") or {}
    scheduler = snapshot.get("scheduler") or {}
    provider = snapshot.get("provider") or {}

    online_workers = int(workers.get("online", 0) or 0)
    online_agents = int(agents.get("online", 0) or 0)
    gpu_workers = int(compute.get("onlineGpuWorkers", 0) or 0)
    memory_backend = str(memory.get("backend") or "unknown")
    memory_status = str(memory.get("status") or "unknown")
    scheduler_status = str(scheduler.get("status") or "unknown")

    configured = provider.get("configuredProviders") or []
    provider_names = []
    for item in configured:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name and name not in provider_names:
                provider_names.append(name)

    provider_text = ", ".join(provider_names) if provider_names else "none currently reported"

    return "\n".join([
        "## SarembokVE Platform Purpose",
        "",
        "SarembokVE is a cloud-first AI computing environment built around its own runtime rather than being only a chat interface.",
        "",
        "### Core purpose",
        "",
        "1. **Runtime-centered AI computing** — Provides a persistent execution layer for AI conversations, routing, task handling, and runtime services.",
        "2. **Provider abstraction** — Separates SarembokVE's runtime from individual upstream model providers, so provider/model selection is handled through the runtime's routing layer.",
        "3. **Persistent state and memory** — Uses a SQLite-WAL persistence layer for runtime state and memory rather than treating every interaction as an isolated request.",
        "4. **Agents, workers, and scheduling** — Provides infrastructure for agent lifecycle management, worker registration, task dispatch, and compute scheduling.",
        "5. **Multimodal interaction surface** — Exposes a browser-based interface for conversational, voice, visual, media, research, and other runtime capabilities where the corresponding service is enabled.",
        "",
        "### Current runtime snapshot",
        "",
        f"- Online workers: **{online_workers}**",
        f"- Online agents: **{online_agents}**",
        f"- Online GPU workers: **{gpu_workers}**",
        f"- Persistent memory: **{memory_backend} · {memory_status}**",
        f"- Scheduler: **{scheduler_status}**",
        f"- Configured provider entries: **{provider_text}**",
        "",
        "### SarembokVE vs. a basic LLM API",
        "",
        "| Area | SarembokVE | Basic LLM API |",
        "|---|---|---|",
        "| Runtime | Persistent application runtime | Request/response service |",
        "| State | SQLite-WAL runtime state and memory | Usually application-managed |",
        "| Providers | Runtime-level provider routing | Usually tied to one API surface |",
        "| Agents / tasks | Worker, agent, and scheduler substrate | Usually external orchestration |",
        "| Interface | Browser UI with multiple interaction surfaces | Usually API or basic chat UI |",
        "",
        "This description distinguishes SarembokVE's architecture from capabilities that may exist in upstream providers or future infrastructure."
    ])


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
    """Produce a runtime-grounded capability summary without synthetic claims."""
    snapshot = snapshot or {}

    runtime = snapshot.get("runtime") or {}
    workers = snapshot.get("workers") or {}
    agents = snapshot.get("agents") or {}
    compute = snapshot.get("compute") or {}
    memory = snapshot.get("memory") or {}
    scheduler = snapshot.get("scheduler") or {}
    provider = snapshot.get("provider") or {}

    configured = _provider_entries(snapshot)
    enabled_methods = []
    if capabilities:
        enabled_methods = [
            str(item.get("method"))
            for item in capabilities.get("capabilities", [])
            if isinstance(item, dict) and item.get("enabled") and item.get("method")
        ]

    lines = [
        "## SarembokVE · Current Capabilities",
        "",
        "The following describes capabilities visible from the current runtime and application configuration. It does not claim resources or upstream features that are not currently verified.",
        "",
        "### Runtime",
        f"- Status: **{runtime.get('status', 'unknown')}**",
        f"- Workers online: **{workers.get('online', 0)}**",
        f"- Agents online: **{agents.get('online', 0)}**",
        f"- GPU workers online: **{compute.get('onlineGpuWorkers', 0)}**",
        f"- Persistent memory: **{memory.get('backend', 'unknown')} · {memory.get('status', 'unknown')}**",
        f"- Scheduler: **{scheduler.get('status', 'unknown')}**",
        "",
        "### Configured providers",
    ]

    if configured:
        for item in configured:
            lines.append(
                f"- **{item['name']}** · `{item['model']}` · `{item['api']}`"
            )
    else:
        lines.append("- None currently reported by Runtime Authority.")

    if enabled_methods:
        lines.extend([
            "",
            "### Enabled runtime operations",
            *[f"- `{method}`" for method in enabled_methods],
        ])

    lines.extend([
        "",
        "SarembokVE should only describe a specific external service, GPU resource, model, research source, or integration as available when the runtime has verified or configured it.",
    ])

    return "\n".join(lines)


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
    if is_platform_purpose_query(prompt) or is_identity_query(prompt) or is_capability_query(prompt) or is_limitation_query(prompt):
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
        "prune workers",
        "cleanup workers",
        "clean workers",
        "clear offline workers",
        "prune offline workers",
    )

    return any(marker in text for marker in markers)


def is_worker_prune_query(prompt: str) -> bool:
    """Identify commands to prune offline or zombie compute workers."""
    norm = _normalize_prompt_intent(prompt)
    prune_markers = (
        "prune workers",
        "prune worker",
        "cleanup workers",
        "clean workers",
        "clear offline workers",
        "prune offline workers",
        "purge offline workers",
        "reset workers",
        "reset worker registry",
    )
    return any(m in norm for m in prune_markers)


def render_identity(snapshot: dict[str, Any]) -> str:
    """Produce an authoritative, deterministic identity profile from observed runtime state."""
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

    workers_online = workers.get("online", 0)
    workers_reg = workers.get("registered", 0)
    workers_stale = workers.get("stale", 0)
    workers_offline = workers.get("offline", 0)

    if workers_reg <= workers_online:
        worker_cluster = f"{workers_online} online worker{'s' if workers_online != 1 else ''}"
    else:
        worker_cluster = f"{workers_online} online worker{'s' if workers_online != 1 else ''} ({workers_reg} registered slots: {workers_stale} stale, {workers_offline} offline)"

    caps = compute.get("onlineWorkerCapabilities") or []
    caps_str = ", ".join(caps) if isinstance(caps, list) else str(caps)

    return "\n".join([
        "### ⚡ SAREMBOK VE · SOVEREIGN AI COMPUTING RUNTIME",
        "",
        "I am **Sarembok VE**, an autonomous multimodal computing environment and sovereign AI runtime.",
        "",
        "**Runtime Telemetry & State:**",
        f"- **Status & Service:** `{runtime.get('status', 'ONLINE')}` on `{runtime.get('service', 'sarembok-ve-cloud-runtime')}`",
        f"- **Compute Fleet:** **{worker_cluster}**, and **{agents.get('registered', 0)} registered agents**.",
        f"- **GPU Acceleration:** **{compute.get('onlineGpuWorkers', 0)}** active GPU tensor nodes.",
        f"- **Persistent Memory:** `{memory.get('status', 'ONLINE')}` ({memory.get('backend', 'sqlite-wal')}) with **{memory.get('entries', 0)} stored entries** across sessions.",
        f"- **Multimodal Capabilities:** Astra Vision & Screen Eye, Duplex Live Voice, Dynamic MCP Skills, `{caps_str}`.",
        f"- **Configured Model Providers:** **{provider_text}**.",
        "",
        "*Ready to execute duplex voice, computer vision, code synthesis, or multi-agent pipelines.*",
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
