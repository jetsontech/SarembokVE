#!/usr/bin/env python3
"""
Test-SarembokSessionScenarios.py
Automated Multi-Session Acceptance Suite for Sarembok_VE v1.6 Persistent Social Intelligence.

Executes 5 sequential session continuity scenarios verifying individual-aware digital human autonomy:
- Session 1: First Contact (Unknown User Entry, Profile Creation, Fact Storage)
- Session 2: Return Visit (Recognized User, Social Memory Recall, Personalized Greeting)
- Session 3: Fact Contradiction & Reconciliation (Conflict Detection, Fact Update)
- Session 4: Long-Term Goal Persistence Across Boundaries
- Session 5: Resilience & Safety Fallback Continuity
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

def get_log_content(log_filename="SessionTest.log"):
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

async def run_session_suite():
    print("============================================================")
    print("      SAREMBOK_VE v1.6 MULTI-SESSION TEST SUITE             ")
    print("============================================================")

    results = {}
    server_process = None
    ue_process = None

    try:
        # 1. Start Python Backend
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

        # 2. Launch Unreal Engine Runtime
        print("\n[INIT] Launching SarembokVE Runtime (-LOG=SessionTest.log)...")
        remove_log_file("SessionTest.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=SessionTest.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(12)

        import websockets

        # ----------------------------------------------------
        # SESSION 1: First Contact (Unknown User Entry & Profile Creation)
        # ----------------------------------------------------
        print("\n[SESSION 1] Testing First Contact, Identity Profile Creation & Fact Ingestion...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-sess-1",
                "timestamp": "2026-08-10T07:00:00Z",
                "command": "TriggerSession1_FirstContact",
                "target": "System",
                "payload": {},
                "context": {"session": "1"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SessionTest.log")

        s1_profile = ("PROFILE_CREATED" in log_content) or ("user-0007" in log_content)
        s1_fact    = ("favorite_workstation" in log_content) or ("NVIDIA" in log_content)
        s1_evt     = ("EVENT_SOURCED" in log_content) or ("FIRST_CONTACT" in log_content)

        results["Session 1: Profile Created (First Contact)"] = s1_profile
        results["Session 1: Initial Fact Ingested"] = s1_fact
        results["Session 1: Sourced Event Emitted"] = s1_evt

        # ----------------------------------------------------
        # SESSION 2: Return Visit (Recognized User & Social Memory Recall)
        # ----------------------------------------------------
        print("\n[SESSION 2] Testing Return Visit, Identity Recognition & Memory Recall...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-sess-2",
                "timestamp": "2026-08-10T07:00:02Z",
                "command": "TriggerSession2_ReturnVisit",
                "target": "System",
                "payload": {},
                "context": {"session": "2"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SessionTest.log")

        s2_recog   = ("RECOGNIZED" in log_content) or ("Interactions=2" in log_content)
        s2_reconn  = ("reconnect.recognized_user" in log_content) or ("Good to see you again Alex" in log_content)

        results["Session 2: Identity Recognized (Return Visit)"] = s2_recog
        results["Session 2: Personalized Reconnect Goal Pushed"] = s2_reconn

        # ----------------------------------------------------
        # SESSION 3: Fact Contradiction & Reconciliation
        # ----------------------------------------------------
        print("\n[SESSION 3] Testing Fact Contradiction & Reconciliation...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-sess-3",
                "timestamp": "2026-08-10T07:00:04Z",
                "command": "TriggerSession3_Contradiction",
                "target": "System",
                "payload": {},
                "context": {"session": "3"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SessionTest.log")

        s3_conflict = ("CONTRADICTION_DETECTED" in log_content) or ("FACT_CONTRADICTION" in log_content)
        s3_update   = ("Mac Studio" in log_content) or ("reconcile.fact" in log_content)

        results["Session 3: Fact Contradiction Detected"] = s3_conflict
        results["Session 3: Social Memory Fact Updated"] = s3_update

        # ----------------------------------------------------
        # SESSION 4: Long-Term Goal Persistence Across Boundaries
        # ----------------------------------------------------
        print("\n[SESSION 4] Testing Long-Term Goal Persistence Across Session Boundary...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-sess-4",
                "timestamp": "2026-08-10T07:00:06Z",
                "command": "TriggerSession4_LongTermGoal",
                "target": "System",
                "payload": {},
                "context": {"session": "4"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SessionTest.log")

        s4_goal = ("deploy.ai.cluster" in log_content) or ("LONG_TERM_GOAL" in log_content)

        results["Session 4: Long-Term Goal Persisted & Recalled"] = s4_goal

        # ----------------------------------------------------
        # SESSION 5: Resilience & Safety Fallback Continuity
        # ----------------------------------------------------
        print("\n[SESSION 5] Testing Resilience & Fallback Safety Continuity...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-sess-5",
                "timestamp": "2026-08-10T07:00:08Z",
                "command": "TriggerSession5_ResilienceFallback",
                "target": "System",
                "payload": {},
                "context": {"session": "5"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(5)
        log_content = get_log_content("SessionTest.log")

        s5_resil = ("resilience.test" in log_content) or ("RESILIENCE_FALLBACK" in log_content)

        results["Session 5: Resilience & Fallback Continuity"] = s5_resil

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
    res = asyncio.run(run_session_suite())
    print("\n============================================================")
    print("      MULTI-SESSION ACCEPTANCE SUMMARY (v1.6)              ")
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
        print(f"  {k:<50}: {status}")

    print("\n============================================================")
    print(f" {passed_count}/{total_count} MULTI-SESSION TESTS PASSED")
    print("============================================================")

    sys.exit(0 if all_passed else 1)
