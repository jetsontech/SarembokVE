# Sarembok VE Deployment Guide

## Prerequisites

- **Host Machine**: Ubuntu 22.04 LTS / Debian 12 / RHEL 9 (Minimum: 2 vCPU, 4GB RAM)
- **Software**: Docker 24.0+ & Docker Compose v2.20+
- **Network**: Ports `80` and `443` open to inbound public traffic
- **DNS**: A/AAAA record pointing `sarembok.com` to the server IP

---

## 1-Command Production Deployment

Execute the automated deployment orchestrator script:

```powershell
powershell -ExecutionPolicy Bypass -File Sarembok.ps1 -Deploy Cloud -Domain "sarembok.com" -AuthToken "YOUR_SECURE_TOKEN"
```

Or run directly via Docker Compose:

```bash
export SAREMBOK_SITE_ADDRESS="sarembok.com"
export SAREMBOK_AUTH_TOKEN="YOUR_SECURE_TOKEN"

docker compose -f Deployment/cloud/compose.yaml -f Deployment/cloud/compose.production.yaml up -d --build
```

---

## Container Architecture

| Service Name | Image | Port (Internal) | Port (External) | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `sarembok-edge` | `caddy:2-alpine` | `80`, `443` | `80`, `443` | TLS termination, Edge proxy, static web app |
| `sarembok-runtime` | `python:3.12-slim` | `9000` | Isolated | SQLite WAL storage, WebSocket JSON-RPC server |

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SAREMBOK_PORT` | `9000` | Internal runtime server port |
| `SAREMBOK_DB_PATH` | `/data/sarembok_cloud.db` | SQLite database file location |
| `SAREMBOK_AUTH_TOKEN` | *Required in Prod* | Secret token for JSON-RPC authentication |
| `SAREMBOK_MAX_CONNECTIONS` | `100` | Max concurrent WebSocket connections |
| `SAREMBOK_SITE_ADDRESS` | `sarembok.com` | Public domain for Caddy TLS certificate |
