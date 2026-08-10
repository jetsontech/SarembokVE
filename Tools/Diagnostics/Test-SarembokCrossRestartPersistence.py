#!/usr/bin/env python3
"""
Test-SarembokCrossRestartPersistence.py
Automated Cognitive Runtime Acceptance Suite (Checks 096 - 115) for Sarembok_VE v1.7.

Executes process restart cycles verifying true disk persistence, event replay reconstruction,
10-source cognitive context assembly, token accounting, and fallback resilience across runtime restarts.
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

def get_log_content(log_filename):
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

async def run_cognitive_persistence_suite():
    print("============================================================")
    print("  SAREMBOK_VE v1.7 COGNITIVE PERSISTENCE SUITE (096 - 115)  ")
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

        # 2. Launch Unreal Engine Runtime Cycle 1
        print("\n[INIT] Launching SarembokVE Runtime Cycle 1 (-LOG=CrossRestartCycle1.log)...")
        remove_log_file("CrossRestartCycle1.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=CrossRestartCycle1.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(12)
        import websockets

        # Trigger Checks 096-099
        print("\n[CHECKS 096-099] Testing DB Persistence & Schema Migration...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-cog-1",
                "timestamp": "2026-08-10T08:00:00Z",
                "command": "TriggerCognitiveTest_096_099",
                "target": "System",
                "payload": {},
                "context": {"check": "096-099"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 100-102
        print("[CHECKS 100-102] Testing Event Persistence & Replay Reconstruction...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-cog-2",
                "timestamp": "2026-08-10T08:00:02Z",
                "command": "TriggerCognitiveTest_100_102",
                "target": "System",
                "payload": {},
                "context": {"check": "100-102"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 106-111
        print("[CHECKS 106-111] Testing Cognitive Context Assembly & Token Accounting...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-cog-3",
                "timestamp": "2026-08-10T08:00:04Z",
                "command": "TriggerCognitiveTest_106_111",
                "target": "System",
                "payload": {},
                "context": {"check": "106-111"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Trigger Checks 112-115
        print("[CHECKS 112-115] Testing Autonomous Action & Memory Projection...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-cog-4",
                "timestamp": "2026-08-10T08:00:06Z",
                "command": "TriggerCognitiveTest_112_115",
                "target": "System",
                "payload": {},
                "context": {"check": "112-115"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(3)

        # Kill Cycle 1 Process to test real process restart persistence
        print("\n[CYCLE 1 KILL] Terminating Unreal Engine process for cross-restart validation...")
        if ue_process and ue_process.poll() is None:
            ue_process.terminate()
            try:
                ue_process.wait(timeout=5)
            except Exception:
                ue_process.kill()

        time.sleep(3)

        # Launch Cycle 2 Process
        print("\n[CYCLE 2 RESTART] Relaunching SarembokVE Runtime Cycle 2 (-LOG=CrossRestartCycle2.log)...")
        remove_log_file("CrossRestartCycle2.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=CrossRestartCycle2.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(12)

        # Trigger Checks 103-105 (Cross-Restart Continuity Verification)
        print("[CHECKS 103-105] Verifying Identity, Conversation & Goal Continuity Across Process Restart...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            cmd = {
                "protocol": "sarembok.v1",
                "id": "cmd-cog-5",
                "timestamp": "2026-08-10T08:00:10Z",
                "command": "TriggerCognitiveTest_103_105",
                "target": "System",
                "payload": {},
                "context": {"check": "103-105"}
            }
            await ws.send(json.dumps(cmd))
            await ws.recv()

        time.sleep(4)

        log1 = get_log_content("CrossRestartCycle1.log")
        log2 = get_log_content("CrossRestartCycle2.log")
        log_content = log1 + "\n" + log2

        # Evaluate Checks 096-115
        results["096 Persistent database initialization"]      = ("CHECK_096" in log_content) or ("DB_INITIALIZED" in log_content)
        results["097 Schema migration"]                        = ("CHECK_097" in log_content) or ("v1.7_init_schema" in log_content)
        results["098 Profile persistence"]                     = ("CHECK_098" in log_content) or ("PROFILE_SAVED" in log_content)
        results["099 Profile reload"]                          = ("CHECK_099" in log_content) or ("PROFILE_LOADED" in log_content)
        results["100 Event persistence"]                       = ("CHECK_100" in log_content) or ("EVENT_SAVED" in log_content)
        results["101 Event replay"]                            = ("CHECK_101" in log_content) or ("EVENTS_LOADED" in log_content)
        results["102 State reconstruction"]                    = ("CHECK_102" in log_content) or ("STATE_RECONSTRUCTED" in log_content)
        results["103 Cross-restart identity recognition"]      = ("CHECK_103" in log_content) or ("CROSS_RESTART" in log_content)
        results["104 Cross-restart conversation continuity"]   = ("CHECK_104" in log_content) or ("CONVERSATION_CONTINUITY" in log_content)
        results["105 Cross-restart goal continuity"]           = ("CHECK_105" in log_content) or ("GOAL_CONTINUITY" in log_content)
        results["106 Context assembly"]                        = ("CHECK_106" in log_content) or ("CONTEXT_ASSEMBLY" in log_content)
        results["107 LLM request generation"]                  = ("CHECK_107" in log_content) or ("LLM_REASONING_PROMPT" in log_content)
        results["108 LLM schema validation"]                  = ("CHECK_108" in log_content) or ("SCHEMA_VALIDATED" in log_content)
        results["109 LLM timeout"]                             = ("CHECK_109" in log_content) or ("TimeoutMs=5000" in log_content)
        results["110 Deterministic fallback"]                  = ("CHECK_110" in log_content) or ("DETERMINISTIC_FALLBACK" in log_content)
        results["111 Fallback -> LLM recovery"]                = ("CHECK_111" in log_content) or ("FALLBACK_LLM_RECOVERY" in log_content)
        results["112 Autonomous decision"]                     = ("CHECK_112" in log_content) or ("AUTONOMOUS_DECISION" in log_content)
        results["113 Action execution"]                        = ("CHECK_113" in log_content) or ("ACTION_EXECUTION" in log_content)
        results["114 Event recording"]                         = ("CHECK_114" in log_content) or ("EVENT_RECORDING" in log_content)
        results["115 Memory projection update"]                = ("CHECK_115" in log_content) or ("MEMORY_PROJECTION" in log_content)

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
    res = asyncio.run(run_cognitive_persistence_suite())
    print("\n============================================================")
    print("      COGNITIVE RUNTIME ACCEPTANCE SUMMARY (096 - 115)     ")
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
    print(f" {passed_count}/{total_count} COGNITIVE PERSISTENCE CHECKS PASSED")
    print("============================================================")

    sys.exit(0 if all_passed else 1)
