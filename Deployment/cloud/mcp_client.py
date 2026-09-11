"""Sarembok External Model Context Protocol (MCP) Client Manager.

Enables Sarembok to act as an MCP Client connecting to external MCP servers
(via HTTP/SSE or stdio subprocesses), dynamically discovering their tools,
and exposing them directly into Sarembok's unified SkillsEngine and LLM tool calling loops.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sarembok.mcp_client")

MCP_CLIENT_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_MCP_CONFIG_PATH = Path(__file__).parent / "mcp_servers.json"


@dataclass
class ExternalMcpServer:
    name: str
    transport: str  # "http", "sse", or "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 15.0
    status: str = "DISCONNECTED"  # "CONNECTED", "ERROR", "DISCONNECTED"
    tools: list[dict[str, Any]] = field(default_factory=list)
    last_error: str = ""
    last_synced: float = 0.0


class MCPClientManager:
    """Manages connections to external MCP servers and provides a unified tool calling interface."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = Path(config_path or DEFAULT_MCP_CONFIG_PATH)
        self.servers: dict[str, ExternalMcpServer] = {}
        self.load_configuration()

    def load_configuration(self) -> None:
        """Load external MCP server configurations from mcp_servers.json."""
        if not self.config_path.exists():
            # Create default template if it doesn't exist
            self._write_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            mcp_servers = data.get("mcpServers", {})
            for name, cfg in mcp_servers.items():
                transport = cfg.get("transport", "stdio" if "command" in cfg else "http")
                server = ExternalMcpServer(
                    name=name,
                    transport=transport,
                    command=cfg.get("command", ""),
                    args=cfg.get("args", []),
                    env=cfg.get("env", {}),
                    url=cfg.get("url", ""),
                    headers=cfg.get("headers", {}),
                    timeout_seconds=float(cfg.get("timeout", 15.0)),
                )
                self.servers[name] = server
            logger.info("Loaded %d external MCP server configs from %s", len(self.servers), self.config_path)
        except Exception as exc:
            logger.warning("Failed to load MCP server configuration: %s", exc)

    def _write_default_config(self) -> None:
        """Create a standard template for external MCP integrations."""
        default_config = {
            "mcpServers": {
                "sqlite": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "sqlite3"],
                    "description": "Local SQLite database querying and inspection MCP server"
                },
                "brave-search": {
                    "transport": "http",
                    "url": "https://api.search.brave.com/res/v1/web/search",
                    "description": "Frontier web search MCP connector"
                }
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
        """Dynamically add or update an external MCP server."""
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
        """Return operational telemetry for a configured server."""
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
        """List all configured external MCP servers and their current status."""
        return [self.get_server_status(name) for name in self.servers]

    def sync_server_tools(self, name: str) -> list[dict[str, Any]]:
        """Perform MCP initialize and tools/list against the target external server."""
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
        """Sync tools from an HTTP/SSE JSON-RPC 2.0 MCP server."""
        if not server.url:
            return []

        # 1. Initialize Handshake
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_CLIENT_PROTOCOL_VERSION,
                "clientInfo": {"name": "sarembok-mcp-client", "version": "1.0.0"},
                "capabilities": {}
            }
        }
        self._post_http_rpc(server.url, init_payload, server.headers, server.timeout_seconds)

        # 2. Tools List Request
        tools_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        res = self._post_http_rpc(server.url, tools_payload, server.headers, server.timeout_seconds)
        result = res.get("result", {})
        return result.get("tools", [])

    def _sync_stdio_server(self, server: ExternalMcpServer) -> list[dict[str, Any]]:
        """Sync tools from a stdio MCP subprocess."""
        if not server.command:
            return []

        # Validate command or test availability
        cmd = [server.command] + server.args
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_CLIENT_PROTOCOL_VERSION,
                "clientInfo": {"name": "sarembok-mcp-client", "version": "1.0.0"}
            }
        }) + "\n"
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, **server.env}
        )
        try:
            stdout_data, _ = proc.communicate(input=init_req + list_req, timeout=server.timeout_seconds)
            tools: list[dict[str, Any]] = []
            for line in stdout_data.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    resp = json.loads(line)
                    if resp.get("id") == 2 and "result" in resp:
                        tools.extend(resp["result"].get("tools", []))
                except Exception:
                    continue
            return tools
        finally:
            if proc.poll() is None:
                proc.kill()

    def _post_http_rpc(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        """Issue a JSON-RPC 2.0 POST request."""
        data = json.dumps(payload).encode("utf-8")
        all_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **headers
        }
        req = urllib.request.Request(url, data=data, headers=all_headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)

    def call_external_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool on an external MCP server via JSON-RPC 2.0 tools/call."""
        server = self.servers.get(server_name)
        if not server:
            raise ValueError(f"MCP server '{server_name}' not configured")

        call_payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000) % 1000000,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            }
        }

        if server.transport in ("http", "sse"):
            res = self._post_http_rpc(server.url, call_payload, server.headers, server.timeout_seconds)
        elif server.transport == "stdio":
            cmd = [server.command] + server.args
            req_str = json.dumps(call_payload) + "\n"
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, **server.env}
            )
            try:
                stdout_data, stderr_data = proc.communicate(input=req_str, timeout=server.timeout_seconds)
                res = None
                for line in stdout_data.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        if parsed.get("id") == call_payload["id"]:
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
        """Collect all external tools with namespace metadata for OpenAI tool schema generation."""
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
    """Singleton getter for MCPClientManager."""
    global _MCP_CLIENT_MANAGER
    if _MCP_CLIENT_MANAGER is None:
        _MCP_CLIENT_MANAGER = MCPClientManager()
    return _MCP_CLIENT_MANAGER


def set_mcp_client_manager(manager: MCPClientManager | None) -> None:
    """Setter for global MCPClientManager singleton (useful for testing and injection)."""
    global _MCP_CLIENT_MANAGER
    _MCP_CLIENT_MANAGER = manager

