# Sarembok VE Troubleshooting Guide

## Diagnostic Flowchart

```text
DNS Resolution -> TLS Certificate -> Caddy Edge -> WebSocket Upgrade -> Auth Handshake -> JSON-RPC Dispatch -> SQLite Storage
```

---

## Common Diagnostic Recipes

### 1. WebSocket Handshake Fails / Timeout
- Verify `SAREMBOK_PUBLIC_HOST` matches your domain or IP.
- Confirm port `443` is open in host firewall (`ufw allow 443/tcp`).
- Ensure client sends `authToken` in RPC params when `SAREMBOK_AUTH_TOKEN` is configured.

### 2. SQLite Database Lock Errors
- Verify database file permissions on `/data/sarembok_cloud.db`.
- Confirm WAL mode is active (`PRAGMA journal_mode=WAL`).
- Run `python Deployment/cloud/smoke_test.py ws://127.0.0.1:9000` to verify lock timeouts.

### 3. Unreal Client Reconnection Loop
- Check Unreal Output Log (`Window -> Output Log`) for `[SAREMBOK]` entries.
- Verify `ServerURL` is set to `wss://sarembok.com` (or `ws://127.0.0.1:9000` for local dev).
- Confirm `AuthToken` is provided to `FSarembokWebSocketClient::Connect()`.
