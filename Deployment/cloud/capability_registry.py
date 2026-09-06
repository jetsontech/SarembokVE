"""Truthful runtime capability registry for Sarembok.

Capability state is deliberately separated from authorization and execution.
A registered capability means the runtime knows how to represent that class of
operation; the live snapshot reports whether the current deployment exposes it.
"""
from __future__ import annotations

import os
from typing import Any


RPC_CAPABILITIES = {
    "SarembokChat": ("dialogue", "Interactive Sarembok dialogue through the configured provider fabric."),
    "GetRuntimeInfo": ("runtime", "Read-only runtime health and system counts."),
    "GetCapabilities": ("capability-fabric", "Read the live capability, integration, authorization, and execution state."),
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
    "CreateTask": ("scheduler", "Create a scheduled compute task."),
    "ClaimTask": ("scheduler", "Claim a queued task on an eligible worker."),
    "CompleteTask": ("scheduler", "Complete a running worker task."),
    "FailTask": ("scheduler", "Fail or retry a worker task."),
    "RuntimeInfo": ("runtime", "Read the extended runtime information surface."),
    "ListProjects": ("projects", "List runtime projects."),
    "CreateProject": ("projects", "Create a runtime project."),
    "WebFetch": ("web", "Retrieve an authorized public HTTP/HTTPS resource for research or computation."),
    "WebSearch": ("web", "Discover public Web resources for research."),
    "Research": ("research", "Perform evidence-oriented research across Web-accessible sources."),
    "W3CResearch": ("standards", "Research W3C specifications and Web standards sources."),
}


class CapabilityRegistry:
    def snapshot(self, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        providers = []
        for name, key, model in [
            ("OpenAI", "OPENAI_API_KEY", os.getenv("LLM_MODEL", "gpt-5-mini")),
            ("OpenRouter", "OPENROUTER_API_KEY", os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")),
            ("Groq", "GROQ_API_KEY", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")),
            ("Gemini", "GEMINI_API_KEY", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")),
            ("Custom", "LLM_ENDPOINT_URL", os.getenv("LLM_MODEL", "custom")),
        ]:
            if os.getenv(key):
                providers.append({"name": name, "model": model, "configured": True})

        runtime = runtime_state or {}
        workers = runtime.get("workers") or {}
        memory = runtime.get("memory") or {}
        compute = runtime.get("compute") or {}
        scheduler = runtime.get("scheduler") or {}
        runtime_online = runtime.get("runtime", {}).get("status") == "ONLINE"
        web_enabled = os.getenv("SAREMBOK_WEB_ENABLED", "true").strip().lower() == "true"
        research_enabled = os.getenv("SAREMBOK_RESEARCH_ENABLED", "true").strip().lower() == "true"
        browser_enabled = os.getenv("SAREMBOK_BROWSER_ENABLED", "false").strip().lower() == "true"

        states = {
            "runtime": "ONLINE" if runtime_online else "UNAVAILABLE",
            "memory": str(memory.get("status") or "UNKNOWN"),
            "compute": "ONLINE" if workers.get("online", 0) else "UNAVAILABLE",
            "agents": "ONLINE" if (runtime.get("agents") or {}).get("registered", 0) else "READY",
            "scheduler": str(scheduler.get("status") or "UNKNOWN"),
            "web": "ENABLED" if web_enabled else "DISABLED",
            "research": "ENABLED" if research_enabled else "DISABLED",
            "standards": "ENABLED" if research_enabled else "DISABLED",
            "browser": "ENABLED" if browser_enabled else "NOT_CONFIGURED",
        }

        capabilities = []
        for method, (domain, description) in RPC_CAPABILITIES.items():
            if domain == "web":
                enabled = web_enabled
            elif domain in {"research", "standards"}:
                enabled = research_enabled
            else:
                enabled = True
            capabilities.append({
                "method": method,
                "domain": domain,
                "description": description,
                "enabled": enabled,
                "state": states.get(domain, "AVAILABLE"),
                "authorization": "separate-policy-boundary",
                "execution": "runtime-dispatch" if enabled else "not-enabled",
            })

        return {
            "registryVersion": "2.0",
            "lifecycle": ["DISCOVER", "CONNECT", "AUTHORIZE", "EXECUTE", "OBSERVE", "VERIFY", "REMEMBER"],
            "truthModel": ["capability", "integration", "authorization", "execution"],
            "capabilities": capabilities,
            "surfaces": [
                {"id": "web", "label": "WEB", "state": states["web"]},
                {"id": "research", "label": "RESEARCH", "state": states["research"]},
                {"id": "w3c", "label": "W3C / STANDARDS", "state": states["standards"]},
                {"id": "knowledge", "label": "KNOWLEDGE", "state": "ONLINE" if memory.get("status") == "ONLINE" else "DEGRADED"},
                {"id": "agents", "label": "AGENTS", "state": states["agents"]},
                {"id": "memory", "label": "MEMORY", "state": states["memory"]},
                {"id": "workers", "label": "WORKERS", "state": str(workers.get("online", 0))},
                {"id": "compute", "label": "COMPUTE", "state": states["compute"]},
                {"id": "browser", "label": "BROWSER", "state": states["browser"]},
                {"id": "apis", "label": "APIs", "state": "CONFIGURED" if providers else "NOT_CONFIGURED"},
            ],
            "providers": providers,
            "runtime": runtime.get("runtime") or {},
            "policy": {
                "authorizationRequired": True,
                "executionTruthRequired": True,
                "credentialSecretsExposed": False,
            },
        }
