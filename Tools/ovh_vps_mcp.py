#!/usr/bin/env python3
"""Sarembok OVH VPS Model Context Protocol (MCP) Server.

Exposes the live Sarembok OVH production VPS (15.204.173.205) to ChatGPT,
Claude, Antigravity, and any MCP-compliant client with full SSH and terminal actions:
- Command execution (vps_execute_command)
- File read (vps_read_file)
- File write (vps_write_file)
- Docker container management (vps_docker_action)
- System telemetry and resource metrics (vps_get_telemetry)

Transport modes supported:
1. stdio (default) - For ChatGPT Desktop, Claude Desktop, Cursor, Zed, Antigravity
2. HTTP / SSE - For remote MCP connectors or network-bridged clients (--http --port 8080)
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Logging to stderr so stdin/stdout remain clean for MCP JSON-RPC messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
LOG = logging.getLogger("ovh-vps-mcp")

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "sarembok-ovh-vps"
SERVER_VERSION = "1.0.0"

# Default SSH Configuration for Sarembok OVH VPS
DEFAULT_VPS_HOST = os.environ.get("OVH_VPS_HOST", "15.204.173.205")
DEFAULT_VPS_USER = os.environ.get("OVH_VPS_USER", "ubuntu")
DEFAULT_KEY_PATH = os.environ.get(
    "OVH_VPS_KEY",
    os.path.expanduser(r"~/.ssh/sarembok_agent"),
)

TOOLS_MANIFEST: List[Dict[str, Any]] = [
    {
        "name": "vps_execute_command",
        "description": "Execute any shell command directly on the live Sarembok OVH VPS (15.204.173.205). Returns stdout, stderr, and exit code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell/bash command to execute on the VPS (e.g., 'docker ps', 'git status', 'tail -n 50 /var/log/syslog')",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory on the VPS (defaults to /home/ubuntu/SarembokVE)",
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": "Maximum execution time in seconds (default: 60)",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "vps_read_file",
        "description": "Read the text contents of a file on the OVH VPS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative file path on the VPS to read (e.g., '/home/ubuntu/SarembokVE/Deployment/cloud/compose.yaml')",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Optional maximum number of lines to return from the file (default: 500)",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "vps_write_file",
        "description": "Write or overwrite a file on the OVH VPS with provided content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute file path on the VPS where the file will be written",
                },
                "content": {
                    "type": "string",
                    "description": "Full text content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "vps_docker_action",
        "description": "Inspect and manage Docker containers running on the OVH VPS (sarembok-runtime, sarembok-edge, sarembok-voice, sarembok-browser).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ps", "logs", "restart", "top", "stats"],
                    "description": "Docker operation to perform: 'ps' (list containers), 'logs' (view logs), 'restart' (restart container), 'top' (process list), 'stats' (resource usage)",
                },
                "container": {
                    "type": "string",
                    "description": "Target container name (e.g. 'sarembok-runtime', 'sarembok-edge', 'sarembok-voice', 'sarembok-browser')",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve (default: 100)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "vps_get_telemetry",
        "description": "Retrieve live hardware, kernel, container health, and resource metrics from the OVH VPS.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class OVHVPSController:
    """Handles low-level SSH operations to the Sarembok OVH VPS."""

    def __init__(
        self,
        host: str = DEFAULT_VPS_HOST,
        user: str = DEFAULT_VPS_USER,
        key_path: str = DEFAULT_KEY_PATH,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = os.path.expanduser(key_path)

    def _build_ssh_command(self, remote_command: str) -> List[str]:
        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
        ]
        if os.path.exists(self.key_path):
            cmd.extend(["-i", self.key_path])
        cmd.append(f"{self.user}@{self.host}")
        cmd.append(remote_command)
        return cmd

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Execute a command over SSH."""
        working_dir = cwd or "/home/ubuntu/SarembokVE"
        full_remote = f"cd {working_dir} && {command}"
        ssh_cmd = self._build_ssh_command(full_remote)

        LOG.info("Executing on %s: %s", self.host, command[:120])
        try:
            res = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "success": res.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "success": False,
            }
        except Exception as exc:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "success": False,
            }

    def read_file(self, path: str, max_lines: int = 500) -> Dict[str, Any]:
        """Read a file on the VPS via SSH."""
        cmd = f"head -n {max_lines} '{path}'"
        res = self.execute(cmd, cwd="/")
        if not res["success"]:
            return {"error": res["stderr"] or "Failed to read file", "path": path}
        return {"path": path, "content": res["stdout"], "truncated": False}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file on the VPS using base64 encoding to preserve formatting."""
        b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        cmd = f"echo '{b64_content}' | base64 -d > '{path}'"
        res = self.execute(cmd, cwd="/")
        if not res["success"]:
            return {"error": res["stderr"] or "Failed to write file", "path": path, "success": False}
        return {"success": True, "path": path, "bytes_written": len(content)}

    def docker_action(
        self,
        action: str,
        container: Optional[str] = None,
        tail: int = 100,
    ) -> Dict[str, Any]:
        """Run docker actions on the VPS."""
        if action == "ps":
            return self.execute("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        elif action == "logs":
            target = container or "sarembok-runtime"
            return self.execute(f"docker logs --tail {tail} {target}")
        elif action == "restart":
            if not container:
                return {"error": "Container name is required for restart action", "success": False}
            return self.execute(f"docker restart {container}")
        elif action == "top":
            target = container or "sarembok-runtime"
            return self.execute(f"docker top {target}")
        elif action == "stats":
            return self.execute("docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'")
        else:
            return {"error": f"Unknown docker action: {action}", "success": False}

    def get_telemetry(self) -> Dict[str, Any]:
        """Collect comprehensive VPS health telemetry."""
        cmds = (
            "echo '=== UPTIME ===' && uptime && "
            "echo '=== MEMORY ===' && free -h && "
            "echo '=== DISK ===' && df -h / && "
            "echo '=== DOCKER CONTAINERS ===' && docker ps --format 'table {{.Names}}\t{{.Status}}' && "
            "echo '=== CPU LOAD ===' && nproc && top -bn1 | head -n 5"
        )
        res = self.execute(cmds, cwd="/")
        return {"host": self.host, "telemetry": res["stdout"], "success": res["success"]}


def handle_tool_call(controller: OVHVPSController, tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute the requested tool and return a JSON-serializable structure."""
    if tool_name == "vps_execute_command":
        cmd = args.get("command", "")
        cwd = args.get("cwd")
        timeout = float(args.get("timeout_seconds", 60.0))
        return controller.execute(cmd, cwd=cwd, timeout=timeout)

    elif tool_name == "vps_read_file":
        path = args.get("path", "")
        max_lines = int(args.get("max_lines", 500))
        return controller.read_file(path, max_lines=max_lines)

    elif tool_name == "vps_write_file":
        path = args.get("path", "")
        content = args.get("content", "")
        return controller.write_file(path, content)

    elif tool_name == "vps_docker_action":
        action = args.get("action", "ps")
        container = args.get("container")
        tail = int(args.get("tail", 100))
        return controller.docker_action(action, container=container, tail=tail)

    elif tool_name == "vps_get_telemetry":
        return controller.get_telemetry()

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def run_stdio_server(controller: OVHVPSController) -> None:
    """Run MCP server over standard input/output (stdio transport)."""
    LOG.info("Starting Sarembok OVH VPS MCP Server in stdio mode...")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            print(json.dumps(err_resp), flush=True)
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
            print(json.dumps(resp), flush=True)

        elif method == "notifications/initialized":
            LOG.info("Client completed initialization handshake.")

        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            print(json.dumps(resp), flush=True)

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_MANIFEST},
            }
            print(json.dumps(resp), flush=True)

        elif method == "tools/call":
            params = req.get("params") or {}
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}

            try:
                result_data = handle_tool_call(controller, tool_name, arguments)
                text_content = (
                    json.dumps(result_data, indent=2)
                    if not isinstance(result_data, str)
                    else result_data
                )
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_content}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                LOG.error("Tool execution failed for %s: %s", tool_name, exc)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exc}"}],
                        "isError": True,
                    },
                }
            print(json.dumps(resp), flush=True)

        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
            print(json.dumps(resp), flush=True)


