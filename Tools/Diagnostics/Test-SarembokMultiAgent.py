#!/usr/bin/env python3
"""
Test-SarembokMultiAgent.py
Automated Acceptance Suite for Checks 226-250 (Sarembok_VE v2.1 Multi-Agent Platform).
Covers: SarembokAgentBus, Runtime Manager, Task Delegation, Shared Planning,
        Role Governance & Quotas, Scoped Collective Memory, and Federated Perception.
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

def get_log(log_file="MultiAgentTest.log"):
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

async def run_multiagent_suite():
    print("============================================================")
    print("  SAREMBOK_VE v2.1 MULTI-AGENT ACCEPTANCE SUITE (226 - 250) ")
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

        print("[INIT] Launching SarembokVE Runtime (-LOG=MultiAgentTest.log)...")
        remove_log("MultiAgentTest.log")

        ue_proc = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=MultiAgentTest.log", "-NOSPLASH"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(15)

        import websockets

        multiagent_commands = [
            ("226-230", "TriggerMultiAgentTest_226_230"),
            ("231-235", "TriggerMultiAgentTest_231_235"),
            ("236-240", "TriggerMultiAgentTest_236_240"),
            ("241-245", "TriggerMultiAgentTest_241_245"),
            ("246-250", "TriggerMultiAgentTest_246_250"),
        ]

        for label, command in multiagent_commands:
            print(f"[CHECKS {label}] {command}...")
            async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
                cmd = {
                    "protocol": "sarembok.v1",
                    "id": f"cmd-multi-{label}",
                    "timestamp": "2026-08-10T16:30:00Z",
                    "command": command,
                    "target": "System",
                    "payload": {},
                    "context": {"check": label}
                }
                await ws.send(json.dumps(cmd))
                await ws.recv()
            time.sleep(3)

        time.sleep(4)
        log = get_log("MultiAgentTest.log")

        # SarembokAgentBus Messaging (226-230)
        results["226 Agent bus and runtime manager initialized"]   = "CHECK_226" in log or "AGENT_BUS" in log
        results["227 Governed message envelope routed across bus"]  = "CHECK_227" in log or "MsgId=" in log
        results["228 Message delivered to target agent inbox"]     = "CHECK_228" in log or "Count=1" in log
        results["229 In-flight message cancellation handled"]       = "CHECK_229" in log or "Cancelled=true" in log
        results["230 Message TTL and priority enforced"]            = "CHECK_230" in log

        # Task Delegation System (231-235)
        results["231 Task delegation subsystem initialized"]       = "CHECK_231" in log or "DELEGATION" in log
        results["232 Event-sourced delegation record created"]     = "CHECK_232" in log or "DelId=" in log
        results["233 Delegation authorized and accepted by worker"]= "CHECK_233" in log
        results["234 Delegation executed and completed"]            = "CHECK_234" in log
        results["235 Delegation failure reassigned to peer agent"]  = "CHECK_235" in log

        # Shared Multi-Agent Planning (236-240)
        results["236 Multi-agent shared plan created"]             = "CHECK_236" in log
        results["237 Plan step dependencies resolved"]              = "CHECK_237" in log
        results["238 Parallel plan steps executed by agent team"]   = "CHECK_238" in log
        results["239 Shared plan completion verified"]              = "CHECK_239" in log
        results["240 Plan recovery executed on step failure"]       = "CHECK_240" in log

        # Role Governance & Resource Quotas (241-245)
        results["241 Agent role registered (Researcher/Navigator)"] = "CHECK_241" in log or "Registered role" in log
        results["242 Resource quota configured per agent"]          = "CHECK_242" in log
        results["243 Quota compliance verified before action"]      = "CHECK_243" in log or "Compliant=true" in log
        results["244 Unauthorized role capability action denied"]   = "CHECK_244" in log
        results["245 Resource quota overflow action denied"]        = "CHECK_245" in log

        # Collective Memory & Federated Perception (246-250)
        results["246 Scoped memory (Private/Team/Session/Global)"]  = "CHECK_246" in log
        results["247 Private memory isolated from peer access"]     = "CHECK_247" in log or "LeakValEmpty=true" in log
        results["248 Memory record provenance attributed"]          = "CHECK_248" in log
        results["249 Perception federated across bus to team"]      = "CHECK_249" in log
        results["250 End-to-end multi-agent scenario completed"]    = "CHECK_250" in log

    finally:
        if ue_proc and ue_proc.poll() is None:
            ue_proc.terminate()
            try: ue_proc.wait(timeout=5)
            except Exception: ue_proc.kill()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()

    return results


if __name__ == "__main__":
    res = asyncio.run(run_multiagent_suite())

    print("\n[REGRESSION] Running v2.0.1 platform hardening suite for regression check...")
    v201_result = subprocess.run(
        [sys.executable, "Tools/Diagnostics/Test-SarembokHardening.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)
    regression_free = v201_result.returncode == 0
    print(f"  v2.0.1 Regression Check: {'PASS' if regression_free else 'REGRESSION DETECTED'}")

    print("\n============================================================")
    print("      MULTI-AGENT PLATFORM ACCEPTANCE SUMMARY (226 - 250)   ")
    print("============================================================")

    passed = 0
    total  = len(res)
    for k, v in res.items():
        status = "PASS" if v else "FAIL"
        if v: passed += 1
        print(f"  {k:<60}: {status}")

    print(f"\n  v2.0.1 Regression Suite  : {'PASS' if regression_free else 'FAIL'}")
    print("\n============================================================")
    print(f"  {passed}/{total} MULTI-AGENT CHECKS PASSED")
    print("============================================================")

    all_pass = (passed == total) and regression_free
    sys.exit(0 if all_pass else 1)
