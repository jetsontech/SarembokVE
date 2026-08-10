# Sarembok Cloud Runtime — Bootstrap

This directory is the first cloud-native deployment layer for Sarembok VE.

## What this is

`server.py` exposes the same 12 public JSON-RPC method names used by the official Python and TypeScript SDKs over WebSocket on port `9000`.

It is a **compatibility gateway**, not a claim that the Unreal Engine production subsystems have been ported to Python. It provides persistent SQLite/WAL-backed cloud state and a stable transport contract so the runtime can be moved off the Unreal workstation without breaking the SDK surface.

## Local validation

From the repository root:

```powershell
docker compose -f Deployment/cloud/compose.yaml up --build -d
python Deployment/cloud/smoke_test.py
```

Expected result:

```text
CLOUD SMOKE TEST: 12/12 FACETS PASSED
```

The container persists state in the `sarembok-data` volume.

## Architecture boundary

```text
Cloud Runtime (Python)
  ├── JSON-RPC transport :9000
  ├── 12-facet compatibility contract
  ├── SQLite + WAL persistence
  ├── Agent state
  ├── Events / messages
  └── Recovery metadata

Unreal Client
  └── Presentation / embodiment / rendering
```

## Next gates

1. Build and run locally.
2. Run the 12-facet smoke test.
3. Compare cloud responses against the existing qualification contract.
4. Add TLS/WSS reverse proxy.
5. Add authentication and authorization.
6. Add structured telemetry and metrics export.
7. Deploy the validated container to a minimal VM.

No cloud provider or domain is required for this bootstrap stage.
