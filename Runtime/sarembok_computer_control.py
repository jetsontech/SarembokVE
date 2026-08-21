"""Safe, provider-neutral computer control adapter for Sarembok.

The adapter exposes inspection and explicitly permitted actions without
bypassing Sarembok's capability/policy layer. It is intentionally headless:
GUI-specific implementations can be added behind this interface later.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True)
class ComputerPolicy:
    allow_process_inspection: bool = True
    allow_system_inspection: bool = True
    allow_file_read: bool = False
    allow_file_write: bool = False
    allow_command_execution: bool = False
    allowed_roots: tuple[str, ...] = ()
    allowed_commands: tuple[str, ...] = ()


class SarembokComputerControl:
    """Local computer adapter with explicit policy gates."""

    def __init__(self, policy: Optional[ComputerPolicy] = None) -> None:
        self.policy = policy or ComputerPolicy()

    def inspect_system(self) -> Dict[str, Any]:
        self._require(self.policy.allow_system_inspection, "system_inspection")
        return {
            "platform": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        }

    def inspect_processes(self) -> Dict[str, Any]:
        self._require(self.policy.allow_process_inspection, "process_inspection")
        if platform.system() == "Windows":
            command: Sequence[str] = ["tasklist", "/FO", "CSV", "/NH"]
        else:
            command = ["ps", "-eo", "pid=,comm="]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return {"returncode": completed.returncode, "stdout": completed.stdout}

    def read_file(self, path: str) -> str:
        self._require(self.policy.allow_file_read, "file_read")
        target = self._safe_path(path)
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        self._require(self.policy.allow_file_write, "file_write")
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "bytes": len(content.encode("utf-8"))}

    def execute_command(self, command: Sequence[str]) -> Dict[str, Any]:
        self._require(self.policy.allow_command_execution, "command_execution")
        if not command or command[0] not in self.policy.allowed_commands:
            raise PermissionError("command_not_allowlisted")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _safe_path(self, path: str) -> Path:
        target = Path(path).expanduser().resolve()
        if not self.policy.allowed_roots:
            raise PermissionError("filesystem_root_not_configured")
        roots = [Path(root).expanduser().resolve() for root in self.policy.allowed_roots]
        if not any(target == root or root in target.parents for root in roots):
            raise PermissionError("path_outside_allowed_root")
        return target

    @staticmethod
    def _require(allowed: bool, capability: str) -> None:
        if not allowed:
            raise PermissionError(f"capability_not_permitted:{capability}")
