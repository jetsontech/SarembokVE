#!/usr/bin/env python3
"""
Test-PrometheusEvolver.py — Diagnostic Test Suite for Sarembok Prometheus Super-Engine
Validates:
1. Recursive Self-Evolution Benchmarking & Milestone Hashing
2. Autonomous Multi-Agent Swarm Code Compilation
3. Proactive Background OmniDaemon Audits & Insight Discovery
4. Sandbox Code Execution & Return Code Integrity
"""

import json
import os
import sys
import time
import urllib.request
import websockets
import asyncio

URL = os.getenv("SAREMBOK_WS_URL", "ws://127.0.0.1:9120")
AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "")

passed_count = 0
failed_count = 0

def log_pass(name, detail=""):
    global passed_count
    passed_count += 1
    print(f"[PASS] [{name}] {detail}")

def log_fail(name, err=""):
    global failed_count
    failed_count += 1
    print(f"[FAIL] [{name}] ERROR: {err}")

async def send_rpc(ws, method, params=None):
    req_id = f"test-{int(time.time()*1000)}"
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": {**(params or {}), "authToken": AUTH_TOKEN}
    }
    await ws.send(json.dumps(payload))
    resp_raw = await ws.recv()
    resp = json.loads(resp_raw)
    if "error" in resp:
        raise RuntimeError(f"RPC Error {resp['error']['code']}: {resp['error']['message']}")
    return resp["result"]

async def run_prometheus_tests():
    print("=" * 70)
    print(" SAREMBOK PROMETHEUS SUPER-ENGINE DIAGNOSTIC VERIFICATION")
    print("=" * 70)

    async with websockets.connect(URL) as ws:
        # Phase 1: Recursive Self-Evolution
        try:
            m = await send_rpc(ws, "TriggerSelfEvolution", {"dimension": "VECTOR_INDEX_SEARCH"})
            assert m["speedupFactor"] >= 1.0, "Speedup factor must be >= 1.0"
            assert len(m["verificationHash"]) == 64, "Must produce valid SHA-256 hash"
            log_pass("SELF_EVOLUTION", f"Cycle {m['iteration']}: {m['dimension']} speedup={m['speedupFactor']}x hash={m['verificationHash'][:12]}...")
        except Exception as e:
            log_fail("SELF_EVOLUTION", str(e))

        try:
            hist = await send_rpc(ws, "ListEvolutionMilestones", {"limit": 5})
            assert len(hist.get("milestones", [])) > 0
            log_pass("EVOLUTION_HISTORY", f"Retrieved {len(hist['milestones'])} historical milestones")
        except Exception as e:
            log_fail("EVOLUTION_HISTORY", str(e))

        # Phase 2: Autonomous Multi-Agent Swarm Code Compilation
        try:
            proj = await send_rpc(ws, "CompileEngineeringSwarm", {
                "goal": "Build a real-time WebSocket distributed order book with sub-millisecond matching"
            })
            assert len(proj["stages"]) == 4, "Must compile 4 distinct swarm stages"
            assert len(proj["files"]) == 4, "Must synthesize 4 multi-language files"
            log_pass("SWARM_COMPILER", f"Project {proj['projectId']}: 4 stages, {len(proj['files'])} synthesized files (Python/JSON/Docker)")
        except Exception as e:
            log_fail("SWARM_COMPILER", str(e))

        try:
            plist = await send_rpc(ws, "ListSwarmProjects", {"limit": 5})
            assert len(plist.get("projects", [])) > 0
            log_pass("SWARM_PROJECT_LIST", f"Found {len(plist['projects'])} compiled swarm projects in ledger")
        except Exception as e:
            log_fail("SWARM_PROJECT_LIST", str(e))

        # Phase 3: Proactive Background OmniDaemon
        try:
            scan = await send_rpc(ws, "TriggerProactiveScan")
            assert len(scan.get("insights", [])) >= 3
            log_pass("PROACTIVE_SCAN", f"Generated {len(scan['insights'])} autonomous proactive insights")
        except Exception as e:
            log_fail("PROACTIVE_SCAN", str(e))

        try:
            insights = await send_rpc(ws, "QueryProactiveInsights", {"limit": 5})
            assert len(insights.get("insights", [])) > 0
            log_pass("PROACTIVE_INSIGHTS", f"Retrieved {len(insights['insights'])} proactive intelligence records")
        except Exception as e:
            log_fail("PROACTIVE_INSIGHTS", str(e))

        # Phase 4: Sandbox Code Execution
        try:
            code = "a = 42\nb = 58\nprint(f'COMPUTATION_SUCCESS: result={a+b}')"
            exec_res = await send_rpc(ws, "ExecuteSandboxCode", {"code": code, "language": "python"})
            assert exec_res["status"] == "SUCCESS"
            assert "result=100" in exec_res["output"]
            log_pass("SANDBOX_EXECUTION", f"Status={exec_res['status']} Time={exec_res['executionTimeMs']}ms Output='{exec_res['output'].strip()}'")
        except Exception as e:
            log_fail("SANDBOX_EXECUTION", str(e))

    print("=" * 70)
    print(f" PROMETHEUS RESULTS: {passed_count}/{passed_count+failed_count} PASSED | {failed_count} FAILED")
    print("=" * 70)
    if failed_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_prometheus_tests())
