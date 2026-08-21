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

## Engineering Agent RPC

The protected Runtime JSON-RPC gateway exposes the Sarembok Engineering Agent
through `EngineeringAgentInfo`, `EngineeringExecutePlan`, and
`EngineeringGetExecution`. These methods require `SAREMBOK_AUTH_TOKEN`, are
not available to anonymous browser sessions, and persist execution evidence
under the writable `/data` volume.

## Operator-managed remote connector

Production enables the Engineering Agent's remote connector with a dedicated
host-managed OpenSSH identity. The private key and pinned `known_hosts` file
are mounted read-only into the runtime by `compose.production.yaml`; neither
is committed to Git or copied into the image. Password authentication is not
used by the agent.

The connector is limited by `SAREMBOK_ENGINEERING_REMOTE_COMMANDS` and uses
the configured VPS profile in `Config/remote_servers/sarembok-vps.json`. Keep
the key restricted to the Docker network and rotate it as an operator-managed
credential.

