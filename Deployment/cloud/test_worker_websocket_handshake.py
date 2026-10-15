"""Verification test suite for Worker Client WebSocket Listener Handshake & P2P Execution."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from typing import Any

import websockets

from Deployment.cloud.worker_client import SarembokWorker


class TestWorkerWebSocketHandshake(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.port = 19842
        self.ws_url = f"ws://127.0.0.1:{self.port}/ws"
        self.enrollment_token = "valid-p2p-enrollment-token"
        self.received_rpcs: list[dict[str, Any]] = []
        self._original_token_file = os.environ.get("SAREMBOK_WORKER_TOKEN_FILE")
        self._token_temp_dir = tempfile.TemporaryDirectory()
        os.environ["SAREMBOK_WORKER_TOKEN_FILE"] = os.path.join(
            self._token_temp_dir.name, "worker-token.json"
        )

        async def handler(websocket):
            async for raw in websocket:
                data = json.loads(raw)
                self.received_rpcs.append(data)
                req_id = data.get("id")
                method = data.get("method")
                params = data.get("params", {})

                if method == "RegisterWorker":
                    # Verify enrollment token
                    supplied = params.get("enrollmentToken")
                    if supplied != self.enrollment_token:
                        err_resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": "unauthorized"}}
                        await websocket.send(json.dumps(err_resp))
                        continue

                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "workerId": params.get("workerId"),
                            "registered": True,
                            "status": "ONLINE",
                            "capabilities": params.get("capabilities", []),
                            "workerToken": "issued-p2p-worker-token-xyz789",
                        },
                    }
                    await websocket.send(json.dumps(resp))

                elif method == "Heartbeat":
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "workerId": params.get("workerId"),
                            "status": "ONLINE",
                            "lastHeartbeat": "2026-10-12T14:00:00Z",
                        },
                    }
                    await websocket.send(json.dumps(resp))

                elif method == "ListTasks":
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tasks": [],
                            "total": 0,
                        },
                    }
                    await websocket.send(json.dumps(resp))

                elif method == "ClaimTask":
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "taskId": params.get("taskId"),
                            "status": "CLAIMED",
                        },
                    }
                    await websocket.send(json.dumps(resp))

                elif method == "CompleteTask":
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "taskId": params.get("taskId"),
                            "status": "COMPLETED",
                        },
                    }
                    await websocket.send(json.dumps(resp))

        self.server = await websockets.serve(handler, "127.0.0.1", self.port)

    async def asyncTearDown(self) -> None:
        self.server.close()
        await self.server.wait_closed()
        if self._original_token_file is None:
            os.environ.pop("SAREMBOK_WORKER_TOKEN_FILE", None)
        else:
            os.environ["SAREMBOK_WORKER_TOKEN_FILE"] = self._original_token_file
        self._token_temp_dir.cleanup()

    async def test_01_verify_handshake_flow(self) -> None:
        worker = SarembokWorker(
            ws_url=self.ws_url,
            enrollment_token=self.enrollment_token,
            worker_id="p2p-test-worker-01",
        )

        report = await worker.verify_handshake()
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(report["handshake"], "PASS")
        self.assertEqual(report["workerId"], "p2p-test-worker-01")
        self.assertTrue(report["workerTokenIssued"])
        self.assertIn("compute", report["capabilities"])
        self.assertIn("mcp", report["capabilities"])

        # A new process instance must load the scoped token and reuse it instead
        # of attempting to re-enroll with the bootstrap-only enrollment token.
        restarted = SarembokWorker(
            ws_url=self.ws_url,
            enrollment_token=self.enrollment_token,
            worker_id="p2p-test-worker-01",
        )
        self.assertEqual(restarted.worker_token, "issued-p2p-worker-token-xyz789")
        _, reconnect_payload = restarted._rpc_request(
            "RegisterWorker", {"workerId": "p2p-test-worker-01"}
        )
        reconnect_params = json.loads(reconnect_payload)["params"]
        self.assertEqual(reconnect_params["workerToken"], "issued-p2p-worker-token-xyz789")
        self.assertNotIn("enrollmentToken", reconnect_params)

        # Confirm exact sequence of dispatched RPCs
        methods = [r.get("method") for r in self.received_rpcs]
        self.assertIn("RegisterWorker", methods)
        self.assertIn("Heartbeat", methods)
        self.assertIn("ListTasks", methods)

    async def test_02_task_execution_roundtrip(self) -> None:
        worker = SarembokWorker(
            ws_url=self.ws_url,
            enrollment_token=self.enrollment_token,
            worker_id="p2p-test-worker-02",
        )

        # Test local deterministic execution via worker executor
        res_calc = worker.execute_task_payload("compute", {"operation": "multiply", "a": 7, "b": 6})
        self.assertEqual(res_calc["status"], "COMPLETED")
        self.assertEqual(res_calc["result"], 42)

        # Test dynamic MCP execution
        res_mcp = worker.execute_task_payload("mcp_call", {"tool": "compute", "arguments": {"operation": "sum", "values": [10, 20, 30]}})
        self.assertEqual(res_mcp["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
