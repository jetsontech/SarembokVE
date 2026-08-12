"""Public WSS Scheduler V3 lifecycle smoke test.

Usage requires SAREMBOK_PUBLIC_WSS_URI and SAREMBOK_AUTH_TOKEN.
The script never prints the token.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import websockets


async def main():
    uri = os.environ.get("SAREMBOK_PUBLIC_WSS_URI", "wss://sarembok.com/")
    token = os.environ.get("SAREMBOK_AUTH_TOKEN", "").strip()
    if not token:
        raise SystemExit("SAREMBOK_AUTH_TOKEN is required")

    worker = f"public-scheduler-v3-{uuid.uuid4().hex[:8]}"
    request_id = 0

    async with websockets.connect(uri, ping_interval=20, ping_timeout=20, max_size=1024 * 1024) as ws:
        async def rpc(method, params):
            nonlocal request_id
            request_id += 1
            body = {"jsonrpc":"2.0","id":request_id,"method":method,"params":{**params,"authToken":token}}
            await ws.send(__import__("json").dumps(body,separators=(",",":")))
            response = __import__("json").loads(await ws.recv())
            if "error" in response:
                raise RuntimeError(f"{method}: {response['error']}")
            return response["result"]

        reg = await rpc("RegisterWorkerV3", {"workerId":worker,"capabilities":["compute","inference"],"gpuVendor":"NVIDIA","gpuModel":"SCHEDULER-V3-SMOKE","vramMb":24576,"availableMemoryMb":24576,"supportedModels":["default"],"maxConcurrentTasks":2})
        assert reg["status"] == "ONLINE"
        print("[OK] RegisterWorkerV3")

        hb = await rpc("HeartbeatV3", {"workerId":worker})
        assert hb["status"] == "ONLINE"
        print("[OK] HeartbeatV3")

        scheduled = await rpc("ScheduleComputeV3", {"taskType":"inference","requiredCapability":"compute","payload":{"smoke":True,"scheduler":"v3"},"idempotencyKey":worker,"maxAttempts":2})
        assert scheduled["assignedWorkerId"] == worker
        print("[OK] ScheduleComputeV3", scheduled["taskId"])

        claimed = await rpc("ClaimTaskV3", {"taskId":scheduled["taskId"],"workerId":worker})
        assert claimed["status"] == "RUNNING"
        print("[OK] ClaimTaskV3")

        completed = await rpc("CompleteTaskV3", {"taskId":scheduled["taskId"],"workerId":worker,"result":{"smoke":"passed"}})
        assert completed["status"] == "COMPLETED"
        assert completed["result"]["smoke"] == "passed"
        print("[OK] CompleteTaskV3")

        task = await rpc("GetTask", {"taskId":scheduled["taskId"]})
        assert task["status"] == "COMPLETED"
        print("[OK] GetTask result persistence")

        metrics = await rpc("GetSchedulerMetrics", {})
        assert metrics["scheduler"] == "V3"
        print("[OK] Scheduler metrics")

        await rpc("WorkerOffline", {"workerId":worker})
        print("[OK] WorkerOffline")

    print("[OK] PUBLIC SCHEDULER V3 FULL LIFECYCLE PASSED")


if __name__ == "__main__":
    asyncio.run(main())
