import asyncio
import json
import websockets

CONNECTED_CLIENTS = set()
EARLY_QUEUED_MESSAGES = []

async def client_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[SAREMBOK SERVER] Client Connected. Total connected clients: {len(CONNECTED_CLIENTS)}")

    # If an early queued message exists (sent before Unreal Engine connected), flush it to the newly connected client
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

            cmd_name = data.get("command", "")
            cmd_id = data.get("id", "cmd-legacy")
            protocol = data.get("protocol", "legacy.v0")

            # Forward / broadcast command to all other connected clients (e.g. Unreal Engine)
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

            # Send acknowledgment / response back to sender
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
    print(" Port: 9000")
    print("==============================")
    print("")

    async with websockets.serve(client_handler, "0.0.0.0", 9000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
