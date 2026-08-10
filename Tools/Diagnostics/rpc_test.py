"""
Sarembok VE JSON-RPC SDK Integration Test
Tests all 8 RPC methods through the WebSocket server.
"""
import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:9000"

RPC_TESTS = [
    {"jsonrpc": "2.0", "id": "t1", "method": "CreateAgent", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t2", "method": "QueryAgentState", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t3", "method": "InjectPerception", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t4", "method": "EvaluateDecision", "params": {"riskScore": 0.3}},
    {"jsonrpc": "2.0", "id": "t5", "method": "EvaluateDecision", "params": {"riskScore": 0.8}},
    {"jsonrpc": "2.0", "id": "t6", "method": "GetCognitiveScorecard", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t7", "method": "QueryWorldModel", "params": {"filter": "entities"}},
    {"jsonrpc": "2.0", "id": "t8", "method": "CreateDelegation", "params": {}},
    {"jsonrpc": "2.0", "id": "t9", "method": "GetAuditTrail", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t10", "method": "SendMessage", "params": {"agentId": "test-agent", "content": "Hello agent"}},
    {"jsonrpc": "2.0", "id": "t11", "method": "GetEvents", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t12", "method": "GetMetrics", "params": {"agentId": "test-agent"}},
    {"jsonrpc": "2.0", "id": "t13", "method": "RestoreState", "params": {"agentId": "test-agent", "walEntries": 42}},
]

async def test():
    print("[RPC TEST] Connecting...")
    ws = await websockets.connect(WS_URL)
    passed = 0
    failed = 0

    for rpc in RPC_TESTS:
        await ws.send(json.dumps(rpc))
        resp_raw = await asyncio.wait_for(ws.recv(), timeout=5)
        resp = json.loads(resp_raw)
        ok = resp.get("id") == rpc["id"] and "result" in resp
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {rpc['method']} (id={rpc['id']}): {json.dumps(resp.get('result', resp.get('error')))}")

    await ws.close()
    print(f"\n[RPC TEST] {passed}/{passed+failed} PASSED")

if __name__ == "__main__":
    asyncio.run(test())
