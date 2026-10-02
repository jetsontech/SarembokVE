# Sarembok_VE Cloud Runtime

This directory contains the standalone cloud-native compatibility gateway for Sarembok_VE on `sarembok.com`.

## Production Domain

The official production domain is:

```text
sarembok.com
```

Cloudflare handles DNS and SSL termination before routing to the Caddy edge (`sarembok-edge`).

## One-Command Deployment

From `C:\Sarembok_VE`:

```powershell
.\Sarembok.ps1 -Deploy Cloud
```

This automatically runs:
`CHECK` → `CONFIGURE` → `VALIDATE` → `BUILD` → `START` → `WAIT FOR HEALTH` → `SMOKE TEST` → `REPORT`.

## Architecture & GPU Compute Abstraction

```text
                         sarembok.com
                              │
                         Cloudflare
                              │
                       HTTPS / WSS
                              │
                              ▼
                    ┌──────────────────┐
                    │   SAREMBOK EDGE  │ (Caddy Reverse Proxy :80 / :443)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ SAREMBOK RUNTIME │ (Control Plane :9000 internal)
                    └────────┬─────────┘
                             │
                      Compute Scheduler
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        GPU INFERENCE   DIGITAL HUMAN    BATCH GPU
          WORKERS          WORKERS         WORKERS
                             │
                         Unreal 5.8
                         MetaHuman
```

GPU worker nodes register dynamically with the runtime using the `RegisterWorker` JSON-RPC method, providing capabilities, GPU model, VRAM, and status.

## Worker Task Execution

Worker task types are executed by concrete capability-specific executors. The worker does not fabricate successful results.

| Task type | Capability | Concrete executor |
| --- | --- | --- |
| `arithmetic`, `smoke_test`, `compute`, `general_compute` | `compute` | Local deterministic compute engine |
| `host_action`, `desktop` | `host_control` / `desktop` | Enrolled host executor |
| `web_automation` | `web_automation` | Playwright/Chromium |
| `inference`, `architecture_synthesis`, `code_generation` | `inference` | Configured OpenAI-compatible/Ollama endpoint or local Transformers model |
| `meta_human` | `meta_human` | Configured Sarembok/Unreal bridge |
| `verification_suite` | `compute` | Explicitly authorized local test command |
| `gpu_deployment` | `gpu` | Verified local NVIDIA hardware via `nvidia-smi` |

Optional worker integrations are enabled only when their real backend is present:

```text
SAREMBOK_WORKER_INFERENCE_URL       OpenAI-compatible or Ollama inference endpoint
SAREMBOK_WORKER_INFERENCE_API_KEY   Optional bearer credential for the inference endpoint
SAREMBOK_WORKER_MODEL               Local Transformers model identifier
SAREMBOK_UNREAL_BRIDGE_URL          Local Sarembok/Unreal bridge HTTP endpoint
SAREMBOK_WORKER_ALLOW_COMMANDS      Enables explicitly confirmed verification/host commands
```

Autonomous pipeline stages are capability-routed and dependency-gated: later stages are not dispatched until their predecessor has actually completed.

GPU rental is provider-backed only when these production settings are configured:

```text
SAREMBOK_GPU_PROVIDER_URL        Provider endpoint; Sarembok POSTs /provision
SAREMBOK_GPU_PROVIDER_API_KEY    Optional provider bearer credential
```

Without a configured provider, a rental request is persisted as `PENDING_PROVIDER`; it is never reported as an active GPU that does not exist.


## Hardening

- Mandatory `SAREMBOK_AUTH_TOKEN` in production.
- Runtime port removed from public host publishing (`ports: !reset []`).
- Container capabilities dropped (`cap_drop: ALL`, `no-new-privileges:true`).
- Read-only container filesystem with writable `/data` volume.
- Health checks for container liveness.
- Continuous WebSocket ping/pong liveness.

## Smoke & Master Testing

To run the full 32-test master regression suite:

```powershell
python Tools/Diagnostics/Test-SarembokMasterSuite.py --target http://127.0.0.1:9000 --auth-token $env:SAREMBOK_AUTH_TOKEN
```

To run the production cloud smoke test:

```powershell
python Deployment/cloud/smoke_test.py ws://127.0.0.1:9000
```

## Running Autonomous GPU Worker Daemon

To attach a compute worker node to the cloud runtime:

```powershell
python Deployment/cloud/worker_client.py --ws-url ws://127.0.0.1:9000 --auth-token $env:SAREMBOK_AUTH_TOKEN
```

