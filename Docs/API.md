# Sarembok VE API Specification

## JSON-RPC 2.0 Protocol Standard

All RPC requests follow the standard JSON-RPC 2.0 envelope format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "Health",
  "params": {
    "authToken": "<YOUR_SAREMBOK_AUTH_TOKEN>"
  }
}
```

---

## Endpoint Reference

### System & Control Plane
* `Health`: System liveness check and summary metrics.
* `RuntimeInfo`: Process uptime, worker count, active session counters, storage status.
* `GetMetrics`: System reliability and cognitive score metrics.

### Worker Management
* `RegisterWorker`: Register a new GPU worker node with capabilities, GPU model, VRAM, and latency.
* `ListWorkers`: Query registered workers with optional capability/status filtering.
* `Heartbeat`: Refresh worker heartbeat timestamp and status (`ONLINE`, `BUSY`, `OFFLINE`).

### Autonomous Agents
* `CreateAgent`: Provision a new agent identity.
* `ListAgents`: List registered agents.
* `GetAgent`: Query agent details.
* `QueryAgentState`: Check agent cognitive lifecycle stage.
* `GetCognitiveScorecard`: Retrieve cognitive breakdown (perception, memory, reasoning, governance).

### Task & Compute Scheduler
* `ScheduleCompute`: Schedule a compute task on an available GPU worker.
* `CreateTask`: Create a custom task in the scheduler queue.
* `ListTasks`: Retrieve task queue with status filtering.
* `GetTask`: Fetch specific task status.
* `CancelTask`: Cancel an active or queued task.

### Digital Humans
* `CreateDigitalHumanSession`: Initialize an in-engine MetaHuman session.
* `ListDigitalHumanSessions`: Query active/past sessions.
* `GetDigitalHumanSession`: Retrieve specific session state.

### Messaging & Events
* `SendMessage`: Send message payload to an agent.
* `InjectPerception`: Inject perception data into agent loop.
* `EvaluateDecision`: Run decision through governance policy check.
* `GetEvents` / `ListEvents`: Query append-only audit trail with filtering.
* `GetAuditTrail`: Verify audit trail record count and integrity.
* `CreateDelegation`: Create sub-goal delegation between agents.
* `RestoreState`: Replay SQLite WAL entries to restore state.
