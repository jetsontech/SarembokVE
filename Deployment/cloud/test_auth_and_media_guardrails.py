import importlib.util
import sqlite3
import sys

import pytest

from pathlib import Path

SERVER_PATH = str(Path(__file__).resolve().with_name("server.py"))


def load_server_module(monkeypatch, *, auth_token="", admin_passcode=""):
    monkeypatch.delenv("SAREMBOK_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SAREMBOK_ADMIN_PASSCODE", raising=False)

    if auth_token:
        monkeypatch.setenv("SAREMBOK_AUTH_TOKEN", auth_token)

    if admin_passcode:
        monkeypatch.setenv("SAREMBOK_ADMIN_PASSCODE", admin_passcode)

    sys.modules.pop("server", None)
    sys.modules.pop("Deployment.cloud.server", None)
    spec = importlib.util.spec_from_file_location("server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_unset_admin_passcode_fails_closed(monkeypatch):
    mod = load_server_module(monkeypatch, auth_token="", admin_passcode="")

    assert mod.ADMIN_PASSCODE == ""
    assert mod.ADMIN_ALLOWED_PASSCODES == set()


def test_missing_runtime_auth_is_rejected_for_chat_requests(monkeypatch):
    mod = load_server_module(monkeypatch, auth_token="", admin_passcode="")

    with pytest.raises(PermissionError):
        mod.authenticate({"params": {}}, "SarembokChat")

    with pytest.raises(PermissionError):
        mod.authenticate({"params": {"authToken": ""}}, "SarembokChat")


def test_runtime_identity_does_not_claim_dynamic_mcp_skills(monkeypatch):
    mod = load_server_module(monkeypatch, auth_token="secure-token", admin_passcode="change-me-now")

    snapshot = {
        "runtime": {"status": "ONLINE", "service": "sarembok-ve-cloud-runtime", "domain": "sarembok.com", "port": 9000},
        "workers": {"registered": 1, "online": 1, "stale": 0, "offline": 0},
        "agents": {"registered": 1, "online": 1},
        "compute": {"onlineGpuWorkers": 1, "onlineWorkerCapabilities": ["compute", "vision", "voice"]},
        "memory": {"backend": "sqlite-wal", "status": "ONLINE", "entries": 3, "integrity": "OK"},
        "provider": {"configuredProviders": [{"name": "openai", "model": "gpt-4o-mini", "api": "OpenAI"}]},
    }

    output = mod.render_identity(snapshot)

    assert "dynamic mcp skills" not in output.lower()
    assert "mcp" not in output.lower()



def _install_isolated_worker_db(mod, monkeypatch):
    db = sqlite3.connect(":memory:")
    db.execute(
        """
        CREATE TABLE workers (
            worker_id TEXT PRIMARY KEY,
            capabilities TEXT,
            gpu_vendor TEXT,
            gpu_model TEXT,
            vram_mb INTEGER,
            cuda_version TEXT,
            available_memory_mb INTEGER,
            supported_models TEXT,
            latency_ms REAL,
            status TEXT,
            last_heartbeat TEXT,
            active_tasks INTEGER DEFAULT 0,
            worker_token_hash TEXT,
            metadata_marker TEXT DEFAULT 'default-marker'
        )
        """
    )
    monkeypatch.setattr(mod.store, "db", db)
    monkeypatch.setattr(mod, "ensure_scheduler_schema", lambda: None)
    return db


def test_register_worker_rejects_browser_session_only(monkeypatch):
    mod = load_server_module(monkeypatch)
    mod.BROWSER_SESSIONS["browser-only-token"] = mod.time.time() + 3600

    with pytest.raises(PermissionError):
        mod.authenticate(
            {"params": {"sessionToken": "browser-only-token"}},
            "RegisterWorker",
        )


def test_enrollment_token_cannot_take_over_existing_worker(monkeypatch):
    mod = load_server_module(monkeypatch)
    mod.WORKER_ENROLLMENT_TOKEN = "worker-enrollment-secret"
    db = _install_isolated_worker_db(mod, monkeypatch)
    db.execute(
        "INSERT INTO workers (worker_id, active_tasks, worker_token_hash) VALUES (?, ?, ?)",
        ("existing-worker", 2, "original-token-hash"),
    )
    db.commit()

    with pytest.raises(PermissionError, match="worker_reenrollment_requires_admin"):
        mod._dispatch_internal(
            "RegisterWorker",
            {
                "workerId": "existing-worker",
                "enrollmentToken": "worker-enrollment-secret",
                "capabilities": ["compute"],
            },
        )

    row = db.execute(
        "SELECT active_tasks, worker_token_hash FROM workers WHERE worker_id=?",
        ("existing-worker",),
    ).fetchone()
    assert row == (2, "original-token-hash")


def test_enrollment_token_can_register_new_worker(monkeypatch):
    mod = load_server_module(monkeypatch)
    mod.WORKER_ENROLLMENT_TOKEN = "worker-enrollment-secret"
    db = _install_isolated_worker_db(mod, monkeypatch)

    result = mod._dispatch_internal(
        "RegisterWorker",
        {
            "workerId": "new-worker",
            "enrollmentToken": "worker-enrollment-secret",
            "capabilities": ["compute"],
        },
    )

    assert result["registered"] is True
    row = db.execute(
        "SELECT worker_token_hash FROM workers WHERE worker_id=?",
        ("new-worker",),
    ).fetchone()
    assert row is not None
    assert row[0]


def test_existing_worker_token_can_reconnect_without_rotation(monkeypatch):
    mod = load_server_module(monkeypatch)
    db = _install_isolated_worker_db(mod, monkeypatch)
    original_token = "persisted-worker-token"
    import hashlib
    original_hash = hashlib.sha256(original_token.encode("utf-8")).hexdigest()
    db.execute(
        "INSERT INTO workers (worker_id, active_tasks, worker_token_hash) VALUES (?, ?, ?)",
        ("existing-worker", 3, original_hash),
    )
    db.execute(
        "UPDATE workers SET metadata_marker=? WHERE worker_id=?",
        ("preserve-existing-row", "existing-worker"),
    )
    db.commit()

    params = {
        "workerId": "existing-worker",
        "workerToken": original_token,
        "capabilities": ["compute"],
    }
    mod.authenticate({"params": params}, "RegisterWorker")
    result = mod._dispatch_internal("RegisterWorker", params)

    assert result["registered"] is True
    assert "workerToken" not in result
    row = db.execute(
        "SELECT active_tasks, worker_token_hash, metadata_marker FROM workers WHERE worker_id=?",
        ("existing-worker",),
    ).fetchone()
    assert row == (3, original_hash, "preserve-existing-row")


def test_invalid_worker_token_cannot_reconnect(monkeypatch):
    mod = load_server_module(monkeypatch)
    db = _install_isolated_worker_db(mod, monkeypatch)
    db.execute(
        "INSERT INTO workers (worker_id, active_tasks, worker_token_hash) VALUES (?, ?, ?)",
        ("existing-worker", 1, "known-hash"),
    )
    db.commit()

    with pytest.raises(PermissionError, match="authentication_required"):
        mod.authenticate(
            {"params": {"workerId": "existing-worker", "workerToken": "wrong-token"}},
            "RegisterWorker",
        )


def test_admin_credential_can_reenroll_existing_worker(monkeypatch):
    mod = load_server_module(monkeypatch, auth_token="trusted-operator-token")
    db = _install_isolated_worker_db(mod, monkeypatch)
    db.execute(
        "INSERT INTO workers (worker_id, active_tasks, worker_token_hash) VALUES (?, ?, ?)",
        ("existing-worker", 2, "old-token-hash"),
    )
    db.commit()

    params = {
        "workerId": "existing-worker",
        "authToken": "trusted-operator-token",
        "capabilities": ["compute"],
    }
    mod.authenticate({"params": params}, "RegisterWorker")
    result = mod._dispatch_internal("RegisterWorker", params)

    assert result["registered"] is True
    assert result["workerToken"]
    row = db.execute(
        "SELECT active_tasks, worker_token_hash FROM workers WHERE worker_id=?",
        ("existing-worker",),
    ).fetchone()
    assert row[0] == 2
    assert row[1] != "old-token-hash"
    assert row[1] == __import__("hashlib").sha256(result["workerToken"].encode("utf-8")).hexdigest()
