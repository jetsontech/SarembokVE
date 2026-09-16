"""Frontier production policy applied at the cloud runtime boundary.

This module exists to make the production posture explicit without rewriting the
large compatibility dispatcher in one release. It disables development-only
synthetic hardware and replaces arbitrary host command execution with a small,
read-only diagnostic allowlist.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any


SAFE_COMMANDS = {
    "date",
    "df",
    "free",
    "git",
    "hostname",
    "id",
    "ls",
    "python",
    "python3",
    "pwd",
    "uname",
    "uptime",
}


def apply(runtime: Any) -> None:
    """Apply production-only truth and tool controls to the compatibility runtime."""
    # The historical dispatcher contains a development-era self-registration
    # routine for a fictional sovereign GPU node. Production must never invoke it.
    runtime.ensure_sovereign_worker = lambda: None

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
        # Only non-destructive diagnostics are allowed. Git is restricted to
        # read-only inspection operations.
        if argv[0] == "git" and (len(argv) < 2 or argv[1] not in {"status", "log", "diff", "show", "rev-parse"}):
            return {"error": "git_operation_not_allowlisted"}
        if argv[0] in {"python", "python3"} and len(argv) > 1 and argv[1] not in {"--version", "-V"}:
            return {"error": "python_execution_disabled_in_production"}
        try:
            proc = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            return {
                "command": command,
                "exitCode": proc.returncode,
                "stdout": stdout[:2500],
                "stderr": stderr[:1000],
                "truncated": len(stdout) > 2500,
            }
        except subprocess.TimeoutExpired:
            return {"command": command, "error": "diagnostic_command_timeout"}
        except Exception as exc:
            return {"command": command, "error": type(exc).__name__}

    def disabled_python(cls, code_snippet: str) -> dict[str, Any]:
        return {
            "status": "DISABLED",
            "error": "arbitrary_python_execution_disabled_in_production",
        }

    def disabled_write(cls, path: str, content: str) -> dict[str, Any]:
        return {
            "status": "DENIED",
            "error": "arbitrary_file_write_disabled_in_production",
            "path": str(path or ""),
        }

    registry = getattr(runtime, "AdminToolRegistry", None)
    if registry is not None:
        registry.run_terminal = classmethod(safe_run_terminal)
        registry.execute_python = classmethod(disabled_python)
        registry.write_file = classmethod(disabled_write)

    # Production must not expose a fabricated sovereign worker identifier as an
    # executable target. Leave legacy constants intact for compatibility, but
    # the release boundary treats them as non-authoritative metadata.
    runtime.PRODUCTION_TRUTH_BOUNDARY = True
    runtime.SYNTHETIC_WORKER_REGISTRATION_DISABLED = True
    runtime.SYNTHETIC_WORKER_ID = os.getenv("SAREMBOK_SYNTHETIC_WORKER_ID", "").strip()
