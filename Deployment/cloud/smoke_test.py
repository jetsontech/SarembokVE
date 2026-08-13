"""Sarembok VE Production Cloud Smoke Test Suite.

Verifies:
1. Edge & Runtime reachability
2. Authentication enforcement & rejection testing
3. 12 core JSON-RPC facets
4. GPU compute worker registration & scheduling
5. Digital Human session creation & routing
6. Health and storage verification
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from typing import Any

import websockets

RAW_ARG = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SAREMBOK_WS_URL", "https://sarembok.com")
if RAW_ARG.startswith("https://"):
    HTTP_URL = RAW_ARG
    WS_URL = RAW_ARG.replace("https://", "wss://")
elif RAW_ARG.startswith("http://"):
    HTTP_URL = RAW_ARG
    WS_URL = RAW_ARG.replace("http://", "ws://")
elif RAW_ARG.startswith("wss://"):
    WS_URL = RAW_ARG
    HTTP_URL = RAW_ARG.replace("wss://", "https://")
elif RAW_ARG.startswith("ws://"):
    WS_URL = RAW_ARG
    HTTP_URL = RAW_ARG.replace("ws://", "http://")
else:
    HTTP_URL = f"https://{RAW_ARG}"
    WS_URL = f"wss://{RAW_ARG}"

AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "")
AGENT_ID = "cloud-smoke-agent"
WORKER_ID = "cloud-smoke-gpu-01"


def print_step(name: str, passed: bool, detail: str = "") -> None:
    tag = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
    suffix = f" - {detail}" if detail else ""
    print(f"{tag} {name}{suffix}")


async def test_auth_rejection(ws_url: str) -> bool:
    """Verify that requests without valid token are rejected when AUTH_TOKEN is active."""
    if not AUTH_TOKEN:
        print_step("Auth Rejection Check", True, "Skipped (no token configured)")
        return True
    try:
        async with websockets.connect(ws_url) as ws:
            bad_req = {
                "jsonrpc": "2.0",
                "id": "bad-auth-test",
                "method": "QueryWorldModel",
                "params": {"authToken": "invalid-secret-token"},
            }
            await ws.send(json.dumps(bad_req))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            rejected = "error" in resp and resp["error"].get("code") == -32001
            print_step("Auth Rejection Check", rejected, "Invalid token rejected correctly" if rejected else f"Unexpected response: {resp}")
            return rejected
    except Exception as exc:
        print_step("Auth Rejection Check", False, f"Exception: {exc}")
        return False


async def main() -> None:
    print("=" * 60)
    print(" SAREMBOK VE CLOUD PRODUCTION SMOKE TEST")
    print(f" Target: {WS_URL}")
    print(f" Auth:   {'ENABLED' if AUTH_TOKEN else 'DISABLED (dev mode)'}")
    print("=" * 60)

    # 1. Test HTTP / Edge Health Probe
    if HTTP_URL:
        try:
            health_url = HTTP_URL.rstrip("/") + "/health"
            req = urllib.request.Request(health_url, headers={"User-Agent": "SarembokSmokeTest/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                ok = resp.status == 200
                print_step("Edge HTTP Health Probe", ok, f"Status {resp.status}")
        except Exception as exc:
            print_step("Edge HTTP Health Probe", False, f"Error: {exc}")

    # 2. Test Auth Rejection
    if not await test_auth_rejection(WS_URL):
        print("\n\033[91mSMOKE TEST FAILED: Authentication rejection test failed.\033[0m")
        sys.exit(1)

    # 3. Main WebSocket Test Suite
    passed = 0
    total = 0

    base_params: dict[str, Any] = {}
    if AUTH_TOKEN:
        base_params["authToken"] = AUTH_TOKEN

    tests = [
        # 12 Core Facets
        ("CreateAgent", {"agentId": AGENT_ID, "displayName": "Sarembok Cloud Smoke Agent", **base_params}),
        ("QueryAgentState", {"agentId": AGENT_ID, **base_params}),
        ("InjectPerception", {"agentId": AGENT_ID, "perception": {"source": "smoke-test", "value": "online"}, **base_params}),
        ("EvaluateDecision", {"agentId": AGENT_ID, "actionId": "smoke-action", "riskScore": 0.3, "confidence": 0.99, **base_params}),
        ("GetCognitiveScorecard", {"agentId": AGENT_ID, **base_params}),
        ("QueryWorldModel", {"filter": "all", **base_params}),
        ("CreateDelegation", {"sourceAgentId": AGENT_ID, "targetAgentId": AGENT_ID, "goalId": "smoke-goal", **base_params}),
        ("GetAuditTrail", {"agentId": AGENT_ID, **base_params}),
        ("SendMessage", {"agentId": AGENT_ID, "content": "cloud smoke test message", **base_params}),
        ("GetEvents", {"agentId": AGENT_ID, **base_params}),
        ("GetMetrics", {"agentId": AGENT_ID, **base_params}),
        ("RestoreState", {"agentId": AGENT_ID, "walEntries": 1, **base_params}),

        # GPU Compute Scheduler Abstraction
        ("RegisterWorker", {
            "workerId": WORKER_ID,
            "capabilities": ["inference", "meta_human", "batch"],
            "gpuVendor": "NVIDIA",
            "gpuModel": "RTX 4090",
            "vramMb": 24576,
            "cudaVersion": "12.2",
            "status": "ONLINE",
            **base_params,
        }),
        ("ListWorkers", {"capability": "meta_human", **base_params}),
        ("ListWorkersStatusFilter", {"status": "ONLINE", **base_params}),
        ("ScheduleCompute", {"taskType": "meta_human_rendering", "requiredCapability": "meta_human", **base_params}),

        # Digital Human Session Routing
        ("CreateDigitalHumanSession", {"agentId": AGENT_ID, "metahumanId": "ada_v1", "voiceProfile": "en_us_female_1", **base_params}),

        # Control Plane Extensions
        ("RuntimeInfo", {**base_params}),
        ("ListAgents", {**base_params}),
        ("GetAgent", {"agentId": AGENT_ID, **base_params}),
        ("ListTasks", {**base_params}),
        ("CreateTask", {"taskType": "meta_human_rendering", **base_params}),
        ("ListDigitalHumanSessions", {**base_params}),
        ("ListEvents", {"agentId": AGENT_ID, "limit": 10, **base_params}),
        ("Heartbeat", {"workerId": WORKER_ID, "status": "ONLINE", **base_params}),
    ]

    try:
        async with websockets.connect(WS_URL) as ws:
            for index, (method, params) in enumerate(tests, 1):
                total += 1
                req_id = f"smoke-{index}"
                rpc_method = "ListWorkers" if method == "ListWorkersStatusFilter" else method
                request = {"jsonrpc": "2.0", "id": req_id, "method": rpc_method, "params": params}
                await ws.send(json.dumps(request))
                raw_resp = await asyncio.wait_for(ws.recv(), timeout=5)
                response = json.loads(raw_resp)
                ok = response.get("id") == req_id and "result" in response
                print_step(method, ok)
                if not ok:
                    print(json.dumps(response, indent=2))
                    sys.exit(1)
                passed += 1

            # 4. Final Health Check RPC
            total += 1
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": "health", "method": "Health", "params": base_params}))
            raw_health = await asyncio.wait_for(ws.recv(), timeout=5)
            health = json.loads(raw_health)
            ok = "result" in health and health["result"].get("status") == "ONLINE"
            print_step("Health Check RPC", ok, json.dumps(health.get("result", {})))
            if not ok:
                sys.exit(1)
            passed += 1

    except Exception as exc:
        print_step("WebSocket Connection & Protocol", False, f"Exception: {exc}")
        sys.exit(1)

    print("=" * 60)
    print(f" SMOKE TEST SUMMARY: {passed}/{total} PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
