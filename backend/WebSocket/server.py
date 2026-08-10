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

            # If no other client is currently connected, queue the command message for when Unreal Engine connects
            other_clients = [c for c in CONNECTED_CLIENTS if c != websocket]
            if not other_clients:
                try:
                    data = json.loads(message)
                    if "command" in data:
                        EARLY_QUEUED_MESSAGES.append(message)
                        print(f"[SAREMBOK SERVER] Pre-world command queued on server: {data.get('command')}")
                except Exception:
                    pass
            else:
                # Forward / broadcast command to all other connected clients
                clients_to_remove = set()
                for client in other_clients:
                    try:
                        await client.send(message)
                        print("[SAREMBOK SERVER] Forwarded command to connected client.")
                    except websockets.exceptions.ConnectionClosed:
                        clients_to_remove.add(client)
                CONNECTED_CLIENTS.difference_update(clients_to_remove)

            # Send acknowledgment back to sender
            try:
                data = json.loads(message)
                cmd = data.get("command", "")
                response = {
                    "type": "ai_response",
                    "text": "Sarembok Runtime Online",
                    "command": cmd,
                    "state": "active"
                }
            except Exception:
                response = {
                    "type": "ai_response",
                    "text": "Sarembok Runtime Online",
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
