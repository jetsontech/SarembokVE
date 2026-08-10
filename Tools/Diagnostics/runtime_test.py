"""
Sarembok VE Runtime Integration Test
Sends Emotion and Speak commands via WebSocket and prints responses.
"""
import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:9000"

async def test():
    print("[TEST] Connecting to WebSocket server...")
    ws = await websockets.connect(WS_URL)
    print("[TEST] Connected.")

    # --- Emotion command ---
    emotion_cmd = json.dumps({
        "command": "Emotion",
        "target": "avatar",
        "payload": {"state": "Happy"}
    })
    print(f"[TEST] Sending Emotion command: {emotion_cmd}")
    await ws.send(emotion_cmd)
    resp = await asyncio.wait_for(ws.recv(), timeout=10)
    print(f"[TEST] EMOTION RESPONSE: {resp}")

    await asyncio.sleep(2)

    # --- Speak command ---
    speak_cmd = json.dumps({
        "command": "Speak",
        "target": "avatar",
        "payload": {
            "text": "Sarembok runtime test successful.",
            "emotion": "Happy"
        }
    })
    print(f"[TEST] Sending Speak command: {speak_cmd}")
    await ws.send(speak_cmd)
    resp = await asyncio.wait_for(ws.recv(), timeout=10)
    print(f"[TEST] SPEAK RESPONSE: {resp}")

    await ws.close()
    print("[TEST] Done. All commands sent and acknowledged.")

if __name__ == "__main__":
    asyncio.run(test())
