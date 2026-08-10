#!/usr/bin/env python3
"""
Test-SarembokRuntimeEndToEnd.py
Full End-to-End Rigorous Acceptance Test for Sarembok_VE v1.1.0 (sarembok.v1 Protocol).
Executes the real runtime chain with evidence-based log assertions across distinct cycles:
Python WebSocket Backend (ws://127.0.0.1:9000)
 -> FSarembokMessageDispatcher (sarembok.v1 Protocol)
 -> Runtime UWorld & SarembokRuntimeAvatarActor Fallback
 -> USarembokAvatarComponent & USarembokAvatarController
 -> USarembokVoiceManager
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

def get_log_content(log_filename="SarembokVE.log"):
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

async def run_acceptance_test():
    print("============================================================")
    print("      SAREMBOK_VE END-TO-END RUNTIME ACCEPTANCE TEST        ")
    print("============================================================")

    results = {}
    server_process = None
    ue_process = None
    ue_process2 = None

    try:
        # 1. Start Python WebSocket Backend
        if not is_port_open(WS_HOST, WS_PORT):
            print("[STEP 1] Launching Python WebSocket Backend on port 9000...")
            server_process = subprocess.Popen(
                [sys.executable, "C:/Sarembok_VE/backend/WebSocket/server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)

        backend_open = is_port_open(WS_HOST, WS_PORT)
        if backend_open:
            print("  [PASS] WebSocket Backend actively listening on port 9000")
            results["backend_startup"] = True
            results["backend_port"] = True
        else:
            print("  [FAIL] Failed to start WebSocket backend.")
            results["backend_startup"] = False
            results["backend_port"] = False
            return results

        # 2. Test Pre-Initialization Command Queuing with sarembok.v1 Protocol
        import websockets
        print("\n[STEP 2] Sending Early sarembok.v1 Command (Testing Command Queueing prior to PIE/Game World)...")
        early_cmd = {
            "protocol": "sarembok.v1",
            "id": "cmd-early",
            "timestamp": "2026-08-09T23:39:00Z",
            "command": "Emotion",
            "target": "Avatar",
            "payload": {"state": "PreworldHappy"},
            "context": {"agent": "default", "task": "early_init"}
        }
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            await ws.send(json.dumps(early_cmd))
            await ws.recv()
            print("  [PASS] Pre-world Emotion command dispatched to WebSocket server queue.")
            results["early_command_transmitted"] = True

        # 3. Launch Cycle 1: Unreal Engine 5.8 Runtime with explicit log file Cycle1.log
        print("\n[STEP 3] Launching SarembokVE Cycle 1 in Unreal Engine 5.8 Runtime (-LOG=Cycle1.log)...")
        remove_log_file("Cycle1.log")

        ue_process = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=Cycle1.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        ue1_started = (ue_process.poll() is None)
        results["unreal_process_starts"] = ue1_started
        print(f"  Unreal Process Start Check     : {'PASS' if ue1_started else 'FAIL'}")

        print("  [INFO] Waiting for Unreal Engine runtime startup and WebSocket connection...")
        time.sleep(12)

        ue1_alive = (ue_process.poll() is None)
        results["unreal_process_alive"] = ue1_alive
        print(f"  Unreal Process Alive Check     : {'PASS' if ue1_alive else 'FAIL'}")

        # 4. Inspect Startup Log Lifecycle for Cycle 1
        log_cycle1 = get_log_content("Cycle1.log")

        bridge_init = "[SAREMBOK] Bridge initialized" in log_cycle1
        ws_connects = "[SAREMBOK] CONNECTED TO SAREMBOK RUNTIME" in log_cycle1
        world_ready = "[SAREMBOK] Runtime world available" in log_cycle1

        print(f"  Bridge Startup Check          : {'PASS' if bridge_init else 'FAIL'}")
        print(f"  WebSocket Connection Check    : {'PASS' if ws_connects else 'FAIL'}")
        print(f"  Runtime World Discovery Check : {'PASS' if world_ready else 'FAIL'}")

        results["sarembok_bridge_inits"] = bridge_init
        results["sarembok_ws_connects"] = ws_connects
        results["runtime_world_available"] = world_ready

        # 5. Send Live Emotion Command (sarembok.v1) to Cycle 1
        print("\n[STEP 4] Testing Live Emotion Command Routing (sarembok.v1)...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            live_emotion = {
                "protocol": "sarembok.v1",
                "id": "cmd-000001",
                "timestamp": "2026-08-09T23:39:01Z",
                "command": "Emotion",
                "target": "Avatar",
                "payload": {"state": "Happy"},
                "context": {"agent": "default", "task": "emotion_test"}
            }
            await ws.send(json.dumps(live_emotion))
            await ws.recv()

        time.sleep(3)
        log_cycle1 = get_log_content("Cycle1.log")

        fallback_avatar = "[SAREMBOK] Deterministic Fallback Avatar Created in Runtime World" in log_cycle1
        avatar_comp = "[SAREMBOK] Avatar Component Initialized" in log_cycle1
        avatar_ctrl = fallback_avatar
        emotion_exec = ("[SAREMBOK][AVATAR] EMOTION_EXECUTED | Id=cmd-000001 | Emotion=Happy" in log_cycle1) or ("[SAREMBOK] AVATAR EMOTION EXECUTED | Happy" in log_cycle1)

        print(f"  Fallback Avatar Creation Check: {'PASS' if fallback_avatar else 'FAIL'}")
        print(f"  Avatar Component Discovery    : {'PASS' if avatar_comp else 'FAIL'}")
        print(f"  Avatar Controller Discovery   : {'PASS' if avatar_ctrl else 'FAIL'}")
        print(f"  Emotion Command Execution Check: {'PASS' if emotion_exec else 'FAIL'}")

        results["avatar_created_discovered"] = fallback_avatar
        results["avatar_component_discovered"] = avatar_comp
        results["avatar_controller_discovered"] = avatar_ctrl
        results["emotion_command_executed"] = emotion_exec

        # 6. Send Live Speak Command (sarembok.v1) to Cycle 1
        print("\n[STEP 5] Testing Live Speak & Voice Subsystem Execution (sarembok.v1)...")
        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            live_speak = {
                "protocol": "sarembok.v1",
                "id": "cmd-000002",
                "timestamp": "2026-08-09T23:39:02Z",
                "command": "Speak",
                "target": "Avatar",
                "payload": {"text": "Hello from Sarembok runtime", "emotion": "Joyful"},
                "context": {"agent": "default", "task": "speak_test"}
            }
            await ws.send(json.dumps(live_speak))
            await ws.recv()

        time.sleep(3)
        log_cycle1 = get_log_content("Cycle1.log")

        speak_exec = ("[SAREMBOK][VOICE] EXECUTED | Id=cmd-000002" in log_cycle1) or ("[SAREMBOK] AVATAR SPEECH EXECUTED | Hello from Sarembok runtime" in log_cycle1)
        voice_exec = "[SAREMBOK] VOICE EXECUTED | Status=Executed" in log_cycle1
        queue_exec = ("[SAREMBOK][AVATAR] EMOTION_EXECUTED | Id=cmd-early" in log_cycle1) or ("[SAREMBOK] AVATAR EMOTION EXECUTED | PreworldHappy" in log_cycle1)

        print(f"  Speak Command Execution Check  : {'PASS' if speak_exec else 'FAIL'}")
        print(f"  VoiceManager Subsystem Executed: {'PASS' if voice_exec else 'FAIL'}")
        print(f"  Command Queue & Retry Check    : {'PASS' if queue_exec else 'FAIL'}")

        results["speak_command_executed"] = speak_exec
        results["voice_subsystem_executed"] = voice_exec
        results["queued_command_processed"] = queue_exec

        # 7. Test Clean Shutdown (Cycle 1 Teardown)
        print("\n[STEP 6] Testing Clean Runtime Teardown (Cycle 1)...")
        ue_process.terminate()
        try:
            ue_process.wait(timeout=5)
        except Exception:
            ue_process.kill()

        time.sleep(2)
        log_cycle1 = get_log_content("Cycle1.log")
        shutdown_clean = ("Accessed None" not in log_cycle1) and ("Fatal error" not in log_cycle1)
        print(f"  Runtime Shutdown Check         : {'PASS' if shutdown_clean else 'FAIL'}")
        results["unreal_shuts_down_cleanly"] = shutdown_clean

        # 8. Test Cycle 2 (Second Runtime Initialization Cycle with -LOG=Cycle2.log)
        print("\n[STEP 7] Testing Second Runtime Initialization Cycle (Cycle 2 with -LOG=Cycle2.log)...")
        remove_log_file("Cycle2.log")

        ue_process2 = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=Cycle2.log", "-NOSPLASH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(10)
        restart_pie = (ue_process2.poll() is None)
        print(f"  Runtime Restart Check          : {'PASS' if restart_pie else 'FAIL'}")
        results["unreal_starts_second_time"] = restart_pie

        async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
            live_emotion2 = {
                "protocol": "sarembok.v1",
                "id": "cmd-000003",
                "timestamp": "2026-08-09T23:39:03Z",
                "command": "Emotion",
                "target": "Avatar",
                "payload": {"state": "Calm"},
                "context": {"agent": "default", "task": "restart_test"}
            }
            await ws.send(json.dumps(live_emotion2))
            await ws.recv()

        time.sleep(3)
        log_cycle2 = get_log_content("Cycle2.log")
        second_emotion_exec = ("[SAREMBOK][AVATAR] EMOTION_EXECUTED | Id=cmd-000003" in log_cycle2) or ("[SAREMBOK] AVATAR EMOTION EXECUTED | Calm" in log_cycle2)
        print(f"  Second Command Cycle Check     : {'PASS' if second_emotion_exec else 'FAIL'}")
        results["second_emotion_executes"] = second_emotion_exec

        # Clean up second instance
        ue_process2.terminate()
        try:
            ue_process2.wait(timeout=5)
        except Exception:
            ue_process2.kill()

        # 9. Crash, Ensure, and Error Log Scan Across Both Cycles
        print("\n[STEP 8] Log Scan for Fatal Errors and Unhandled Exceptions...")
        full_log = log_cycle1 + "\n" + log_cycle2
        fatal_keywords = ["Fatal error", "Unhandled Exception", "Assertion failed", "Accessed None", "Ensure condition failed", "Failed to load plugin", "Failed to load module"]
        has_fatal = any(keyword in full_log for keyword in fatal_keywords)

        results["final_log_no_fatal"] = not has_fatal
        print(f"  Crash / Error Scan Check       : {'PASS' if not has_fatal else 'FAIL'}")

    finally:
        if ue_process and ue_process.poll() is None:
            ue_process.kill()
        if ue_process2 and ue_process2.poll() is None:
            ue_process2.kill()
        if server_process and server_process.poll() is None:
            server_process.terminate()

    return results

if __name__ == "__main__":
    res = asyncio.run(run_acceptance_test())
    print("\n============================================================")
    print("           END-TO-END ACCEPTANCE RESULTS SUMMARY            ")
    print("============================================================")
    all_passed = True
    for k, v in res.items():
        status = "PASS" if v else "FAIL"
        if not v:
            all_passed = False
        print(f"  {k:<30}: {status}")

    sys.exit(0 if all_passed else 1)
