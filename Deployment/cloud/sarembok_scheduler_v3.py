"""Small async worker SDK for the Sarembok Scheduler V3 JSON-RPC channel."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import websockets


class SarembokSchedulerV3Client:
    def __init__(self, uri: str, auth_token: str, worker_id: str | None = None, **worker):
        self.uri = uri
        self.auth_token = auth_token
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:12]}"
        self.worker = worker
        self.ws = None
        self._next_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.uri, ping_interval=20, ping_timeout=20, max_size=1024 * 1024)
        await self.call("RegisterWorkerV3", {"workerId": self.worker_id, **self.worker})
        return self

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("client_not_connected")
        self._next_id += 1
        body = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": dict(params or {})}
        body["params"]["authToken"] = self.auth_token
        await self.ws.send(json.dumps(body, separators=(",", ":")))
        response = json.loads(await self.ws.recv())
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

    async def heartbeat(self):
        return await self.call("HeartbeatV3", {"workerId": self.worker_id})

    async def schedule(self, task_type: str, capability: str, payload: Any, *, idempotency_key: str | None = None, max_attempts: int = 3):
        p = {"taskType": task_type, "requiredCapability": capability, "payload": payload, "maxAttempts": max_attempts}
        if idempotency_key:
            p["idempotencyKey"] = idempotency_key
        return await self.call("ScheduleComputeV3", p)

    async def claim(self, task_id: str):
        return await self.call("ClaimTaskV3", {"taskId": task_id, "workerId": self.worker_id})

    async def complete(self, task_id: str, result: Any = None):
        return await self.call("CompleteTaskV3", {"taskId": task_id, "workerId": self.worker_id, "result": result})

    async def fail(self, task_id: str, error: str):
        return await self.call("FailTask", {"taskId": task_id, "workerId": self.worker_id, "error": error})

    async def run_heartbeat_loop(self, interval: float = 30.0):
        while True:
            await self.heartbeat()
            await asyncio.sleep(interval)
