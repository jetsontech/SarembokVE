import asyncio
import json
import websockets

CONNECTED_CLIENTS = set()
EARLY_QUEUED_MESSAGES = []

def handle_rpc_method(method, params, req_id):
    if method == "CreateAgent":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"agentId": params.get("agentId"), "status": "created"}}
    elif method == "QueryAgentState":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"agentId": params.get("agentId"), "cognitiveReliability": 0.945, "status": "IDLE"}}
    elif method == "InjectPerception":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"agentId": params.get("agentId"), "perceptionInjected": True}}
    elif method == "EvaluateDecision":
        risk = params.get("riskScore", 0.1)
        res = "ALLOW" if risk <= 0.65 else ("CONFIRM_REQUIRED" if risk <= 0.90 else "DENY")
        return {"id": req_id, "jsonrpc": "2.0", "result": {"governanceResult": res, "auditToken": f"gov-{req_id}"}}
    elif method == "GetCognitiveScorecard":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"agentId": params.get("agentId"), "overallReliability": 0.945}}
    elif method == "QueryWorldModel":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"filter": params.get("filter"), "entitiesCount": 3}}
    elif method == "CreateDelegation":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"delegationId": "del-sdk-001", "status": "created"}}
    elif method == "GetAuditTrail":
        return {"id": req_id, "jsonrpc": "2.0", "result": {"agentId": params.get("agentId"), "integrity": True}}
    elif method == "SendMessage":
        return {"id": req_id, "jsonrpc": "2.0", "result": {
            "agentId": params.get("agentId"),
            "messageId": f"msg-{req_id}",
            "delivered": True
        }}
    elif method == "GetEvents":
        return {"id": req_id, "jsonrpc": "2.0", "result": {
            "agentId": params.get("agentId"),
            "events": [
                {"type": "PERCEPTION", "timestamp": "2026-08-10T19:00:00Z", "traceId": "tr-001"},
                {"type": "DECISION", "timestamp": "2026-08-10T19:00:01Z", "traceId": "tr-002"},
                {"type": "ACTION", "timestamp": "2026-08-10T19:00:02Z", "traceId": "tr-003"}
            ],
            "count": 3
        }}
    elif method == "GetMetrics":
        return {"id": req_id, "jsonrpc": "2.0", "result": {
            "agentId": params.get("agentId"),
            "metrics": {
                "perception": 0.96,
                "memory": 0.91,
                "reasoning": 0.94,
                "policy": 0.99,
                "overall": 0.945
            },
            "uptimeSeconds": 3600
        }}
    elif method == "RestoreState":
        return {"id": req_id, "jsonrpc": "2.0", "result": {
            "agentId": params.get("agentId"),
            "restored": True,
            "walEntriesReplayed": params.get("walEntries", 0),
            "stateConsistent": True
        }}
    else:
        return {"id": req_id, "jsonrpc": "2.0", "result": {"method": method, "status": "ok"}}

async def client_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[SAREMBOK SERVER] Client Connected. Total connected clients: {len(CONNECTED_CLIENTS)}")

    if EARLY_QUEUED_MESSAGES:
        print(f"[SAREMBOK SERVER] Flushing {len(EARLY_QUEUED_MESSAGES)} pre-world queued messages to client...")
        for queued_msg in EARLY_QUEUED_MESSAGES:
            try:
                await websocket.send(queued_msg)
                print(f"[SAREMBOK SERVER] Sent queued pre-world message: {queued_msg}")
            except Exception as e:
                print(f"[SAREMBOK SERVER] Failed to flush queued message: {e}")
        EARLY_QUEUED_MESSAGES.clear()

    try:
        async for message in websocket:
            print(f"[SAREMBOK SERVER] Received message: {message}")

            try:
                data = json.loads(message)
            except Exception:
                error_response = {
                    "protocol": "sarembok.v1",
                    "id": "cmd-error",
                    "type": "error",
                    "error": {
                        "code": "INVALID_JSON",
                        "message": "Malformed JSON payload received"
                    }
                }
                await websocket.send(json.dumps(error_response))
                continue

            method = data.get("method")
            if method:
                req_id = data.get("id", "rpc-001")
                params = data.get("params", {})
                rpc_resp = handle_rpc_method(method, params, req_id)
                await websocket.send(json.dumps(rpc_resp))
                continue

            cmd_name = data.get("command", "")
            cmd_id = data.get("id", "cmd-legacy")
            protocol = data.get("protocol", "legacy.v0")

            other_clients = [c for c in CONNECTED_CLIENTS if c != websocket]
            if not other_clients:
                if cmd_name:
                    EARLY_QUEUED_MESSAGES.append(message)
                    print(f"[SAREMBOK SERVER] Pre-world command queued on server: {cmd_name}")
            else:
                clients_to_remove = set()
                for client in other_clients:
                    try:
                        await client.send(message)
                        print("[SAREMBOK SERVER] Forwarded command to connected client.")
                    except websockets.exceptions.ConnectionClosed:
                        clients_to_remove.add(client)
                CONNECTED_CLIENTS.difference_update(clients_to_remove)

            response = {
                "protocol": protocol,
                "id": cmd_id,
                "type": "ai_response",
                "text": "Sarembok Runtime Online",
                "command": cmd_name,
                "state": "active"
            }
            await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed:
        print("[SAREMBOK SERVER] Client Disconnected")
    finally:
        CONNECTED_CLIENTS.discard(websocket)

async def main():
    print("")
    print("==============================")
    print(" Sarembok WebSocket Runtime")
    print(" Port: 9000 (RPC & Telemetry)")
    print("==============================")
    print("")

    async with websockets.serve(client_handler, "0.0.0.0", 9000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
