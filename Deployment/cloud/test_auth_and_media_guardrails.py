import importlib.util
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