def run_http_server(controller: OVHVPSController, port: int = 8080) -> None:
    """Run MCP server over HTTP POST / JSON-RPC endpoint."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class MCPHttpHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def do_GET(self):
            if self.path in ("/", "/health"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ONLINE",
                    "mcp_server": SERVER_NAME,
                    "tools": len(TOOLS_MANIFEST),
                }).encode("utf-8"))
            elif self.path == "/mcp/tools":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"tools": TOOLS_MANIFEST}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path not in ("/", "/mcp", "/rpc"):
                self.send_response(404)
                self.end_headers()
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                req = json.loads(body)
            except Exception as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {exc}"}).encode("utf-8"))
                return

            method = req.get("method")
            req_id = req.get("id")

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                        "capabilities": {"tools": {}},
                    },
                }
            elif method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_MANIFEST}}
            elif method == "tools/call":
                params = req.get("params") or {}
                tool_name = params.get("name", "")
                args = params.get("arguments") or {}
                try:
                    res = handle_tool_call(controller, tool_name, args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(res, indent=2)}],
                            "isError": False,
                        },
                    }
                except Exception as exc:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                    }
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

    server = HTTPServer(("0.0.0.0", port), MCPHttpHandler)
    LOG.info("Sarembok OVH VPS MCP HTTP Server listening on port %d...", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Server terminated by user.")


def main():
    parser = argparse.ArgumentParser(description="Sarembok OVH VPS MCP Server")
    parser.add_argument("--host", default=DEFAULT_VPS_HOST, help="VPS IP/hostname (default: 15.204.173.205)")
    parser.add_argument("--user", default=DEFAULT_VPS_USER, help="SSH user (default: ubuntu)")
    parser.add_argument("--key", default=DEFAULT_KEY_PATH, help="SSH private key path")
    parser.add_argument("--http", action="store_true", help="Run HTTP server instead of stdio")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    args = parser.parse_args()

    controller = OVHVPSController(host=args.host, user=args.user, key_path=args.key)

    if args.http:
        run_http_server(controller, port=args.port)
    else:
        run_stdio_server(controller)


if __name__ == "__main__":
    main()
