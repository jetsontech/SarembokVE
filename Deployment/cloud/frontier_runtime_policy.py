"""Frontier production policy applied to the compatibility runtime."""
from __future__ import annotations

import hmac
import os
import shlex
import subprocess
from typing import Any

SAFE_COMMANDS = {"date","df","free","git","hostname","id","ls","python","python3","pwd","uname","uptime"}
SYNTHETIC_WORKER_IDS = {"sarembok-edge-frontier-01"}
SYNTHETIC_WORKER_PREFIXES = ("worker-gpu-","worker-edge-","worker-scale-")


def _cloud(runtime: Any) -> Any:
    cloud = getattr(runtime, "cloud_server", None)
    if cloud is None:
        raise RuntimeError("cloud_server_unavailable")
    return cloud


def _purge_synthetic_workers(runtime: Any) -> None:
    cloud = _cloud(runtime)
    store = getattr(cloud, "store", None)
    db = getattr(store, "db", None)
    if db is None:
        raise RuntimeError("runtime_store_unavailable")
    rows = db.execute("SELECT worker_id FROM workers").fetchall()
    doomed = [
        str(row[0])
        for row in rows
        if str(row[0]) in SYNTHETIC_WORKER_IDS or str(row[0]).startswith(SYNTHETIC_WORKER_PREFIXES)
    ]
    if doomed:
        db.executemany("DELETE FROM workers WHERE worker_id=?", [(wid,) for wid in doomed])
        db.commit()


def apply(runtime: Any) -> None:
    """Apply production-only truth and typed administrative execution controls."""
    runtime.ensure_sovereign_worker=lambda: None
    cloud = _cloud(runtime)
    cloud.ensure_sovereign_worker=lambda: None

    original_liveness = getattr(cloud, "evaluate_worker_liveness", None)
    if callable(original_liveness):
        def guarded_worker_liveness(*args: Any, **kwargs: Any):
            result = original_liveness(*args, **kwargs)
            _purge_synthetic_workers(runtime)
            return result
        cloud.evaluate_worker_liveness = guarded_worker_liveness

    _purge_synthetic_workers(runtime)

    # The legacy server has its own administrative gate. Frontier production
    # authentication is authoritative, so bind that gate to the same
    # configured credentials and provide a typed-admin execution bridge.
    legacy_dispatch = getattr(cloud, "dispatch", None)
    if callable(legacy_dispatch):
        admin_token = os.getenv("SAREMBOK_ADMIN_TOKEN", "").strip()
        admin_passcode = os.getenv("SAREMBOK_ADMIN_PASSCODE", "").strip()
        legacy_globals = getattr(legacy_dispatch, "__globals__", None)
        if isinstance(legacy_globals, dict):
            legacy_globals["ADMIN_TOKENS"] = {admin_token} if admin_token else set()
            legacy_globals["ADMIN_ALLOWED_PASSCODES"] = {admin_passcode} if admin_passcode else set()

        def guarded_admin_dispatch(method: str, params: dict[str, Any]) -> Any:
            if method != "AdminExecuteDirective":
                return legacy_dispatch(method, params)
            supplied_token = str(params.get("adminToken") or params.get("adminSessionToken") or "").strip()
            supplied_passcode = str(params.get("adminPasscode") or params.get("passcode") or "").strip()
            token_ok = bool(admin_token and supplied_token and hmac.compare_digest(supplied_token, admin_token))
            passcode_ok = bool(admin_passcode and supplied_passcode and hmac.compare_digest(supplied_passcode, admin_passcode))
            if not (token_ok or passcode_ok):
                raise ValueError("admin_authentication_required: configured frontier administrative credential required")
            directive = str(params.get("directive") or params.get("prompt") or "").strip()
            if not directive:
                raise ValueError("directive is required")
            session_id = str(params.get("sessionId") or "admin-session").strip() or "admin-session"
            model = str(params.get("model") or "").strip() or None
            dialogue = getattr(cloud, "sarembok_process_dialogue", None)
            if not callable(dialogue):
                return legacy_dispatch(method, {**params, "adminPasscode": admin_passcode, "passcode": admin_passcode})
            return dialogue(directive, session_id=session_id, model=model, admin=True)

        cloud.dispatch = guarded_admin_dispatch

    def safe_run_terminal(cls, command: str) -> dict[str, Any]:
        command = str(command or "").strip()
        if not command:
            return {"error":"command is required"}
        try:
            argv = shlex.split(command, posix=True)
        except ValueError as exc:
            return {"error":f"invalid_command: {exc}"}
        if not argv or argv[0] not in SAFE_COMMANDS:
            return {"error":"command_not_allowlisted"}
        if any(token in command for token in (";","&&","||","|",">","<","`","$(","${")):
            return {"error":"shell_syntax_not_permitted"}
        if argv[0] == "git" and (len(argv) < 2 or argv[1] not in {"status","log","diff","show","rev-parse"}):
            return {"error":"git_operation_not_allowlisted"}
        if argv[0] in {"python","python3"} and len(argv) > 1 and argv[1] not in {"--version","-V"}:
            return {"error":"python_execution_disabled_in_production"}
        try:
            proc = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=8, check=False)
            stdout, stderr = proc.stdout.strip(), proc.stderr.strip()
            return {"command":command,"exitCode":proc.returncode,"stdout":stdout[:2500],"stderr":stderr[:1000],"truncated":len(stdout)>2500}
        except subprocess.TimeoutExpired:
            return {"command":command,"error":"diagnostic_command_timeout"}
        except Exception as exc:
            return {"command":command,"error":type(exc).__name__}

    def disabled_python(cls, code_snippet: str) -> dict[str, Any]:
        return {"status":"DISABLED","error":"arbitrary_python_execution_disabled_in_production"}

    def disabled_read(cls, path: str) -> dict[str, Any]:
        return {"status":"DENIED","error":"arbitrary_admin_file_read_disabled_in_production"}

    def disabled_write(cls, path: str, content: str) -> dict[str, Any]:
        return {"status":"DENIED","error":"arbitrary_file_write_disabled_in_production","path":str(path or "")}

    def disabled_admin_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status":"DISABLED","error":"free_form_admin_agent_disabled_in_production","executionModel":"typed_rpc_only"}

    registry = getattr(runtime, "AdminToolRegistry", None)
    if registry is not None:
        registry.run_terminal=classmethod(safe_run_terminal)
        registry.execute_python=classmethod(disabled_python)
        registry.read_file=classmethod(disabled_read)
        registry.write_file=classmethod(disabled_write)

    runtime.run_admin_agent_loop=disabled_admin_agent
    runtime.PRODUCTION_TRUTH_BOUNDARY=True
    runtime.SYNTHETIC_WORKER_REGISTRATION_DISABLED=True
    runtime.SYNTHETIC_WORKER_ID=os.getenv("SAREMBOK_SYNTHETIC_WORKER_ID","").strip()
