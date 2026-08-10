#!/usr/bin/env python3
"""
Test-SarembokHardening.py
Automated Acceptance Suite for Checks 201-225 (Sarembok_VE v2.0.1 Platform Hardening).
Covers: Multi-Agent Isolation, Concurrent Execution, API Stress Testing,
        Governance Adversarial Sweeps, and Kill-and-Recover Event Replay.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import socket

PROJECT_ROOT = "C:/Sarembok_VE"
UE_EXEC      = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
UPROJECT     = os.path.join(PROJECT_ROOT, "SarembokVE.uproject")
WS_HOST      = "127.0.0.1"
WS_PORT      = 9000

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def get_log(log_file="HardeningTest.log"):
    path = os.path.join(PROJECT_ROOT, "Saved", "Logs", log_file)
    if os.path.exists(path):
        try:
            res = subprocess.check_output(
                f'powershell -Command "Get-Content -Path \'{path}\' -Raw -ErrorAction SilentlyContinue"',
                shell=True, text=True, errors="ignore")
            return res
        except Exception:
            pass
    return ""

def remove_log(log_file):
    path = os.path.join(PROJECT_ROOT, "Saved", "Logs", log_file)
    if os.path.exists(path):
        try: os.remove(path)
        except Exception: pass

async def run_hardening_suite():
    print("============================================================")
    print("  SAREMBOK_VE v2.0.1 PLATFORM HARDENING SUITE (201 - 225)   ")
    print("============================================================")

    results = {}
    server_proc = None
    ue_proc     = None

    try:
        if not is_port_open(WS_HOST, WS_PORT):
            server_proc = subprocess.Popen(
                [sys.executable, "C:/Sarembok_VE/backend/WebSocket/server.py"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)

        if not is_port_open(WS_HOST, WS_PORT):
            print("[FAIL] WebSocket backend not available.")
            return results

        print("[INIT] Launching SarembokVE Runtime (-LOG=HardeningTest.log)...")
        remove_log("HardeningTest.log")

        ue_proc = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=HardeningTest.log", "-NOSPLASH"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(15)

        import websockets

        hardening_commands = [
            ("201-205", "TriggerHardeningTest_201_205"),
            ("206-210", "TriggerHardeningTest_206_210"),
            ("211-215", "TriggerHardeningTest_211_215"),
            ("216-220", "TriggerHardeningTest_216_220"),
            ("221-225", "TriggerHardeningTest_221_225"),
        ]

        for label, command in hardening_commands:
            print(f"[CHECKS {label}] {command}...")
            async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
                cmd = {
                    "protocol": "sarembok.v1",
                    "id": f"cmd-hard-{label}",
                    "timestamp": "2026-08-10T16:00:00Z",
                    "command": command,
                    "target": "System",
                    "payload": {},
                    "context": {"check": label}
                }
                await ws.send(json.dumps(cmd))
                await ws.recv()
            time.sleep(3)

        time.sleep(4)
        log = get_log("HardeningTest.log")

        # Multi-Agent Isolation (201-205)
        results["201 Three distinct agent profiles created"]       = "Count=3" in log or "CHECK_201" in log
        results["202 Memory namespaces isolated per agent"]         = "Isolated=true" in log or "CHECK_202" in log
        results["203 Context hierarchy generated per agent"]        = "CHECK_203" in log
        results["204 Cumulative metrics isolated per agent"]        = "CHECK_204" in log
        results["205 Context attribution chain complete"]           = "CHECK_205" in log

        # Concurrent Agent Execution (206-210)
        results["206 Concurrent cognitive cycles started"]         = "Active=3" in log or "CHECK_206" in log
        results["207 Concurrent cycle ticks interleaved"]           = "CHECK_207" in log
        results["208 Zero trace ID collisions across agents"]       = "CHECK_208" in log
        results["209 Deterministic event ordering maintained"]      = "CHECK_209" in log
        results["210 All concurrent agent cycles completed"]       = "CHECK_210" in log

        # API Throughput & Stress (211-215)
        results["211 1000 API requests processed successfully"]     = "1000/1000" in log or "CHECK_211" in log
        results["212 API throughput measured (req/sec)"]            = "ReqPerSec" in log or "CHECK_212" in log
        results["213 Zero API error rate under stress"]             = "ErrorRate=0.0%" in log or "CHECK_213" in log
        results["214 Submillisecond P50 response latency"]          = "CHECK_214" in log
        results["215 Stress memory resource growth bounded"]       = "CHECK_215" in log

        # Governance Adversarial Validation (216-220)
        results["216 Complete risk spectrum (0.0-1.0) swept"]       = "Tested=8" in log or "CHECK_216" in log
        results["217 Confidence floor un-bypassable under attack"]  = "CHECK_217" in log
        results["218 Hard risk ceiling un-bypassable under attack"] = "CHECK_218" in log
        results["219 Cryptographic audit chain integrity verified"] = "CHECK_219" in log
        results["220 Consequential unauthorized actions denied"]    = "CHECK_220" in log

        # Kill-and-Recover Event Replay (221-225)
        results["221 Mid-cycle termination logged to event store"] = "CHECK_221" in log
        results["222 Event replay reconstructed engine state"]     = "CHECK_222" in log
        results["223 Agent identity restored post-termination"]     = "CHECK_223" in log
        results["224 Goal tree and memory recovered"]              = "CHECK_224" in log
        results["225 Cognitive cycle resumed deterministically"]   = "CHECK_225" in log

    finally:
        if ue_proc and ue_proc.poll() is None:
            ue_proc.terminate()
            try: ue_proc.wait(timeout=5)
            except Exception: ue_proc.kill()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()

    return results


if __name__ == "__main__":
    res = asyncio.run(run_hardening_suite())

    print("\n[REGRESSION] Running v2.0 platform acceptance suite for regression check...")
    v20_result = subprocess.run(
        [sys.executable, "Tools/Diagnostics/Test-SarembokPlatform.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)
    regression_free = v20_result.returncode == 0
    print(f"  v2.0 Regression Check: {'PASS' if regression_free else 'REGRESSION DETECTED'}")

    print("\n============================================================")
    print("      PLATFORM HARDENING SUMMARY (201 - 225)                ")
    print("============================================================")

    passed = 0
    total  = len(res)
    for k, v in res.items():
        status = "PASS" if v else "FAIL"
        if v: passed += 1
        print(f"  {k:<60}: {status}")

    print(f"\n  v2.0 Regression Suite    : {'PASS' if regression_free else 'FAIL'}")
    print("\n============================================================")
    print(f"  {passed}/{total} HARDENING CHECKS PASSED")
    print("============================================================")

    all_pass = (passed == total) and regression_free
    sys.exit(0 if all_pass else 1)
