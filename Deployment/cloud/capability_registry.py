"""Truthful runtime capability registry for Sarembok."""
from __future__ import annotations
import os
from typing import Any

RPC_CAPABILITIES = {
    'SarembokChat': ('dialogue', 'Interactive Sarembok dialogue through the configured provider fabric.'),
    'GetRuntimeInfo': ('runtime', 'Read-only runtime health and system counts.'),
    'GetConversationHistory': ('memory', 'Read conversation history for a session.'),
    'CreateAgent': ('agents', 'Register an agent in the runtime.'),
    'QueryAgentState': ('agents', 'Read registered agent state.'),
    'InjectPerception': ('perception', 'Inject perception events for a registered agent.'),
    'EvaluateDecision': ('governance', 'Evaluate a decision through the runtime policy boundary.'),
    'GetCognitiveScorecard': ('evaluation', 'Read the runtime cognitive scorecard.'),
    'QueryWorldModel': ('world-model', 'Query the current world-model surface.'),
    'CreateDelegation': ('agents', 'Create an agent delegation record.'),
    'GetAuditTrail': ('governance', 'Read an agent audit trail.'),
    'SendMessage': ('messaging', 'Send a message to a registered agent.'),
    'GetEvents': ('events', 'Read agent events.'),
    'GetMetrics': ('observability', 'Read agent metrics.'),
    'RestoreState': ('persistence', 'Record a state-restore operation.'),
    'RegisterWorker': ('compute', 'Register a compute worker.'),
    'ListWorkers': ('compute', 'List registered workers and their liveness.'),
    'Heartbeat': ('compute', 'Update a worker heartbeat.'),
    'CreateTask': ('scheduler', 'Create a scheduled compute task.'),
    'ClaimTask': ('scheduler', 'Claim a queued task on an eligible worker.'),
    'CompleteTask': ('scheduler', 'Complete a running worker task.'),
    'FailTask': ('scheduler', 'Fail or retry a worker task.'),
    'RuntimeInfo': ('runtime', 'Read the extended runtime information surface.'),
    'ListProjects': ('projects', 'List runtime projects.'),
    'CreateProject': ('projects', 'Create a runtime project.'),
}

class CapabilityRegistry:
    def snapshot(self, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        providers = []
        for name, key, model in [('OpenAI','OPENAI_API_KEY',os.getenv('LLM_MODEL','gpt-5-mini')),('OpenRouter','OPENROUTER_API_KEY',os.getenv('OPENROUTER_MODEL','openai/gpt-oss-120b')),('Groq','GROQ_API_KEY',os.getenv('GROQ_MODEL','openai/gpt-oss-120b')),('Gemini','GEMINI_API_KEY',os.getenv('GEMINI_MODEL','gemini-3.8-flash')),('Custom','LLM_ENDPOINT_URL',os.getenv('LLM_MODEL','custom'))]:
            if os.getenv(key): providers.append({'name': name, 'model': model, 'configured': True})
        return {'registryVersion':'1.0', 'capabilities':[{'method':m,'domain':d,'description':desc,'enabled':True} for m,(d,desc) in RPC_CAPABILITIES.items()], 'providers':providers, 'runtime':runtime_state or {}}
