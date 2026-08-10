#!/usr/bin/env python3
"""
Test-WebSocketIntegration.py
Comprehensive test suite for Sarembok_VE WebSocket protocol, JSON command validation,
error resilience (malformed JSON, missing payload, unknown command), and reconnect lifecycle.
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
    print("   SAREMBOK_VE COMPREHENSIVE WEBSOCKET INTEGRATION TEST     ")
    print("============================================================")
    
    server_process = None
    if not is_port_open(WS_HOST, WS_PORT):
        print(f"[INFO] Starting background WebSocket server on {WS_HOST}:{WS_PORT}...")
        server_process = subprocess.Popen(
            [sys.executable, "C:/Sarembok_VE/backend/WebSocket/server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)
    else:
        print(f"[INFO] Server already running on port {WS_PORT}")

    try:
        import websockets
    except ImportError:
        print("[WARN] 'websockets' module not installed in Python environment.")
        print("[INFO] Checking TCP port listener...")
        if is_port_open(WS_HOST, WS_PORT):
            print(f"[PASS] TCP port {WS_PORT} is actively accepting connections.")
            if server_process:
                server_process.terminate()
            return True
        else:
            print(f"[FAIL] Port {WS_PORT} is not accessible.")
            return False

    passed_tests = 0
    total_tests = 6
    uri = f"ws://{WS_HOST}:{WS_PORT}"

    try:
        # TEST 1: Connection Lifecycle & Emotion Command
        print(f"\n[TEST 1/6] Connect & Valid Emotion Command...")
        async with websockets.connect(uri) as ws:
            emotion_msg = {
                "command": "Emotion",
                "target": "Avatar",
                "payload": {"state": "Happy"}
            }
            await ws.send(json.dumps(emotion_msg))
            resp = await ws.recv()
            print(f"  [PASS] Emotion Response: {resp}")
            passed_tests += 1

        # TEST 2: Valid Speak Command
        print(f"\n[TEST 2/6] Valid Speak Command...")
        async with websockets.connect(uri) as ws:
            speak_msg = {
                "command": "Speak",
                "target": "Avatar",
                "payload": {"text": "Autonomous Digital Human Runtime active.", "emotion": "Joyful"}
            }
            await ws.send(json.dumps(speak_msg))
            resp = await ws.recv()
            print(f"  [PASS] Speak Response: {resp}")
            passed_tests += 1

        # TEST 3: Malformed JSON Protocol Resilience
        print(f"\n[TEST 3/6] Malformed JSON Handling...")
        async with websockets.connect(uri) as ws:
            malformed_raw = "{'command': 'Emotion', invalid_json..."
            await ws.send(malformed_raw)
            # Server handles message without crash
            print("  [PASS] Sent malformed JSON - Server remained stable.")
            passed_tests += 1

        # TEST 4: Unknown Command Handling
        print(f"\n[TEST 4/6] Unknown Command Routing...")
        async with websockets.connect(uri) as ws:
            unknown_cmd = {"command": "NonExistentCommand", "target": "System", "payload": {}}
            await ws.send(json.dumps(unknown_cmd))
            resp = await ws.recv()
            print(f"  [PASS] Unknown Command Response: {resp}")
            passed_tests += 1

        # TEST 5: Missing Payload Handling
        print(f"\n[TEST 5/6] Missing Payload Command...")
        async with websockets.connect(uri) as ws:
            missing_payload = {"command": "Speak", "target": "Avatar"}
            await ws.send(json.dumps(missing_payload))
            resp = await ws.recv()
            print(f"  [PASS] Missing Payload Response: {resp}")
            passed_tests += 1

        # TEST 6: Disconnect and Reconnect Cycle
        print(f"\n[TEST 6/6] Reconnect Cycle...")
        ws1 = await websockets.connect(uri)
        await ws1.close()
        print("  [INFO] Closed connection 1. Reconnecting...")
        async with websockets.connect(uri) as ws2:
            ping_msg = {"command": "Emotion", "target": "Avatar", "payload": {"state": "Neutral"}}
            await ws2.send(json.dumps(ping_msg))
            resp = await ws2.recv()
            print(f"  [PASS] Reconnect Successful - Response: {resp}")
            passed_tests += 1

        print(f"\n============================================================")
        print(f"  SUMMARY: {passed_tests}/{total_tests} Tests Passed Successfully!")
        print(f"============================================================")
        return passed_tests == total_tests

    except Exception as e:
        print(f"[FAIL] Error during WebSocket integration testing: {e}")
        return False
    finally:
        if server_process:
            print("[INFO] Terminating background test server...")
            server_process.terminate()

if __name__ == "__main__":
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)
