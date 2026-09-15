"""Sarembok External Model Context Protocol (MCP) Client Manager.

Connects Sarembok to external MCP servers via HTTP/SSE or stdio, discovers
available tools, and exposes them through the unified SkillsEngine.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sarembok.mcp_client")

# Keep the legacy wire version for compatibility with currently configured
# servers. The capability layer is transport-neutral and can be upgraded to
# newer MCP transports independently.
MCP_CLIENT_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_MCP_CONFIG_PATH = Path(__file__).parent / "mcp_servers.json"


@dataclass
class ExternalMcpServer:
    name: str
    transport: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 15.0
    status: str = "DISCONNECTED"
    tools: list[dict[str, Any]] = field(default_factory=list)
    last_error: str = ""
    last_synced: float = 0.0
    description: str = ""


class MCPClientManager:
    """Manage external MCP servers and provide a unified tool-call interface."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = Path(config_path or DEFAULT_MCP_CONFIG_PATH)
        self.servers: dict[str, ExternalMcpServer] = {}
        self.load_configuration()

    @staticmethod
    def _resolve_env(value: Any) -> str:
        return os.path.expandvars(str(value)) if value is not None else ""

    @staticmethod
    def _looks_like_sqlite_shell(cfg: dict[str, Any]) -> bool:
        command = str(cfg.get("command", "")).lower()
        args = [str(v).lower() for v in cfg.get("args", [])]
        return command in {"python", "python3", "py"} and "-m" in args and "sqlite3" in args

    def _validate_config(self, name: str, cfg: dict[str, Any]) -> tuple[bool, str]:
        transport = cfg.get("transport", "stdio" if "command" in cfg else "http")
        if transport not in {"http", "sse", "stdio"}:
            return False, f"unsupported transport '{transport}'"
        if transport == "stdio" and not cfg.get("command"):
            return False, "stdio MCP server requires command"
        if transport in {"http", "sse"} and not cfg.get("url"):
            return False, "HTTP/SSE MCP server requires url"
        if self._looks_like_sqlite_shell(cfg):
            return False, "python -m sqlite3 is a SQLite shell, not an MCP server"
        return True, ""

    def load_configuration(self) -> None:
        if not self.config_path.exists():
            self._write_default_config()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.servers.clear()
            for name, cfg in data.get("mcpServers", {}).items():
                valid, error = self._validate_config(name, cfg)
                if not valid:
                    logger.warning("Ignoring invalid MCP server '%s': %s", name, error)
                    continue
                transport = cfg.get("transport", "stdio" if "command" in cfg else "http")
                resolved_env = {k: self._resolve_env(v) for k, v in (cfg.get("env") or {}).items()}
                resolved_headers = {k: self._resolve_env(v) for k, v in (cfg.get("headers") or {}).items()}
                self.servers[name] = ExternalMcpServer(
                    name=name,
                    transport=transport,
                    command=self._resolve_env(cfg.get("command", "")),
                    args=[self._resolve_env(v) for v in cfg.get("args", [])],
                    env=resolved_env,
                    url=self._resolve_env(cfg.get("url", "")),
                    headers=resolved_headers,
                    timeout_seconds=float(cfg.get("timeout", 15.0)),
                    description=str(cfg.get("description", "")),
                )
            logger.info("Loaded %d valid external MCP server configs from %s", len(self.servers), self.config_path)
        except Exception as exc:
            logger.warning("Failed to load MCP server configuration: %s", exc)

    def _write_default_config(self) -> None:
        default_config = {
            "mcpServers": {
                "brave-search": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@brave/brave-search-mcp-server"],
                    "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
                    "description": "Brave-maintained real-time web search MCP server",
                },
                "memory-hub": {
                    "transport": "http",
                    "url": "http://127.0.0.1:8000/mcp",
                    "description": "Sarembok native episodic memory MCP connector",
                },
            }
        }
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
        except Exception as exc:
            logger.warning("Could not write default mcp_servers.json: %s", exc)

    def register_server(
        self,
        name: str,
        transport: str = "http",
        url: str = "",
        command: str = "",
        args: list[str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        cfg = {"transport": transport, "url": url, "command": command, "args": args or []}
        valid, error = self._validate_config(name, cfg)
        if not valid:
            raise ValueError(f"Invalid MCP server '{name}': {error}")
        server = ExternalMcpServer(
            name=name,
            transport=transport,
            url=url,
            command=command,
            args=args or [],
            headers=headers or {},
            timeout_seconds=timeout,
        )
        self.servers[name] = server
        self.sync_server_tools(name)
        return self.get_server_status(name)

    def get_server_status(self, name: str) -> dict[str, Any]:
        server = self.servers.get(name)
        if not server:
            return {"name": name, "status": "NOT_FOUND"}
        return {
            "name": server.name,
            "transport": server.transport,
            "status": server.status,
            "toolCount": len(server.tools),
            "tools": [t.get("name") for t in server.tools],
            "lastError": server.last_error,
            "lastSynced": server.last_synced,
        }

    def list_servers(self) -> list[dict[str, Any]]:
        return [self.get_server_status(name) for name in self.servers]

    def sync_server_tools(self, name: str) -> list[dict[str, Any]]:
        server = self.servers.get(name)
        if not server:
            raise ValueError(f"MCP server '{name}' not found")
        try:
            if server.transport in ("http", "sse"):
                tools = self._sync_http_server(server)
            elif server.transport == "stdio":
                tools = self._sync_stdio_server(server)
            else:
                raise ValueError(f"Unsupported transport: {server.transport}")
            server.tools = tools
            server.status = "CONNECTED"
            server.last_error = ""
            server.last_synced = time.time()
            return tools
        except Exception as exc:
            server.status = "ERROR"
            server.last_error = str(exc)
            logger.warning("Failed to sync MCP server '%s': %s", name, exc)
            return []

    def _sync_http_server(self, server: ExternalMcpServer) -> list[dict[str, Any]]:
        if not server.url:
            return []
        init_payload = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": MCP_CLIENT_PROTOCOL_VERSION,
                "clientInfo": {"name": "sarembok-mcp-client", "version": "2.0.0"},
                "capabilities": {},
            },
        }
        self._post_http_rpc(server.url, init_payload, server.headers, server.timeout_seconds)
        tools_payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        res = self._post_http_rpc(server.url, tools_payload, server.headers, server.timeout_seconds)
        return res.get("result", {}).get("tools", [])

    def _sync_stdio_server(self, server: ExternalMcpServer) -> list[dict[str, Any]]:
        if not server.command:
            return []
        cmd = [server.command] + server.args
        init_req = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": MCP_CLIENT_PROTOCOL_VERSION,
                "clientInfo": {"name": "sarembok-mcp-client", "version": "2.0.0"},
                "capabilities": {},
            },
        }) + "\n"
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env={**os.environ, **server.env}, shell=False,
        )
        try:
            stdout_data, _ = proc.communicate(input=init_req + list_req, timeout=server.timeout_seconds)
            for line in stdout_data.splitlines():
                try:
                    resp = json.loads(line.strip())
                    if resp.get("id") == 2 and "result" in resp:
                        return resp["result"].get("tools", [])
                except Exception:
                    continue
            return []
        finally:
            if proc.poll() is None:
                proc.kill()

    def _post_http_rpc(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        all_headers = {"Content-Type": "application/json", "Accept": "application/json", **headers}
        req = urllib.request.Request(url, data=data, headers=all_headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def call_external_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        server = self.servers.get(server_name)
        if not server:
            raise ValueError(f"MCP server '{server_name}' not configured")
        if not any(t.get("name") == tool_name for t in server.tools):
            raise ValueError(f"MCP tool '{tool_name}' was not discovered on server '{server_name}'")

        call_id = int(time.time() * 1000) % 1000000
        call_payload = {
            "jsonrpc": "2.0", "id": call_id, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        if server.transport in ("http", "sse"):
            res = self._post_http_rpc(server.url, call_payload, server.headers, server.timeout_seconds)
        elif server.transport == "stdio":
            proc = subprocess.Popen(
                [server.command] + server.args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env={**os.environ, **server.env}, shell=False,
            )
            try:
                stdout_data, stderr_data = proc.communicate(input=json.dumps(call_payload) + "\n", timeout=server.timeout_seconds)
                res = None
                for line in stdout_data.splitlines():
                    try:
                        parsed = json.loads(line.strip())
                        if parsed.get("id") == call_id:
                            res = parsed
                            break
                    except Exception:
                        continue
                if res is None:
                    raise RuntimeError(f"Stdio MCP response parse failed: {stderr_data}")
            finally:
                if proc.poll() is None:
                    proc.kill()
        else:
            raise ValueError(f"Unsupported transport: {server.transport}")

        if "error" in res:
            raise RuntimeError(f"MCP error from {server_name}: {res['error'].get('message')}")
        return res.get("result", {})

    def get_all_external_tools(self) -> list[dict[str, Any]]:
        unified: list[dict[str, Any]] = []
        for server_name, server in self.servers.items():
            for tool in server.tools:
                namespaced_tool = dict(tool)
                original_name = tool.get("name", "tool")
                namespaced_tool["name"] = f"mcp_{server_name}_{original_name}"
                namespaced_tool["mcp_server"] = server_name
                namespaced_tool["mcp_original_name"] = original_name
                unified.append(namespaced_tool)
        return unified


_MCP_CLIENT_MANAGER: MCPClientManager | None = None


def get_mcp_client_manager() -> MCPClientManager:
    global _MCP_CLIENT_MANAGER
    if _MCP_CLIENT_MANAGER is None:
        _MCP_CLIENT_MANAGER = MCPClientManager()
    return _MCP_CLIENT_MANAGER


def set_mcp_client_manager(manager: MCPClientManager | None) -> None:
    global _MCP_CLIENT_MANAGER
    _MCP_CLIENT_MANAGER = manager
