# Sarembok Scheduler V2 — Production Baseline

**Baseline status:** FROZEN / PRODUCTION VALIDATED  
**Validation date:** 2026-08-12  
**Public endpoint:** `wss://sarembok.com/`

## Acceptance Result

Scheduler V2 passed the complete public production lifecycle through the real WSS/TLS edge path.

- TLS/WSS: PASS
- Caddy / edge routing: PASS
- Runtime reachability: PASS
- JSON-RPC 2.0: PASS
- Application authentication: PASS (`params.authToken`)
- RegisterWorker: PASS
- Heartbeat: PASS
- ScheduleCompute: PASS
- Worker assignment: PASS
- ClaimTask: PASS
- `active_tasks`: `0 -> 1` PASS
- CompleteTask: PASS
- `active_tasks`: `1 -> 0` PASS
- Task lifecycle: `QUEUED -> RUNNING -> COMPLETED` PASS
- SQLite persistence: PASS
- Test worker cleanup: PASS

## Production State

Runtime image was rebuilt and recreated from the Scheduler V2 source. The running container was verified healthy, and the production image contained the expected scheduler and heartbeat RPC implementations.

The live worker schema includes:

- `worker_id`
- `capabilities`
- `gpu_vendor`
- `gpu_model`
- `vram_mb`
- `cuda_version`
- `available_memory_mb`
- `supported_models`
- `latency_ms`
- `status`
- `last_heartbeat`
- `active_tasks INTEGER NOT NULL DEFAULT 0`

The schema migration was executed against the live runtime SQLite database and verified successfully.

## Frozen Contract

Scheduler V2 is now a compatibility baseline. Do not modify its RPC contract or task-state semantics while implementing the next worker layer unless a deliberate versioned change is required.

Current RPC surface:

```text
RegisterWorker
Heartbeat
ScheduleCompute
ClaimTask
CompleteTask
```

Authentication contract:

```text
params.authToken
```

Task state contract:

```text
QUEUED -> RUNNING -> COMPLETED
```

Worker concurrency accounting:

```text
active_tasks: 0 -> 1 -> 0
```

## Next Build Target

Move directly to the real worker integration layer:

1. Persistent WSS worker client.
2. Authenticated `RegisterWorker`.
3. Periodic `Heartbeat`.
4. Work polling/dispatch.
5. `ClaimTask`.
6. Actual workload execution.
7. `CompleteTask`.
8. Reconnect and re-registration after connection loss.
9. Worker capability/GPU telemetry reporting.

Scheduler V2 remains frozen while this layer is built around the established production contract.
