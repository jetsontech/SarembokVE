"""Authoritative runtime introspection for Sarembok VE."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _db_integrity(db: sqlite3.Connection) -> str:
    try:
        row = db.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]).upper() if row else "UNKNOWN"
    except Exception:
        return "ERROR"


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _worker_snapshot(db: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(db, "workers"):
        return {"registered": 0, "online": 0, "stale": 0, "offline": 0, "workers": []}
    rows = db.execute(
        """SELECT worker_id, capabilities, gpu_vendor, gpu_model, vram_mb,
        cuda_version, available_memory_mb, supported_models, latency_ms,
        status, last_heartbeat FROM workers ORDER BY worker_id"""
    ).fetchall()
    workers = []
    counts = {"ONLINE": 0, "STALE": 0, "OFFLINE": 0}
    for row in rows:
        status = str(row[9] or "UNKNOWN").upper()
        counts[status] = counts.get(status, 0) + 1
        workers.append({
            "workerId": row[0], "capabilities": _json_list(row[1]),
            "gpuVendor": row[2], "gpuModel": row[3], "vramMb": row[4],
            "cudaVersion": row[5], "availableMemoryMb": row[6],
            "supportedModels": _json_list(row[7]), "latencyMs": row[8],
            "status": status, "lastHeartbeat": row[10],
        })
    return {
        "registered": len(rows), "online": counts.get("ONLINE", 0),
        "stale": counts.get("STALE", 0), "offline": counts.get("OFFLINE", 0),
        "workers": workers,
    }


def _agent_snapshot(db: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(db, "agents"):
        return {"registered": 0, "online": 0, "agents": []}
    rows = db.execute(
        "SELECT agent_id, display_name, status, created_at, updated_at FROM agents ORDER BY agent_id"
    ).fetchall()
    agents = [{
        "agentId": row[0], "displayName": row[1],
        "status": str(row[2]).upper(), "createdAt": row[3], "updatedAt": row[4],
    } for row in rows]
    return {
        "registered": len(agents),
        "online": sum(1 for agent in agents if agent["status"] == "ONLINE"),
        "agents": agents,
    }


def _memory_snapshot(db: sqlite3.Connection) -> dict[str, Any]:
    integrity = _db_integrity(db)
    if not _table_exists(db, "memories"):
        return {"backend": "sqlite-wal", "status": "UNAVAILABLE", "entries": 0, "integrity": integrity}
    count = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    tiers = {str(row[0]): int(row[1]) for row in db.execute(
        "SELECT tier, COUNT(*) FROM memories GROUP BY tier"
    ).fetchall()}
    return {
        "backend": "sqlite-wal",
        "status": "ONLINE" if integrity == "OK" else "DEGRADED",
        "entries": int(count), "tiers": tiers, "integrity": integrity,
    }


def _scheduler_snapshot(db: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(db, "tasks"):
        return {"status": "UNAVAILABLE", "queueDepth": 0, "running": 0, "completed": 0, "failed": 0, "authority": "tasks_table"}
    rows = db.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall()
    counts = {str(row[0]).upper(): int(row[1]) for row in rows}
    return {
        "status": "READY",
        "queueDepth": counts.get("QUEUED", 0) + counts.get("PENDING_WORKER", 0),
        "running": counts.get("RUNNING", 0),
        "completed": counts.get("COMPLETED", 0),
        "failed": counts.get("FAILED", 0),
        "byStatus": counts,
        "authority": "tasks_table",
    }


def _compute_snapshot(workers: dict[str, Any], provider_router: Any) -> dict[str, Any]:
    capabilities: set[str] = set()
    gpu_workers: list[str] = []
    for worker in workers["workers"]:
        if worker["status"] != "ONLINE":
            continue
        capabilities.update(str(cap).lower() for cap in worker["capabilities"])
        if worker.get("gpuModel"):
            gpu_workers.append(worker["workerId"])
    try:
        configured = provider_router.configured()
    except Exception:
        configured = []
    if configured:
        capabilities.add("llm")
    return {
        "onlineWorkerCapabilities": sorted(capabilities),
        "gpuWorkerIds": gpu_workers,
        "onlineGpuWorkers": len(gpu_workers),
        "configuredModelProviders": [
            {"name": p.name, "model": p.model, "kind": p.kind} for p in configured
        ],
    }


def _provider_snapshot(provider_router: Any) -> dict[str, Any]:
    try:
        metrics = provider_router.metrics()
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": type(exc).__name__}
    recent = metrics.get("recent") or []
    successful = [entry for entry in recent if entry.get("ok")]
    last_success = successful[-1] if successful else None
    return {
        "status": "AVAILABLE" if metrics.get("configuredProviders") else "UNCONFIGURED",
        "configuredProviders": metrics.get("configuredProviders", []),
        "lastSuccessful": ({
            "provider": last_success.get("provider"), "model": last_success.get("model"),
            "api": last_success.get("api"), "latencyMs": last_success.get("latency_ms"),
            "ttftMs": last_success.get("ttft_ms"), "timestamp": last_success.get("timestamp"),
        } if last_success else None),
        "samples": metrics.get("samples", 0),
        "successes": metrics.get("successes", 0),
        "failures": metrics.get("failures", 0),
        "cooldowns": metrics.get("cooldowns", {}),
    }


def snapshot(store: Any, provider_router: Any, started_at: float) -> dict[str, Any]:
    """Return only observable runtime state; this function never invents facts."""
    db = store.db
    workers = _worker_snapshot(db)
    agents = _agent_snapshot(db)
    memory = _memory_snapshot(db)
    scheduler = _scheduler_snapshot(db)
    provider = _provider_snapshot(provider_router)
    conversations = int(db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]) if _table_exists(db, "conversations") else 0
    events = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0]) if _table_exists(db, "events") else 0
    tasks = int(db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]) if _table_exists(db, "tasks") else 0
    return {
        "type": "system_diagnostic",
        "source": "runtime_authority",
        "observedAt": _now(),
        "runtime": {
            "status": "ONLINE", "service": "sarembok-ve-cloud-runtime",
            "port": int(os.getenv("SAREMBOK_PORT", "9000")),
            "domain": os.getenv("SAREMBOK_DOMAIN", "sarembok.com"),
            "uptimeSeconds": int(time.time() - started_at),
        },
        "workers": workers,
        "agents": agents,
        "compute": _compute_snapshot(workers, provider_router),
        "memory": memory,
        "scheduler": scheduler,
        "provider": provider,
        "state": {"tasks": tasks, "events": events, "conversations": conversations},
    }


def render_markdown(data: dict[str, Any]) -> str:
    """Render a human-readable diagnostic directly from the authoritative snapshot."""
    runtime = data["runtime"]
    workers = data["workers"]
    agents = data["agents"]
    compute = data["compute"]
    memory = data["memory"]
    scheduler = data["scheduler"]
    provider = data["provider"]
    lines = [
        "## Sarembok Runtime Diagnostic", "",
        f"**Observed:** `{data['observedAt']}`",
        f"**Authority:** `{data['source']}`", "",
        "### Runtime",
        f"- Status: **{runtime['status']}**",
        f"- Service: `{runtime['service']}`",
        f"- Port: `{runtime['port']}`",
        f"- Domain: `{runtime['domain']}`",
        f"- Uptime: `{runtime['uptimeSeconds']}s`", "",
        "### Registered Workers",
        f"- Registered: **{workers['registered']}**",
        f"- Online: **{workers['online']}**",
        f"- Stale: **{workers['stale']}**",
        f"- Offline: **{workers['offline']}**",
    ]
    for worker in workers["workers"]:
        gpu = f" — {worker['gpuModel']} / {worker['vramMb']} MB" if worker.get("gpuModel") else ""
        caps = ", ".join(worker["capabilities"]) or "none"
        lines.append(f"- `{worker['workerId']}` — **{worker['status']}** — capabilities: `{caps}`{gpu}")
    lines += [
        "", "### Compute",
        f"- Online GPU workers: **{compute['onlineGpuWorkers']}**",
        f"- Online worker capabilities: `{', '.join(compute['onlineWorkerCapabilities']) or 'none'}`",
        f"- Configured model providers: **{len(compute['configuredModelProviders'])}**", "",
        "### Agents",
        f"- Registered: **{agents['registered']}**",
        f"- Online: **{agents['online']}**",
    ]
    for agent in agents["agents"]:
        lines.append(f"- `{agent['agentId']}` — {agent['displayName']} — **{agent['status']}**")
    lines += [
        "", "### Persistent Memory",
        f"- Backend: **{memory['backend']}**",
        f"- Status: **{memory['status']}**",
        f"- Entries: **{memory['entries']}**",
        f"- Integrity: `{memory['integrity']}`", "",
        "### Scheduler",
        f"- State: **{scheduler['status']}**",
        f"- Queue depth: **{scheduler['queueDepth']}**",
        f"- Running: **{scheduler['running']}**",
        f"- Completed: **{scheduler['completed']}**",
        f"- Failed: **{scheduler['failed']}**",
        f"- Authority: `{scheduler['authority']}`", "",
        "### Model Provider",
    ]
    last = provider.get("lastSuccessful")
    if last:
        lines += [
            f"- Last successful provider: **{last['provider']}**",
            f"- Model: `{last['model']}`",
            f"- API: `{last['api']}`",
            f"- Latency: `{last['latencyMs']} ms`",
            f"- TTFT: `{last['ttftMs']} ms`" if last.get("ttftMs") is not None else "- TTFT: `not recorded`",
        ]
    else:
        lines.append("- No successful provider call is recorded in the current process telemetry.")
    lines += ["", "**Truth boundary:** this report is generated from runtime-observed state. It does not infer or invent unavailable infrastructure facts."]
    return "\n".join(lines)
