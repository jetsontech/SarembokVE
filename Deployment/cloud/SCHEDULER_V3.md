# Sarembok Cloud Scheduler V3

Scheduler V3 is layered on the frozen `cloud-scheduler-v2-production` checkpoint.

## Production controls

| Control | Default | Environment variable |
|---|---:|---|
| Worker heartbeat timeout | 90s | `SAREMBOK_WORKER_HEARTBEAT_TIMEOUT` |
| Task lease | 300s | `SAREMBOK_TASK_LEASE_SECONDS` |
| Retry delay | 5s | `SAREMBOK_TASK_RETRY_DELAY_SECONDS` |
| Maximum attempts | 3 | `SAREMBOK_TASK_MAX_ATTEMPTS` |

## Worker lifecycle

1. `RegisterWorkerV3`
2. `HeartbeatV3` every ~30 seconds
3. `ScheduleComputeV3`
4. `ClaimTaskV3`
5. `CompleteTaskV3` or `FailTask`
6. `WorkerOffline` when shutting down cleanly

Workers advertise `maxConcurrentTasks`. Placement considers active + queued work, capability, model compatibility, latency, and available memory.

## Recovery

The runtime reaper runs every five seconds. It marks workers stale after the heartbeat timeout, returns queued work to the pending pool, expires running task leases, decrements worker load, and retries work until `maxAttempts` is reached. Terminal work becomes `FAILED`.

## Idempotency

`ScheduleComputeV3` accepts `idempotencyKey`. Repeating the same key returns the existing task instead of creating duplicate work.

## Results

`CompleteTaskV3` accepts any JSON-compatible `result`. `GetTask` returns the persisted payload, status, attempt counters, lease information, error, and completion timestamps.

## Observability

`GetSchedulerMetrics` reports worker and task status counts plus the active scheduler timing policy.

## Public smoke test

Set `SAREMBOK_AUTH_TOKEN` and run:

```bash
python Deployment/cloud/public_scheduler_v3_smoke.py
```

The smoke test uses `wss://sarembok.com/` by default and never prints the authentication token.

## Safe deployment

Use `deploy_scheduler_v3.sh`. It rebuilds and recreates only the runtime, starts the edge service with the production compose overlay, checks `/health`, and runs the public WSS smoke test.

**Do not use `docker compose down -v` and do not delete the persistent `/data/sarembok_cloud.db` volume.**
