# Sarembok VE Deployment Guide

## Prerequisites

- **Host Machine**: Ubuntu 22.04 LTS / Debian 12 / RHEL 9 (Minimum: 2 vCPU, 4GB RAM)
- **Software**: Docker 24.0+ & Docker Compose v2.20+
- **Network**: Ports `80` and `443` open to inbound public traffic
- **DNS**: A/AAAA record pointing `sarembok.com` to the server IP

---

## Safe Frontend Deployment

The OVH edge container bind-mounts the VPS `frontend/` directory at `/srv`. Deploy tracked frontend changes with:

```powershell
powershell -ExecutionPolicy Bypass -File Tools/Deploy-To-OVH.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File Tools/Deploy-To-OVH.ps1
```

The script checks that the VPS is on `main` and has no tracked local edits, fetches `origin/main`, and uses `git merge --ff-only`. It never resets or discards VPS files. Untracked backups and configuration are preserved; an incoming tracked-file collision causes Git to stop rather than overwrite them. The script deploys the static frontend only and verifies `/`, `/docs`, the logo/banner assets, `robots.txt`, and `sitemap.xml` over local HTTPS. A Caddy restart is not required for bind-mounted static files.

## Runtime Deployment Status

The VPS runtime containers are currently managed outside the tracked repository deployment configuration. `Deployment/cloud/compose.yaml` and `compose.production.yaml` are not present in the repository. Runtime/backend releases are therefore not automated by the frontend script; add and review sanitized, tracked runtime manifests and secrets references before enabling container rebuilds.

---

## Container Architecture

| Service Name | Image | Port (Internal) | Port (External) | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `sarembok-edge` | `caddy:2-alpine` | `80`, `443` | `80`, `443` | TLS termination, edge proxy, static frontend |
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
