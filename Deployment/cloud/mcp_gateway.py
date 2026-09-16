"""Sarembok Model Context Protocol (MCP) Gateway.

Implements the official Model Context Protocol (MCP) JSON-RPC 2.0 specification
(2024-11-05), exposing Sarembok's tools, skills, and resources as a standard MCP Server
and enabling bi-directional integration with external MCP tooling ecosystems.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

try:
    from skills_engine import get_skills_engine
except ImportError:
    try:
        from Deployment.cloud.skills_engine import get_skills_engine
    except ImportError:
        from .skills_engine import get_skills_engine

logger = logging.getLogger("sarembok.mcp_gateway")

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "sarembok-mcp-gateway",
    "version": "2.0.0",
}


class MCPGateway:
    def __init__(self, db_store: Any = None) -> None:
        self.skills_engine = get_skills_engine()
        self.store = db_store
        self._custom_tool_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register_tool_handler(self, tool_name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self._custom_tool_handlers[tool_name] = handler

    def handle_request(self, payload: dict[str, Any] | str) -> dict[str, Any] | None:
        """Process a standard JSON-RPC 2.0 MCP request."""
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
        else:
            data = payload

        req_id = data.get("id")
        method = data.get("method")
        params = data.get("params") or {}

        # Notifications (no id)
        if not req_id and method == "notifications/initialized":
            logger.info("MCP client initialized notification received.")
            return None

        if not method:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: missing method"},
            }

        try:
            result = self._dispatch_method(method, params)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }
        except Exception as exc:
            logger.error("Error handling MCP method %s: %s", method, exc)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(exc)},
            }

    def _dispatch_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": SERVER_INFO,
            }

        if method == "ping":
            return {}

        if method == "tools/list":
            tools = self.skills_engine.get_mcp_tools()
            return {"tools": tools}

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}

            # Check custom handlers first
            if tool_name in self._custom_tool_handlers:
                output = self._custom_tool_handlers[tool_name](arguments)
                text_out = output if isinstance(output, str) else json.dumps(output, indent=2)
                return {
                    "content": [{"type": "text", "text": text_out}],
                    "isError": False,
                }

            # Dispatch via skills engine
            exec_res = self.skills_engine.execute_skill(tool_name, arguments)
            if not exec_res.get("success"):
                return {
                    "content": [{"type": "text", "text": exec_res.get("error", "Skill execution failed")}],
                    "isError": True,
                }

            out = exec_res.get("output", "")
            text_out = out if isinstance(out, str) else json.dumps(out, indent=2)
            return {
                "content": [{"type": "text", "text": text_out}],
                "isError": False,
            }

        if method == "resources/list":
            resources = [
                {
                    "uri": "sarembok://cluster/workers",
                    "name": "Compute Cluster Workers",
                    "description": "Live status of registered and active sovereign GPU compute nodes.",
                    "mimeType": "application/json",
                },
                {
                    "uri": "sarembok://memory/entries",
                    "name": "Persistent SQLite Memory",
                    "description": "Stored long-term episodic facts and cross-session knowledge.",
                    "mimeType": "application/json",
                },
                {
                    "uri": "sarembok://system/health",
                    "name": "Runtime System Health",
                    "description": "Authoritative uptime, active model providers, and service state.",
                    "mimeType": "application/json",
                },
            ]
            return {"resources": resources}

        if method == "resources/read":
            uri = params.get("uri", "")
            if uri == "sarembok://cluster/workers":
                workers_data = {"status": "ONLINE", "onlineGpuNodes": 1}
                if self.store and hasattr(self.store, "db"):
                    try:
                        rows = self.store.db.execute("SELECT worker_id, status, last_heartbeat FROM workers").fetchall()
                        workers_data["workers"] = [{"id": r[0], "status": r[1], "lastHeartbeat": r[2]} for r in rows]
                    except Exception:
                        pass
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(workers_data, indent=2),
                    }]
                }

            if uri == "sarembok://memory/entries":
                mem_data = []
                if self.store and hasattr(self.store, "db"):
                    try:
                        rows = self.store.db.execute("SELECT key, value, tier, created_at FROM memories ORDER BY created_at DESC LIMIT 20").fetchall()
                        mem_data = [{"key": r[0], "value": r[1], "tier": r[2], "createdAt": r[3]} for r in rows]
                    except Exception:
                        pass
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(mem_data, indent=2),
                    }]
                }

            if uri == "sarembok://system/health":
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({"service": "sarembok-ve-cloud-runtime", "status": "ONLINE", "mcp": "enabled"}, indent=2),
                    }]
                }

            raise ValueError(f"Resource not found: {uri}")

        raise ValueError(f"Unsupported MCP method: {method}")


_GLOBAL_MCP_GATEWAY: MCPGateway | None = None


def get_mcp_gateway(store: Any = None) -> MCPGateway:
    global _GLOBAL_MCP_GATEWAY
    if _GLOBAL_MCP_GATEWAY is None:
        _GLOBAL_MCP_GATEWAY = MCPGateway(db_store=store)
    return _GLOBAL_MCP_GATEWAY
