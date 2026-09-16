"""Frontier production policy applied at the cloud runtime boundary."""
from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

SAFE_COMMANDS = {
    "date", "df", "free", "git", "hostname", "id", "ls", "python", "python3", "pwd", "uname", "uptime",
}
SYNTHETIC_WORKER_IDS = {"sarembok-edge-frontier-01"}
SYNTHETIC_WORKER_PREFIXES = ("worker-gpu-", "worker-edge-", "worker-scale-")
PUBLIC_HTTP_PATHS = {"/", "/index.html", "/health", "/healthz", "/session"}


def _purge_synthetic_workers(runtime: Any) -> None:
    rows = runtime.store.db.execute("SELECT worker_id FROM workers").fetchall()
    doomed = []
    for row in rows:
        worker_id = str(row[0])
        if worker_id in SYNTHETIC_WORKER_IDS or worker_id.startswith(SYNTHETIC_WORKER_PREFIXES):
            doomed.append(worker_id)
    if doomed:
        runtime.store.db.executemany("DELETE FROM workers WHERE worker_id=?", [(wid,) for wid in doomed])
        runtime.store.db.commit()


def _not_found(connection: Any) -> Any:
    body = b"Not Found\n"
    if hasattr(connection, "respond"):
        return connection.respond(404, "Not Found\n")
    return (404, [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))], body)


def apply(runtime: Any) -> None:
    """Apply production-only truth, execution and HTTP controls."""
    runtime.ensure_sovereign_worker = lambda: None
    _purge_synthetic_workers(runtime)

    original_http = runtime.cloud_server.process_http_request

    async def secure_http_request(connection: Any, request: Any) -> Any:
        headers = getattr(request, "headers", {}) or {}
        upgrade = headers.get("Upgrade", "") if hasattr(headers, "get") else ""
        if str(upgrade).lower() == "websocket":
            return None
        path = getattr(request, "path", None) or getattr(connection, "path", "/")
        path_only = str(path).split("?", 1)[0]
        if path_only not in PUBLIC_HTTP_PATHS:
            return _not_found(connection)
        return await original_http(connection, request)

    runtime.cloud_server.process_http_request = secure_http_request

    def safe_run_terminal(cls, command: str) -> dict[str, Any]:
        command = str(command or "").strip()
        if not command:
            return {"error": "command is required"}
        try:
            argv = shlex.split(command, posix=True)
        except ValueError as exc:
            return {"error": f"invalid_command: {exc}"}
        if not argv or argv[0] not in SAFE_COMMANDS:
            return {"error": "command_not_allowlisted"}
        if any(token in command for token in (";", "&&", "||", "|", ">", "<", "`", "$(", "${")):
            return {"error": "shell_syntax_not_permitted"}
        if argv[0] == "git" and (len(argv) < 2 or argv[1] not in {"status", "log", "diff", "show", "rev-parse"}):
            return {"error": "git_operation_not_allowlisted"}
        if argv[0] in {"python", "python3"} and len(argv) > 1 and argv[1] not in {"--version", "-V"}:
            return {"error": "python_execution_disabled_in_production"}
        try:
            proc = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=8, check=False)
            stdout, stderr = proc.stdout.strip(), proc.stderr.strip()
            return {"command": command, "exitCode": proc.returncode, "stdout": stdout[:2500], "stderr": stderr[:1000], "truncated": len(stdout) > 2500}
        except subprocess.TimeoutExpired:
            return {"command": command, "error": "diagnostic_command_timeout"}
        except Exception as exc:
            return {"command": command, "error": type(exc).__name__}

    def disabled_python(cls, code_snippet: str) -> dict[str, Any]:
        return {"status": "DISABLED", "error": "arbitrary_python_execution_disabled_in_production"}

    def disabled_write(cls, path: str, content: str) -> dict[str, Any]:
        return {"status": "DENIED", "error": "arbitrary_file_write_disabled_in_production", "path": str(path or "")}

    registry = getattr(runtime, "AdminToolRegistry", None)
    if registry is not None:
        registry.run_terminal = classmethod(safe_run_terminal)
        registry.execute_python = classmethod(disabled_python)
        registry.write_file = classmethod(disabled_write)

    runtime.PRODUCTION_TRUTH_BOUNDARY = True
    runtime.SYNTHETIC_WORKER_REGISTRATION_DISABLED = True
    runtime.SYNTHETIC_WORKER_ID = os.getenv("SAREMBOK_SYNTHETIC_WORKER_ID", "").strip()
