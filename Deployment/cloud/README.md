# Sarembok_VE Cloud Runtime

This directory contains the standalone cloud-native compatibility gateway for Sarembok_VE.

## Runtime contract

`server.py` preserves the existing public JSON-RPC contract over WebSocket on port `9000`.

## Local validation

From `C:\Sarembok_VE`:

```powershell
docker compose -f Deployment/cloud/compose.yaml build --no-cache
docker compose -f Deployment/cloud/compose.yaml up -d
python Deployment/cloud/smoke_test.py
```

Expected:

```text
CLOUD SMOKE TEST: 12/12 FACETS PASSED
```

## Hardening

The runtime provides:

- Optional token authentication via `SAREMBOK_AUTH_TOKEN`.
- Constant-time token comparison.
- Maximum WebSocket message size.
- Maximum concurrent connection count.
- Request and method validation.
- Serialized SQLite access with a busy timeout.
- Structured application logging.
- SIGINT/SIGTERM graceful shutdown.
- WebSocket ping/pong liveness.
- Compression disabled at the runtime boundary.
- Non-root container execution.
- Read-only container filesystem with writable `/data` and constrained `/tmp`.
- Dropped Linux capabilities and `no-new-privileges`.
- Container CPU, memory, and PID limits.
- Localhost-only port publishing in the development Compose profile.

Authentication remains optional for local compatibility testing. A production deployment must provide `SAREMBOK_AUTH_TOKEN` through a secret mechanism and place TLS/WSS termination in front of the runtime before exposing it to the Internet.

## Deployment boundary

```text
Internet
   |
HTTPS / WSS
   |
TLS termination + authentication
   |
Sarembok_VE Cloud Runtime :9000
   |
SQLite WAL volume
```

The runtime must not be published directly to the public Internet without the TLS/authentication boundary.
