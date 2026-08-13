import asyncio
import json
import os
import ssl
import sys
import websockets

URI = "wss://sarembok.com/"
TOKEN = os.environ.get("SAREMBOK_AUTH_TOKEN")

if not TOKEN:
    print("FAIL: SAREMBOK_AUTH_TOKEN is not set")
    sys.exit(1)


async def rpc(ws, request_id, method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }

    payload["params"]["authToken"] = TOKEN

    await ws.send(json.dumps(payload))

    raw = await asyncio.wait_for(ws.recv(), timeout=15)
    response = json.loads(raw)

    print()
    print(f"--- {method} ---")
    print(json.dumps(response, indent=2))

    if "error" in response:
        print(f"FAIL: {method}")
        return response, False

    print(f"PASS: {method}")
    return response, True


async def main():

    print("=" * 70)
    print(" SAREMBOK V3 — AUTHENTICATED PUBLIC RPC CONTRACT TEST")
    print("=" * 70)
    print()
    print(f"Endpoint: {URI}")

    ssl_context = ssl.create_default_context()

    async with websockets.connect(
        URI,
        ssl=ssl_context,
        open_timeout=10,
        close_timeout=5,
        ping_interval=20,
        ping_timeout=10,
    ) as ws:

        print()
        print("PASS: TLS established")
        print("PASS: WebSocket established")
        print("PASS: Public WSS reachable")

        results = []

        # ------------------------------------------------------------
        # Core runtime
        # ------------------------------------------------------------

        response, ok = await rpc(ws, 1, "Health")
        results.append(("Health", ok))

        health = response.get("result", {}) if ok else {}

        if ok:
            if health.get("status") == "ONLINE":
                print("PASS: Runtime status ONLINE")
            else:
                print("FAIL: Runtime status is not ONLINE")
                results.append(("Runtime ONLINE", False))

            if health.get("authConfigured") is True:
                print("PASS: Authentication configured")
            else:
                print("FAIL: Authentication configuration missing")
                results.append(("Authentication configured", False))

        # ------------------------------------------------------------
        # Worker registry
        # ------------------------------------------------------------

        response, ok = await rpc(ws, 2, "ListWorkers")
        results.append(("ListWorkers", ok))

        # ------------------------------------------------------------
        # Agent lifecycle
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            3,
            "CreateAgent",
            {
                "agentId": "v3-production-smoke-agent",
                "name": "V3 Production Smoke Agent",
            },
        )
        results.append(("CreateAgent", ok))

        # ------------------------------------------------------------
        # Agent state
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            4,
            "QueryAgentState",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("QueryAgentState", ok))

        # ------------------------------------------------------------
        # World model
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            5,
            "QueryWorldModel",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("QueryWorldModel", ok))

        # ------------------------------------------------------------
        # Cognitive scorecard
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            6,
            "GetCognitiveScorecard",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("GetCognitiveScorecard", ok))

        # ------------------------------------------------------------
        # Events
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            7,
            "GetEvents",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("GetEvents", ok))

        # ------------------------------------------------------------
        # Metrics
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            8,
            "GetMetrics",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("GetMetrics", ok))

        # ------------------------------------------------------------
        # Digital Human
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            9,
            "CreateDigitalHumanSession",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("CreateDigitalHumanSession", ok))

        session_id = None

        if ok:
            session_id = (
                response
                .get("result", {})
                .get("sessionId")
            )

        if session_id:
            response, ok = await rpc(
                ws,
                10,
                "GetDigitalHumanSession",
                {
                    "sessionId": session_id,
                },
            )
            results.append(("GetDigitalHumanSession", ok))

        # ------------------------------------------------------------
        # Scheduler V3
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            11,
            "ScheduleCompute",
            {
                "agentId": "v3-production-smoke-agent",
                "taskType": "smoke_test",
                "payload": {
                    "source": "authenticated_v3_smoke",
                    "purpose": "production_contract_validation",
                },
            },
        )
        results.append(("ScheduleCompute", ok))

        # ------------------------------------------------------------
        # Audit trail
        # ------------------------------------------------------------

        response, ok = await rpc(
            ws,
            12,
            "GetAuditTrail",
            {
                "agentId": "v3-production-smoke-agent",
            },
        )
        results.append(("GetAuditTrail", ok))

        # ------------------------------------------------------------
        # Final report
        # ------------------------------------------------------------

        print()
        print("=" * 70)
        print(" SAREMBOK V3 — TEST SUMMARY")
        print("=" * 70)

        passed = 0
        failed = 0

        for name, ok in results:
            status = "PASS" if ok else "FAIL"

            if ok:
                passed += 1
            else:
                failed += 1

            print(f"{status:<6} {name}")

        print()
        print(f"PASSED: {passed}")
        print(f"FAILED: {failed}")
        print()

        if failed:
            print("=" * 70)
            print(" SAREMBOK V3 — RPC CONTRACT TEST: FAILED")
            print("=" * 70)
            sys.exit(1)

        print("=" * 70)
        print(" SAREMBOK V3 — RPC CONTRACT TEST: PASS")
        print("=" * 70)


asyncio.run(main())
