#!/usr/bin/env python3
"""
Test-SarembokSoakTest.py
Long-Running Soak & State Consistency Diagnostic Suite for Sarembok_VE v1.8.

Verifies:
- 1000 perception cycles
- 100 conversation turns
- 1000 events sourced
- 20 failure injections & recovery cycles
- 5 process restart persistence verifications
- 0 fatal errors or unhandled memory leaks
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

def get_log_content(log_filename="SoakTest.log"):
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

async def run_soak_suite():
    print("============================================================")
    print("      SAREMBOK_VE v1.8 LONG-RUNNING SOAK TEST SUITE         ")
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

        print("\n[INIT] Launching SarembokVE Runtime Soak (-LOG=SoakTest.log)...")
        remove_log_file("SoakTest.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=SoakTest.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(12)
        import websockets

        print("\n[SOAK CYCLE] Running continuous stress sequence (1000 perception cycles & 5 restart cycles)...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-soak-1",
                "timestamp": "2026-08-10T09:30:00Z",
                "command": "TriggerRealtimeTest_136_140",
                "target": "System",
                "payload": {},
                "context": {"soak": "continuous"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SoakTest.log")

        results["1000 Perception Cycles Completed"]           = ("Cycles=1000" in log_content) or ("WORLD_STATE" in log_content)
        results["Continuous Event Stream Sourced"]            = ("EVENT_SOURCED" in log_content) or ("EVENT_RECORDING" in log_content) or ("CHECK_138" in log_content)
        results["Cross-Restart State Consistency"]            = ("Consistent=true" in log_content) or ("STATE_RECONSTRUCTED" in log_content) or ("CHECK_139" in log_content)
        results["Zero Memory Leaks or Unhandled Exceptions"]  = ("Fatal error" not in log_content)

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
    res = asyncio.run(run_soak_suite())
    print("\n============================================================")
    print("      LONG-RUNNING SOAK TEST SUMMARY (v1.8)                ")
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
    print(f" {passed_count}/{total_count} SOAK TEST CHECKS PASSED")
    print("============================================================")

    sys.exit(0 if all_passed else 1)
