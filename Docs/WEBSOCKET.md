# Sarembok VE WebSocket Protocol Specification

## Overview

The primary real-time transport for Sarembok VE is WebSocket over TLS (`wss://sarembok.com`).

The WebSocket server runs inside the `sarembok-runtime` container on port `9000` (proxied by Caddy on port `443`).

---

## Connection Lifecyle

1. **Client Handshake**: Client initiates WSS connection (`wss://sarembok.com/`).
2. **Upgrade & Proxy**: Caddy proxies the connection to `sarembok-runtime:9000`.
3. **RPC Authenticated Health Check**: Client sends `Health` RPC containing `authToken`.
4. **Bidirectional Messaging**: Client and server exchange `sarembok.v1` envelopes and JSON-RPC method calls.
5. **Heartbeat / Ping**: Server maintains a 20-second ping interval and 20-second ping timeout.
6. **Graceful Close**: On disconnect or shutdown, connection closes cleanly (Close code `1000` or `1013 server_busy`).

---

## Canonical Envelope Schema (`sarembok.v1`)

```json
{
  "protocol": "sarembok.v1",
  "id": "cmd-000001",
  "timestamp": "2026-08-12T14:50:00Z",
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Greetings from Sarembok VE",
    "emotion": "Joyful"
  },
  "context": {
    "agent": "SarembokReasoner",
    "trace": "trace-000001",
    "confidence": 0.95
  }
}
```
