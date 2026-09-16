"""Authoritative runtime capability registry for Sarembok VE.

This registry describes software capabilities, but never promotes a capability
into a claim that hardware, credentials, or an external service is currently
available. Operational state must come from live runtime telemetry.
"""
from __future__ import annotations

import os
from typing import Any

RPC_CAPABILITIES = {
    "SarembokChat": ("dialogue", "Interactive Sarembok dialogue through the configured provider fabric."),
    "GetRuntimeInfo": ("runtime", "Read-only runtime health and system counts."),
    "GetConversationHistory": ("memory", "Read conversation history for a session."),
    "CreateAgent": ("agents", "Register an agent in the runtime."),
    "QueryAgentState": ("agents", "Read registered agent state."),
    "InjectPerception": ("perception", "Inject perception events for a registered agent."),
    "EvaluateDecision": ("governance", "Evaluate a decision through the runtime policy boundary."),
    "GetCognitiveScorecard": ("evaluation", "Read the runtime cognitive scorecard."),
    "QueryWorldModel": ("world-model", "Query the current world-model surface."),
    "CreateDelegation": ("agents", "Create an agent delegation record."),
    "GetAuditTrail": ("governance", "Read an agent audit trail."),
    "SendMessage": ("messaging", "Send a message to a registered agent."),
    "GetEvents": ("events", "Read agent events."),
    "GetMetrics": ("observability", "Read agent metrics."),
    "RestoreState": ("persistence", "Record a state-restore operation."),
    "RegisterWorker": ("compute", "Register a compute worker."),
    "ListWorkers": ("compute", "List registered workers and their liveness."),
    "Heartbeat": ("compute", "Update a worker heartbeat."),
    "PruneWorkers": ("compute", "Prune dead or offline compute workers from the registry."),
    "CreateTask": ("scheduler", "Create a scheduled compute task."),
    "ScheduleCompute": ("scheduler", "Schedule a compute task on eligible workers."),
    "ListTasks": ("scheduler", "List queued, running, or completed compute tasks."),
    "ClaimTask": ("scheduler", "Claim a queued task on an eligible worker."),
    "CompleteTask": ("scheduler", "Complete a running worker task."),
    "FailTask": ("scheduler", "Fail or retry a worker task."),
    "RuntimeInfo": ("runtime", "Read the extended runtime information surface."),
    "ListProjects": ("projects", "List runtime projects."),
    "CreateProject": ("projects", "Create a runtime project."),
    "BrowserNavigate": ("browser", "Navigate to a verified public URL and extract structured text."),
    "BrowserScreenshot": ("browser", "Capture a full-page or viewport screenshot of a public URL."),
    "BrowserRender": ("browser", "Render full-page DOM of a public URL using headless Chromium."),
    "CreateDigitalHumanSession": ("avatar", "Create an active digital human session."),
    "GetDigitalHumanSession": ("avatar", "Get digital human session status and voice profile."),
    "ListDigitalHumanSessions": ("avatar", "List all digital human sessions."),
    "CloseDigitalHumanSession": ("avatar", "Close an active digital human session."),
    "GenerateImage": ("frontier-vision", "Image generation capability; operational availability is determined by live provider/worker state."),
    "ExecuteComputeTask": ("compute", "Execute compute work on eligible registered workers."),
    "GetVisualEngineStatus": ("frontier-vision", "Read visual synthesis provider and worker status."),
}


def _provider_snapshot() -> list[dict[str, Any]]:
    """Return configured providers without implying that configuration means healthy."""
    providers: list[dict[str, Any]] = []
    candidates = [
        ("OpenAI", "OPENAI_API_KEY", "LLM_MODEL", "gpt-5-mini"),
        ("OpenRouter", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        ("Groq", "GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-120b"),
        ("Gemini", "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-3.6-flash"),
        ("Custom", "LLM_ENDPOINT_URL", "LLM_MODEL", "custom"),
    ]
    for name, key, model_key, default_model in candidates:
        configured = bool(os.getenv(key))
        if configured:
            providers.append({
                "name": name,
                "model": os.getenv(model_key, default_model),
                "configured": True,
                "status": "configured",
            })
    return providers


class CapabilityRegistry:
    def snapshot(self, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        runtime = runtime_state or {}
        return {
            "registryVersion": "2.0",
            "truthModel": "implemented_configured_operational",
            "capabilities": [
                {"method": m, "domain": d, "description": desc, "enabled": True}
                for m, (d, desc) in RPC_CAPABILITIES.items()
            ],
            "providers": _provider_snapshot(),
            "runtime": runtime,
        }
