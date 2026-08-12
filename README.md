# Sarembok VE — Autonomous Digital Human & AI Cloud Platform

> **Production Deployment & Operating System for Embodied Digital Humans in Unreal Engine 5.8**

`https://sarembok.com`

---

## Overview

**Sarembok VE** is a production-grade cloud platform and runtime orchestrator that bridges AI reasoning and digital human avatars in **Unreal Engine 5.8**.

The platform provides:
* **Public Web Experience & Operator Control Plane**: High-aesthetic modern landing page and authenticated control dashboard for managing Workers, Agents, Tasks, Digital Human Sessions, and Event Audit Logs.
* **Cloud Runtime Engine (`sarembok-runtime`)**: Async Python process hosting SQLite WAL storage, worker heartbeats, compute task scheduler, and JSON-RPC 2.0 API gateway.
* **Edge Proxy (`sarembok-edge`)**: Caddy web server providing automated TLS, HTTP static file delivery, and WebSocket upgrade proxying.
* **Unreal Engine 5.8 Plugins (`SarembokBridge`)**: In-engine C++ modules enabling high-performance bidirectional WebSocket connectivity (`sarembok.v1` protocol).

---

## Quick Start (Production Deployment)

### 1. Configure Environment Variables
```bash
export SAREMBOK_PUBLIC_HOST="sarembok.com"
export SAREMBOK_AUTH_TOKEN="your-secure-secret-token"
```

### 2. Deploy with Docker Compose
```bash
docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml up -d --build
```

### 3. Verify System Health
```bash
python Deployment/cloud/smoke_test.py ws://127.0.0.1:9000
```

---

## System Architecture

```text
                               PUBLIC INTERNET
                                      |
                                      v
                             https://sarembok.com
                                      |
                                      v
                             +----------------+
                             |     CADDY      |
                             |  TLS / Edge    |
                             +-------+--------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
       Web Application                               WebSocket Proxy
   (Landing Page / Control Plane)                     (sarembok.v1)
              |                                             |
              +----------------------+----------------------+
                                     |
                                     v
                           sarembok-runtime:9000
                                     |
                                     v
                            CloudStore / SQLite
                                     |
                +--------------------+--------------------+
                |                    |                    |
                v                    v                    v
          GPU Workers           AI Reasoners       Digital Humans
                |
                v
      Unreal Engine 5.8 Client
```

---

## Documentation

Detailed documentation is available in the [`Docs/`](Docs/) directory:

* 🏗️ [**Architecture Guide**](Docs/ARCHITECTURE.md) — System topology, layers, and data flow.
* 🚀 [**Deployment Guide**](Docs/DEPLOYMENT.md) — Docker Compose, VPS provisioning, and environment config.
* 📡 [**API Specification**](Docs/API.md) — 25+ JSON-RPC 2.0 control plane & runtime methods.
* ⚡ [**WebSocket Protocol**](Docs/WEBSOCKET.md) — Real-time bidirectional transport schema (`sarembok.v1`).
* 🎮 [**Unreal Engine Integration**](Docs/UNREAL_INTEGRATION.md) — C++ setup, `SarembokBridge` plugin, and PIE setup.
* 🛠️ [**Operations & Maintenance**](Docs/OPERATIONS.md) — Backup, restore, log monitoring, and worker heartbeats.
* 🔒 [**Security Guide**](Docs/SECURITY.md) — Authentication token protection, connection limits, and privilege isolation.
* 🩺 [**Troubleshooting**](Docs/TROUBLESHOOTING.md) — Diagnostic scripts, common fixes, and log inspection.

---

## Verification & Qualification

To execute the complete 30-step production qualification suite:
```powershell
python Tools/Diagnostics/Test-SarembokProductionAcceptance.py ws://127.0.0.1:9000
```

`PRODUCTION ACCEPTANCE: PASSED`