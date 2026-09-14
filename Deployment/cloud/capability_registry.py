"""Truthful runtime capability registry for SarembokVE.

The registry describes contracts separately from live availability. UI and
model responses must not treat a declared capability as an active resource.
"""
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
    'PruneWorkers': ('compute', 'Prune dead or offline compute workers from the registry.'),
    'CreateTask': ('scheduler', 'Create a scheduled compute task.'),
    'ScheduleCompute': ('scheduler', 'Schedule a compute task on eligible workers.'),
    'ListTasks': ('scheduler', 'List queued, running, or completed compute tasks.'),
    'ClaimTask': ('scheduler', 'Claim a queued task on an eligible worker.'),
    'CompleteTask': ('scheduler', 'Complete a running worker task.'),
    'FailTask': ('scheduler', 'Fail or retry a worker task.'),
    'RuntimeInfo': ('runtime', 'Read the extended runtime information surface.'),
    'ListProjects': ('projects', 'List runtime projects.'),
    'CreateProject': ('projects', 'Create a runtime project.'),
    'BrowserNavigate': ('browser', 'Navigate to a verified public URL and extract structured text.'),
    'BrowserScreenshot': ('browser', 'Capture a screenshot of a public URL.'),
    'BrowserRender': ('browser', 'Render full-page DOM of a public URL.'),
    'CreateDigitalHumanSession': ('avatar', 'Create an active MetaHuman digital human session.'),
    'GetDigitalHumanSession': ('avatar', 'Get digital human session status.'),
    'ListDigitalHumanSessions': ('avatar', 'List digital human sessions.'),
    'CloseDigitalHumanSession': ('avatar', 'Close an active digital human session.'),
    'GenerateImage': ('frontier-vision', 'Generate imagery through a configured visual engine.'),
    'ExecuteComputeTask': ('compute', 'Execute compute on an eligible worker.'),
    'GetVisualEngineStatus': ('frontier-vision', 'Read visual engine health.'),
}


class CapabilityRegistry:
    def snapshot(self, runtime_state: dict[str, Any] | None = None) -> dict[str, Any]:
        runtime_state = runtime_state or {}
        workers = runtime_state.get('workers', {})
        online_workers = int(workers.get('online', 0) or 0)
        provider_configured = bool(runtime_state.get('provider', {}).get('configuredProviders'))
        capabilities = []
        for method, (domain, description) in RPC_CAPABILITIES.items():
            enabled = True
            available = True
            if domain == 'compute':
                available = online_workers > 0
            elif domain == 'frontier-vision':
                available = bool(runtime_state.get('compute', {}).get('onlineGpuWorkers', 0))
            elif domain == 'dialogue':
                available = provider_configured
            capabilities.append({
                'method': method,
                'domain': domain,
                'description': description,
                'declared': True,
                'enabled': enabled,
                'available': available,
                'executing': False,
            })
        return {
            'registryVersion': '2.0',
            'capabilities': capabilities,
            'providers': runtime_state.get('provider', {}).get('configuredProviders', []),
            'runtime': runtime_state,
        }
