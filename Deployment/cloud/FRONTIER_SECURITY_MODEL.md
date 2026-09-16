# SarembokVE Frontier Security Model

## Trust boundaries

1. Browser is an untrusted client.
2. Cloudflare/Caddy is the public edge.
3. `knowledge_rpc_server.py` is the production RPC boundary.
4. `server.py` is the legacy-compatible runtime dispatcher.
5. Providers and external workers are separate trust domains.

## Required controls

- Explicit environment-managed administrator and master credentials.
- Browser session scoped to USER permissions.
- Operator, administrator, master and worker identities are distinct.
- Unknown RPC methods fail closed.
- WebSocket origins are allowlisted.
- Per-IP and per-principal request rate limits are enforced.
- Mutating calls can carry idempotency keys.
- Execution IDs correlate requests, telemetry and audit events.
- Credential-bearing fields are redacted before logging or response propagation.
- Worker hardware claims are not treated as attested until independently verified.
- Cancellation is represented by execution identity and suppresses further stream output.
