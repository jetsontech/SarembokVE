"""Provider-neutral remote terminal capability for the Sarembok agent.

Credentials are deliberately outside the agent plan and source tree. The
default transport uses the host's OpenSSH client in batch mode, which supports
SSH keys, ssh-agent, and the operator's configured known_hosts file. Password
authentication remains an interactive operator concern and is never captured
in an execution record.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

try:  # Supports both package imports and the repository's focused test command.
    from .engineering_agent import ToolDescriptor
except ImportError:  # pragma: no cover - exercised only when run as a loose module
    from engineering_agent import ToolDescriptor


@dataclass(frozen=True)
class RemoteServer:
    name: str
    host: str
    username: str
    port: int = 22
    identity_file: str | None = None

    @classmethod
    def from_environment(cls, prefix: str = "SAREMBOK_SSH_") -> "RemoteServer":
        host = os.environ.get(f"{prefix}HOST")
        username = os.environ.get(f"{prefix}USER", "ubuntu")
        if not host:
            raise ValueError(f"{prefix}HOST is required")
        return cls(
            name=os.environ.get(f"{prefix}NAME", host),
            host=host,
            username=username,
            port=int(os.environ.get(f"{prefix}PORT", "22")),
            identity_file=os.environ.get(f"{prefix}IDENTITY_FILE"),
        )


@dataclass(frozen=True)
class RemoteResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "ok": self.returncode == 0,
        }


class RemoteTransport(Protocol):
    def run(self, command: str, *, timeout_seconds: float) -> RemoteResult: ...


class OpenSSHTransport:
    """OpenSSH transport with safe argument separation and no password capture."""

    def __init__(self, server: RemoteServer):
        self.server = server

    def run(self, command: str, *, timeout_seconds: float) -> RemoteResult:
        target = f"{self.server.username}@{self.server.host}"
        args = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UpdateHostkeys=no",
            "-p",
            str(self.server.port),
        ]
        if self.server.identity_file:
            args.extend(["-i", self.server.identity_file])
        args.extend([target, "--", command])
        completed = subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout_seconds)
        return RemoteResult(command, completed.returncode, completed.stdout[-8000:], completed.stderr[-8000:])


class RemoteTerminalTool:
    """Execute explicitly allowlisted commands on one configured server."""

    descriptor = ToolDescriptor(
        id="server.remote_terminal",
        version="1",
        capability_class="execute",
        required_permissions=frozenset({"server.connect", "server.execute"}),
        risk_level="external",
        supports_dry_run=True,
        provider="sarembok",
    )

    def __init__(self, transport: RemoteTransport, *, allowed_commands: Sequence[str], max_output_chars: int = 8000):
        self.transport = transport
        self.allowed_commands = tuple(allowed_commands)
        self.max_output_chars = max_output_chars

    def invoke(self, input: Mapping[str, Any], *, dry_run: bool = False) -> Mapping[str, Any]:
        command = str(input.get("command", "")).strip()
        if not command:
            raise ValueError("remote command is required")
        if not any(command == allowed or command.startswith(allowed + " ") for allowed in self.allowed_commands):
            raise PermissionError("remote command is not allowlisted")
        if dry_run:
            return {"dry_run": True, "command": command, "argv": shlex.split(command)}
        result = self.transport.run(command, timeout_seconds=float(input.get("timeout_seconds", 30)))
        output = result.as_dict()
        output["stdout"] = output["stdout"][-self.max_output_chars :]
        output["stderr"] = output["stderr"][-self.max_output_chars :]
        return output

