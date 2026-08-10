"""Local cloud-runtime smoke test for the 12 public RPC facets."""

import asyncio
import json
import sys

import websockets

WS_URL = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:9000"
AGENT = "cloud-smoke-agent"


async def main() -> None:
    async with websockets.connect(WS_URL) as ws:
        tests = [
            ("CreateAgent", {"agentId": AGENT, "displayName": "Sarembok Cloud Smoke"}),
            ("QueryAgentState", {"agentId": AGENT}),
            ("InjectPerception", {"agentId": AGENT, "perception": {"source": "smoke-test", "value": "online"}}),
            ("EvaluateDecision", {"agentId": AGENT, "actionId": "smoke-action", "riskScore": 0.3, "confidence": 0.99}),
            ("GetCognitiveScorecard", {"agentId": AGENT}),
            ("QueryWorldModel", {"filter": "all"}),
            ("CreateDelegation", {"sourceAgentId": AGENT, "targetAgentId": AGENT, "goalId": "smoke-goal"}),
            ("GetAuditTrail", {"agentId": AGENT}),
            ("SendMessage", {"agentId": AGENT, "content": "cloud smoke test"}),
            ("GetEvents", {"agentId": AGENT}),
            ("GetMetrics", {"agentId": AGENT}),
            ("RestoreState", {"agentId": AGENT, "walEntries": 1}),
        ]

        passed = 0
        for index, (method, params) in enumerate(tests, 1):
            request = {"jsonrpc": "2.0", "id": f"smoke-{index}", "method": method, "params": params}
            await ws.send(json.dumps(request))
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            ok = response.get("id") == request["id"] and "result" in response
            print(f"[{'PASS' if ok else 'FAIL'}] {method}")
            if not ok:
                print(json.dumps(response, indent=2))
                raise SystemExit(1)
            passed += 1

        await ws.send(json.dumps({"jsonrpc": "2.0", "id": "health", "method": "Health", "params": {}}))
        health = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print(f"[{'PASS' if 'result' in health else 'FAIL'}] Health")
        print(f"\nCLOUD SMOKE TEST: {passed}/12 FACETS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
