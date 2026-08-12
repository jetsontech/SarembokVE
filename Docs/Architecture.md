# Sarembok VE Architecture Guide

## Overview

Sarembok VE is designed as a modular, hardware-adaptive digital human platform consisting of four core layers:

1. **Edge Transport Layer (Caddy)**: Public HTTPS and WSS entry point providing automated TLS termination, security header injection, and reverse proxying.
2. **Web Operator Layer (Frontend)**: Single-page Web application serving a public landing showcase and an authenticated operator control plane for real-time monitoring and management.
3. **Cloud Runtime Core (`sarembok-runtime`)**: Asynchronous Python process (`server.py`) handling SQLite persistence, JSON-RPC 2.0 dispatch, GPU compute scheduling, and digital human session routing.
4. **Engine Client Layer (Unreal Engine 5.8)**: In-engine C++ subsystem plugins (`SarembokBridge`, `SarembokAvatar`, `SarembokVoice`, `SarembokVision`, `SarembokAgent`, `SarembokMemory`) executing real-time morph targets, speech, perception, and reasoning loops.

---

## Data Flow Diagram

```text
User / Operator
      │
      ├─── HTTP GET / ───► Caddy Edge ───► Static Web App (index.html)
      │
      └─── WSS /ws ──────► Caddy Edge ───► sarembok-runtime (server.py)
                                                    │
                                                    ├──► SQLite WAL (/data/sarembok_cloud.db)
                                                    ├──► GPU Worker Pool
                                                    └──► Digital Human Sessions (Unreal Engine)
```

---

## Storage Architecture

All runtime state is stored in `/data/sarembok_cloud.db` using SQLite with Write-Ahead Logging (WAL):

- `agents`: Autonomous agent identities and status.
- `workers`: GPU compute node capabilities, VRAM, and heartbeat timestamps.
- `digital_human_sessions`: Active avatar sessions and assigned worker mappings.
- `tasks`: Compute scheduler queue and execution history.
- `events`: Append-only structured system audit trail.
- `messages`: Agent conversation log history.
- `delegations`: Inter-agent goal delegation hierarchy.
