#!/usr/bin/env python3
"""
Test-SarembokRealtimeInteraction.py
Automated Acceptance Suite for Checks 116 to 140 (Sarembok_VE v1.8 Real-Time Cognition).
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time

PROJECT_ROOT = "C:/Sarembok_VE"
UE_EXEC = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
UPROJECT = os.path.join(PROJECT_ROOT, "SarembokVE.uproject")
WS_HOST = "127.0.0.1"
WS_PORT = 9000

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def get_log_content(log_filename="RealtimeTest.log"):
    log_path = os.path.join(PROJECT_ROOT, "Saved", "Logs", log_filename)
    if os.path.exists(log_path):
        try:
            cmd = f'powershell -Command "Get-Content -Path \'{log_path}\' -Raw -ErrorAction SilentlyContinue"'
            res = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")
            return res
        except Exception:
            pass
    return ""

def remove_log_file(log_filename):
    log_path = os.path.join(PROJECT_ROOT, "Saved", "Logs", log_filename)
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception:
            pass

async def run_realtime_suite():
    print("============================================================")
    print("  SAREMBOK_VE v1.8 REAL-TIME COGNITION SUITE (116 - 140)    ")
    print("============================================================")

    results = {}
    server_process = None
    ue_process = None

    try:
        if not is_port_open(WS_HOST, WS_PORT):
            print("[INIT] Launching Python WebSocket Backend on port 9000...")
            server_process = subprocess.Popen(
                [sys.executable, "C:/Sarembok_VE/backend/WebSocket/server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)

        if not is_port_open(WS_HOST, WS_PORT):
            print("[FAIL] WebSocket backend not available.")
            return results

        print("\n[INIT] Launching SarembokVE Runtime (-LOG=RealtimeTest.log)...")
        remove_log_file("RealtimeTest.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=RealtimeTest.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(12)
        import websockets

        # Trigger Checks 116-120
        print("\n[CHECKS 116-120] Testing Real Speech Input Pipeline (STT)...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-rt-1",
                "timestamp": "2026-08-10T09:00:00Z",
                "command": "TriggerRealtimeTest_116_120",
                "target": "System",
                "payload": {},
                "context": {"check": "116-120"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 121-125
        print("[CHECKS 121-125] Testing Action Authorization Policy Gate...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-rt-2",
                "timestamp": "2026-08-10T09:00:02Z",
                "command": "TriggerRealtimeTest_121_125",
                "target": "System",
                "payload": {},
                "context": {"check": "121-125"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 126-130
        print("[CHECKS 126-130] Testing Memory Relevance Retrieval (RAG)...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-rt-3",
                "timestamp": "2026-08-10T09:00:04Z",
                "command": "TriggerRealtimeTest_126_130",
                "target": "System",
                "payload": {},
                "context": {"check": "126-130"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 131-135
        print("[CHECKS 131-135] Testing 13-Stage Autonomous Lifecycle...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-rt-4",
                "timestamp": "2026-08-10T09:00:06Z",
                "command": "TriggerRealtimeTest_131_135",
                "target": "System",
                "payload": {},
                "context": {"check": "131-135"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 136-140
        print("[CHECKS 136-140] Testing Human Interaction Loop & Performance...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-rt-5",
                "timestamp": "2026-08-10T09:00:08Z",
                "command": "TriggerRealtimeTest_136_140",
                "target": "System",
                "payload": {},
                "context": {"check": "136-140"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(4)
        log_content = get_log_content("RealtimeTest.log")

        results["116 Audio stream ingestion"]                  = ("CHECK_116" in log_content) or ("AUDIO_STREAM" in log_content)
        results["117 Speech-to-Text transcription"]            = ("CHECK_117" in log_content) or ("SPEECH_RECOGNIZED" in log_content)
        results["118 STT delegate broadcast"]                  = ("CHECK_118" in log_content)
        results["119 Conversation input boundary"]             = ("CHECK_119" in log_content)
        results["120 User turn processed"]                     = ("CHECK_120" in log_content)
        results["121 Policy gate evaluation"]                  = ("CHECK_121" in log_content) or ("POLICY_EVALUATE" in log_content)
        results["122 Policy deny unsafe action"]               = ("CHECK_122" in log_content)
        results["123 Strict policy enforcement"]               = ("CHECK_123" in log_content)
        results["124 Safety gate interception"]                = ("CHECK_124" in log_content)
        results["125 Authorized action dispatch"]              = ("CHECK_125" in log_content)
        results["126 Relevance score calculation"]             = ("CHECK_126" in log_content) or ("RELEVANCE_RANKED" in log_content)
        results["127 Top-K memory ranking"]                    = ("CHECK_127" in log_content)
        results["128 Context ballooning prevention"]           = ("CHECK_128" in log_content)
        results["129 Retrieval augmented assembly"]            = ("CHECK_129" in log_content)
        results["130 Memory selection efficiency"]             = ("CHECK_130" in log_content)
        results["131 Stage FormGoal"]                          = ("CHECK_131" in log_content)
        results["132 Stage PolicyCheck"]                       = ("CHECK_132" in log_content)
        results["133 Stage Learn"]                             = ("CHECK_133" in log_content)
        results["134 Stage Persist"]                           = ("CHECK_134" in log_content)
        results["135 Full lifecycle transition"]               = ("CHECK_135" in log_content)
        results["136 Human in the loop interaction"]          = ("CHECK_136" in log_content)
        results["137 Real-time STT-TTS latency"]               = ("CHECK_137" in log_content)
        results["138 Continuous perceive loop"]                = ("CHECK_138" in log_content)
        results["139 Soak state consistency"]                  = ("CHECK_139" in log_content)
        results["140 End-to-End real-time cognition"]          = ("CHECK_140" in log_content)

    finally:
        if ue_process and ue_process.poll() is None:
            ue_process.terminate()
            try:
                ue_process.wait(timeout=5)
            except Exception:
                ue_process.kill()
        if server_process and server_process.poll() is None:
            server_process.terminate()

    return results

if __name__ == "__main__":
    res = asyncio.run(run_realtime_suite())
    print("\n============================================================")
    print("      REAL-TIME COGNITION ACCEPTANCE SUMMARY (116 - 140)    ")
    print("============================================================")
    all_passed = True
    passed_count = 0
    total_count = len(res)

    for k, v in res.items():
        status = "PASS" if v else "FAIL"
        if v:
            passed_count += 1
        else:
            all_passed = False
        print(f"  {k:<55}: {status}")

    print("\n============================================================")
    print(f" {passed_count}/{total_count} REAL-TIME CHECKS PASSED")
    print("============================================================")

    sys.exit(0 if all_passed else 1)
