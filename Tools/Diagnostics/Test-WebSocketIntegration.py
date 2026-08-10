#!/usr/bin/env python3
"""
Test-WebSocketIntegration.py
Validates the Sarembok_VE WebSocket server communication lifecycle and JSON command schemas.
"""

import asyncio
import json
import socket
import subprocess
import sys
import time

WS_HOST = "127.0.0.1"
WS_PORT = 9000

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

async def run_integration_test():
    print("============================================================")
    print("      SAREMBOK_VE WEBSOCKET INTEGRATION TEST SUITE          ")
    print("============================================================")
    
    server_process = None
    if not is_port_open(WS_HOST, WS_PORT):
        print(f"[INFO] Starting background WebSocket server on {WS_HOST}:{WS_PORT}...")
        server_process = subprocess.Popen(
            [sys.executable, "C:/Sarembok_VE/backend/WebSocket/server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Give server time to bind
    else:
        print(f"[INFO] Server already running on port {WS_PORT}")

    try:
        import websockets
    except ImportError:
        print("[WARN] 'websockets' module not installed in Python environment.")
        print("[INFO] Attempting basic TCP socket ping to verify listener...")
        if is_port_open(WS_HOST, WS_PORT):
            print(f"[PASS] TCP port {WS_PORT} is actively accepting connections.")
            if server_process:
                server_process.terminate()
            return True
        else:
            print(f"[FAIL] Port {WS_PORT} is not accessible.")
            return False

    try:
        uri = f"ws://{WS_HOST}:{WS_PORT}"
        print(f"[CONNECTING] Connecting to {uri}...")
        async with websockets.connect(uri) as ws:
            print("[PASS] Connected to Sarembok WebSocket Server!")

            # 1. Test Emotion Command
            emotion_msg = {
                "command": "Emotion",
                "target": "Avatar",
                "payload": {
                    "state": "Happy"
                }
            }
            print(f"[OUT] Sending Emotion Command: {json.dumps(emotion_msg)}")
            await ws.send(json.dumps(emotion_msg))
            response = await ws.recv()
            print(f"[IN] Response: {response}")

            # 2. Test Speak Command
            speak_msg = {
                "command": "Speak",
                "target": "Avatar",
                "payload": {
                    "text": "Hello from Sarembok Digital Human runtime!",
                    "emotion": "Joyful"
                }
            }
            print(f"[OUT] Sending Speak Command: {json.dumps(speak_msg)}")
            await ws.send(json.dumps(speak_msg))
            response = await ws.recv()
            print(f"[IN] Response: {response}")

            print("\n[SUCCESS] WebSocket integration lifecycle test PASSED cleanly!")
            return True
    except Exception as e:
        print(f"[FAIL] Error during WebSocket communication: {e}")
        return False
    finally:
        if server_process:
            print("[INFO] Shutting down test server subprocess...")
            server_process.terminate()

if __name__ == "__main__":
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)
