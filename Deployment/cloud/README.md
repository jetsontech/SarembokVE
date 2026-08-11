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

## Hardening

- Mandatory `SAREMBOK_AUTH_TOKEN` in production.
- Runtime port removed from public host publishing (`ports: !reset []`).
- Container capabilities dropped (`cap_drop: ALL`, `no-new-privileges:true`).
- Read-only container filesystem with writable `/data` volume.
- Health checks for container liveness.
- Continuous WebSocket ping/pong liveness.

## Smoke Testing

To test the deployment:

```powershell
python Deployment/cloud/smoke_test.py ws://127.0.0.1:9000
```
