#!/usr/bin/env python3
"""
Test-Sarembok30CompleteAcceptance.py
Grand Final Acceptance Suite for Checks 251-300 (Sarembok VE 3.0 Complete Platform).
Covers: World Intelligence, Autonomous Collaboration, Embodied Action Completeness,
        Production Resilience & WAL, External Platform API (12 Facets), and End-to-End Scenario.
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

def get_log(log_file="V3Test.log"):
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

async def run_v3_suite():
    print("============================================================")
    print("  SAREMBOK VE 3.0 COMPLETE PLATFORM ACCEPTANCE (251 - 300)  ")
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

        print("[INIT] Launching SarembokVE Runtime (-LOG=V3Test.log)...")
        remove_log("V3Test.log")

        ue_proc = subprocess.Popen(
            [UE_EXEC, UPROJECT, "-game", "-NullRHI", "-unattended", "-LOG=V3Test.log", "-NOSPLASH"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(22)

        import websockets

        v3_commands = [
            ("251-260", "TriggerV3Test_251_260"),
            ("261-270", "TriggerV3Test_261_270"),
            ("271-280", "TriggerV3Test_271_280"),
            ("281-290", "TriggerV3Test_281_290"),
            ("291-300", "TriggerV3Test_291_300"),
        ]

        for label, command in v3_commands:
            print(f"[CHECKS {label}] {command}...")
            async with websockets.connect(f"ws://{WS_HOST}:{WS_PORT}") as ws:
                cmd = {
                    "protocol": "sarembok.v1",
                    "id": f"cmd-v3-{label}",
                    "timestamp": "2026-08-10T17:00:00Z",
                    "command": command,
                    "target": "System",
                    "payload": {},
                    "context": {"check": label}
                }
                await ws.send(json.dumps(cmd))
                await asyncio.sleep(1)
            time.sleep(3)

        time.sleep(4)
        log = get_log("V3Test.log")

        # World Intelligence (251-260)
        results["251 SarembokWorldModel subsystem initialized"]     = "CHECK_251" in log or "WORLD_MODEL" in log
        results["252 Entities (Humans/Agents/Objects) upserted"]    = "CHECK_252" in log
        results["253 Spatial-temporal transforms tracked"]          = "CHECK_253" in log
        results["254 Belief disagreement detected without overwrite"]= "CHECK_254" in log
        results["255 Disagreement resolved via consensus policy"]    = "CHECK_255" in log
        results["256 Closed loop: Perception -> World Model"]      = "CHECK_256" in log
        results["257 Memory explains World Model state"]            = "CHECK_257" in log
        results["258 Reasoning operates against World Model"]       = "CHECK_258" in log
        results["259 Actions update World Model state"]            = "CHECK_259" in log
        results["260 Multi-agent belief attributed with confidence"] = "CHECK_260" in log

        # Autonomous Team Bidding & Collaboration (261-270)
        results["261 Task bidding submitted by agents"]             = "CHECK_261" in log
        results["262 Capability, cost, confidence bid evaluated"]   = "CHECK_262" in log
        results["263 Dynamic team assembled (Planner/Researcher)"]  = "CHECK_263" in log
        results["264 Autonomous goal decomposition executed"]       = "CHECK_264" in log
        results["265 Concurrent team action dispatched"]            = "CHECK_265" in log
        results["266 Resource quotas enforced across team"]          = "CHECK_266" in log
        results["267 Inter-agent plan proposal verified"]           = "CHECK_267" in log
        results["268 Conflicting team outputs reconciled"]          = "CHECK_268" in log
        results["269 Team task completion signaled to bus"]         = "CHECK_269" in log
        results["270 Autonomous collaboration scenario complete"]   = "CHECK_270" in log

        # Embodied Action Completeness (271-280)
        results["271 Embodied action pipeline initialized"]         = "CHECK_271" in log
        results["272 Multi-factor governance gate enforced"]        = "CHECK_272" in log
        results["273 Speak and Listen actions verified"]            = "CHECK_273" in log
        results["274 Look, Turn, Move, Navigate verified"]          = "CHECK_274" in log
        results["275 Gesture, Emote, Interact verified"]            = "CHECK_275" in log
        results["276 Remember, Retrieve, Query verified"]           = "CHECK_276" in log
        results["277 Delegate and Plan actions verified"]           = "CHECK_277" in log
        results["278 All 14 embodied actions governed fully"]       = "CHECK_278" in log
        results["279 Unauthorized embodied action blocked"]         = "CHECK_279" in log
        results["280 Embodied action completeness verified"]        = "CHECK_280" in log

        # Production Resilience & WAL (281-290)
        results["281 Write-Ahead Log (WAL) entry appended"]         = "CHECK_281" in log
        results["282 WAL replayed successfully"]                    = "CHECK_282" in log
        results["283 Process crash state restored post-restart"]    = "CHECK_283" in log
        results["284 Network message deduplication verified"]       = "CHECK_284" in log
        results["285 Agent failure reassigned automatically"]       = "CHECK_285" in log
        results["286 WebSocket backend auto-reconnected"]           = "CHECK_286" in log
        results["287 State persistence WAL verified"]               = "CHECK_287" in log
        results["288 Restart recovery deterministic"]               = "CHECK_288" in log
        results["289 Cryptographic audit trail reconstructed"]      = "CHECK_289" in log
        results["290 Production resilience suite passed"]           = "CHECK_290" in log

        # Platform API & End-to-End Scenario (291-300)
        results["291 Platform API Agents facet verified"]           = "CHECK_291" in log
        results["292 Platform API State and Goals facets"]          = "CHECK_292" in log
        results["293 Platform API Perception and Memory facets"]    = "CHECK_293" in log
        results["294 Platform API Conversation & Delegation"]       = "CHECK_294" in log
        results["295 Platform API Governance & Audit facets"]       = "CHECK_295" in log
        results["296 Public SDK contract stable across 12 facets"] = "CHECK_296" in log
        results["297 End-to-end human entrance scenario complete"]  = "CHECK_297" in log
        results["298 Cognitive reliability scorecard >= 94.5%"]     = "CHECK_298" in log
        results["299 Full 300-check pyramid regression-free"]       = "CHECK_299" in log
        results["300 Sarembok VE 3.0 Complete Platform verified"]   = "CHECK_300" in log

    finally:
        if ue_proc and ue_proc.poll() is None:
            ue_proc.terminate()
            try: ue_proc.wait(timeout=5)
            except Exception: ue_proc.kill()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()

    return results


if __name__ == "__main__":
    res = asyncio.run(run_v3_suite())

    print("\n[REGRESSION] Running v2.1 multi-agent platform suite for regression check...")
    v21_result = subprocess.run(
        [sys.executable, "Tools/Diagnostics/Test-SarembokMultiAgent.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)
    regression_free = v21_result.returncode == 0
    print(f"  v2.1 Regression Check: {'PASS' if regression_free else 'REGRESSION DETECTED'}")

    print("\n============================================================")
    print("      SAREMBOK VE 3.0 COMPLETE ACCEPTANCE SUMMARY (251 - 300)")
    print("============================================================")

    passed = 0
    total  = len(res)
    for k, v in res.items():
        status = "PASS" if v else "FAIL"
        if v: passed += 1
        print(f"  {k:<60}: {status}")

    print(f"\n  v2.1 Regression Suite    : {'PASS' if regression_free else 'FAIL'}")
    print("\n============================================================")
    print(f"  {passed}/{total} SAREMBOK 3.0 CHECKS PASSED")
    print("============================================================")

    all_pass = (passed == total) and regression_free
    sys.exit(0 if all_pass else 1)
