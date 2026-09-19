"""
Sarembok OS — JSON-RPC WebSocket bridge over the kernel-model simulation.

Exposes the syscall surface to the console UI. Serves both the WebSocket
JSON-RPC endpoint and the static console UI over HTTP.

Run: python3 sim/console_bridge.py [--http-port 8080] [--ws-port 9001]
Requires: pip install websockets
"""
import argparse
import asyncio
import http.server
import json
import os
import socketserver
import sys
import threading

sys.path.insert(0, os.path.dirname(__file__))
from kernel import Kernel  # noqa: E402

try:
    import websockets
except ImportError:
    websockets = None

CONSOLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "console")


class ConsoleHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CONSOLE_DIR, **kwargs)

    def do_GET(self):
        if self.path in ("", "/"):
            self.path = "/console.html"
        return super().do_GET()

    def log_message(self, format, *args):
        # Silence default request logging to avoid terminal spam
        pass


def _http_serve(host: str, port: int):
    # Allow socket reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, port), ConsoleHTTPHandler) as httpd:
        httpd.serve_forever()


class Bridge:
    def __init__(self, db_path: str):
        self.kernel = Kernel(db_path=db_path)

    async def handle(self, raw: str) -> str:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError as e:
            return json.dumps({"jsonrpc": "2.0", "id": None,
                               "error": {"code": -32700, "message": str(e)}})
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params", {}) or {}
        try:
            result = self._dispatch(method, params)
            return json.dumps({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception as e:
            return json.dumps({"jsonrpc": "2.0", "id": rid,
                               "error": {"code": -32000, "message": str(e)}})

    def _dispatch(self, method: str, p: dict):
        k = self.kernel
        if method == "GetRuntimeInfo":
            return k.get_runtime_info()
        if method == "SpawnAgent":
            return {"agent_id": k.spawn_agent(p["name"],
                                              p.get("capabilities",
                                                    ["recall", "remember", "embody"]))}
        if method == "AgentRemember":
            mid = k.remember(int(p["agentId"]), p["key"], p["value"],
                             p.get("tier", "SEMANTIC"))
            return {"mem_id": mid}
        if method == "AgentRecall":
            refs = k.recall(int(p["agentId"]), p["query"],
                            int(p.get("max", 64)))
            return {"refs": [{"mem_id": e.id, "key": e.key,
                              "value": e.value, "tier": e.tier.name}
                             for e in refs]}
        if method == "ListMemories":
            mems = []
            for owner, arena in k._arenas.items():
                for e in arena.entries.values():
                    mems.append({
                        "id": e.id,
                        "owner": owner,
                        "key": e.key,
                        "value": e.value,
                        "tier": e.tier.name,
                        "created_ns": e.created_ns,
                        "last_access_ns": e.last_access_ns,
                        "access_count": e.access_count,
                    })
            return {"memories": mems}
        if method == "AgentKill":
            k.kill_agent(int(p["agentId"]))
            return {"status": "DEAD"}
        if method == "AgentRestore":
            k.restore_agent(int(p["agentId"]))
            return {"status": "RUNNING"}
        if method == "ListAgents":
            return {"agents": [{"id": a.id, "name": a.name,
                                "state": a.state.name}
                               for a in k.list_agents()]}
        if method == "Dmesg":
            return {"log": k.dmesg(int(p.get("n", 20)))}
        raise ValueError(f"unknown method: {method}")


async def _serve(host: str, ws_port: int, db_path: str):
    bridge = Bridge(db_path)

    async def handler(ws):
        async for msg in ws:
            reply = await bridge.handle(msg)
            await ws.send(reply)

    async with websockets.serve(handler, host, ws_port):
        print(f"[ws] Sarembok WebSocket bridge at ws://{host}:{ws_port}")
        print("[ws] serving JSON-RPC — see docs/SYSCALLS.md")
        await asyncio.Future()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--ws-port", "--port", type=int, default=9001, dest="ws_port")
    ap.add_argument("--http-port", type=int, default=8080)
    ap.add_argument("--db", "--wal", default="sarembok.db", dest="db")
    args = ap.parse_args()

    if websockets is None:
        print("error: pip install websockets", file=sys.stderr)
        sys.exit(1)

    os.makedirs(CONSOLE_DIR, exist_ok=True)
    http_thread = threading.Thread(
        target=_http_serve, args=(args.host, args.http_port), daemon=True
    )
    http_thread.start()
    print(f"[http] Sarembok console serving at http://{args.host}:{args.http_port}")

    asyncio.run(_serve(args.host, args.ws_port, args.db))


if __name__ == "__main__":
    main()
